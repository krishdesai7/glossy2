"""Old English dictionary built from Wiktionary via kaikki.org (wiktextract)."""

import json
import sqlite3
import threading
import unicodedata
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

from glossy2.normalize import normalize

DOWNLOAD_URL = "https://kaikki.org/dictionary/Old%20English/kaikki.org-dictionary-OldEnglish.jsonl"
JSONL_PATH = Path("data/kaikki-oe.jsonl")
INDEX_PATH = Path("data/dictionary.sqlite")
_NON_FORM_TAGS = {"table-tags", "inflection-template", "class"}


@dataclass
class Entry:
    lemma: str
    pos: str
    senses: list[str]
    url: str
    form_tags: list[list[str]]


def _page_url(word: str) -> str:
    decomposed = unicodedata.normalize("NFD", word)
    title = unicodedata.normalize("NFC", "".join(c for c in decomposed if not unicodedata.combining(c)))
    return f"https://en.wiktionary.org/wiki/{quote(title)}#Old_English"


def build_index(jsonl_path: Path, index_path: Path) -> None:
    """Index every usable form. A form-of record points at its lemma."""
    records = []
    real_lemmas: set[str] = set()
    with Path(jsonl_path).open(encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            records.append(record)
            senses = record.get("senses", [])
            if any(not sense.get("form_of") for sense in senses):
                real_lemmas.add(record["word"])

    connection = sqlite3.connect(index_path)
    connection.executescript(
        "DROP TABLE IF EXISTS forms; DROP TABLE IF EXISTS lemmas;"
        "CREATE TABLE forms (form TEXT, lemma TEXT, pos TEXT, senses TEXT, url TEXT, tags TEXT);"
        "CREATE TABLE lemmas (form TEXT PRIMARY KEY);"
    )
    rows = []
    lemma_forms: set[str] = set()
    for record in records:
        word = record["word"]
        senses = record.get("senses", [])
        glosses = [gloss for sense in senses for gloss in sense.get("glosses", [])]
        targets = [t["word"] for s in senses for t in s.get("form_of", []) if t.get("word")]
        if word in real_lemmas:
            sense_text = json.dumps(glosses, ensure_ascii=False)
            url = _page_url(word)
            lemma_forms.add(normalize(word))
            rows.append((normalize(word), word, record.get("pos", ""), sense_text, url, "[]"))
            for form in record.get("forms", []):
                tags = form.get("tags", [])
                if form.get("form") and not _NON_FORM_TAGS.intersection(tags):
                    if "canonical" in tags:
                        lemma_forms.add(normalize(form["form"]))
                    rows.append(
                        (normalize(form["form"]), word, record.get("pos", ""), sense_text, url,
                         json.dumps(tags))
                    )
        for target in dict.fromkeys(targets):
            known = target in real_lemmas
            url = _page_url(target if known else word)
            tags = sorted(_case_number_tags(glosses))
            rows.append(
                (normalize(word), target, record.get("pos", ""), json.dumps(glosses, ensure_ascii=False),
                 url, json.dumps(tags))
            )
    connection.executemany("INSERT INTO forms VALUES (?,?,?,?,?,?)", rows)
    connection.executemany("INSERT OR IGNORE INTO lemmas VALUES (?)", [(f,) for f in lemma_forms])
    connection.execute("CREATE INDEX forms_form ON forms(form)")
    connection.commit()
    connection.close()


def _case_number_tags(glosses: list[str]) -> set[str]:
    words = {
        "nominative", "accusative", "genitive", "dative", "instrumental", "singular", "plural",
        "first-person", "second-person", "third-person", "past", "present", "indicative",
        "subjunctive", "imperative", "participle", "infinitive",
    }
    return {w for g in glosses for w in g.lower().replace("/", " ").split() if w in words}


def fetch_dictionary(jsonl_path: Path = JSONL_PATH, index_path: Path = INDEX_PATH) -> None:
    index_path.parent.mkdir(parents=True, exist_ok=True)
    if not jsonl_path.exists():
        print(f"Downloading the Wiktionary data (about 134 MB) from {DOWNLOAD_URL}")
        try:
            urllib.request.urlretrieve(DOWNLOAD_URL, jsonl_path)
        except OSError as error:
            raise SystemExit(
                f"Couldn't download the dictionary ({error}). kaikki.org marks this file as "
                "deprecated, so check https://kaikki.org/dictionary/Old%20English/ for its replacement."
            ) from error
    print("Building the dictionary index")
    build_index(jsonl_path, index_path)


class Dictionary:
    def __init__(self, connection: sqlite3.Connection):
        self._connection = connection
        self._lock = threading.Lock()

    @classmethod
    def open(cls, path: Path = INDEX_PATH) -> "Dictionary":
        if not Path(path).exists():
            if Path(path) != INDEX_PATH:
                raise FileNotFoundError(path)
            fetch_dictionary()
        return cls(sqlite3.connect(path, check_same_thread=False))

    def lookup(self, form: str) -> list[Entry]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT lemma, pos, senses, url, tags FROM forms WHERE form = ?", (normalize(form),)
            ).fetchall()
        merged: dict[tuple[str, str], Entry] = {}
        for lemma, pos, senses, url, tags in rows:
            entry = merged.setdefault((lemma, pos), Entry(lemma, pos, [], url, []))
            entry.senses.extend(s for s in json.loads(senses) if s not in entry.senses)
            parsed = json.loads(tags)
            if parsed and parsed not in entry.form_tags:
                entry.form_tags.append(parsed)
        return list(merged.values())

    def has_lemma(self, lemma: str) -> bool:
        with self._lock:
            row = self._connection.execute(
                "SELECT 1 FROM lemmas WHERE form = ?", (normalize(lemma),)
            ).fetchone()
        return row is not None
