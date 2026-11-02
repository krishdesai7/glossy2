from collections import Counter


class FakeYcoe:
    def __init__(self, table=None):
        self.table = table or {}

    def tags(self, form):
        return Counter(self.table.get(form, {}))


class FakeDictionary:
    def __init__(self, entries=None, lemmas=()):
        self.entries, self.lemmas = entries or {}, set(lemmas)

    def lookup(self, form):
        return self.entries.get(form, [])

    def has_lemma(self, lemma):
        return lemma in self.lemmas
