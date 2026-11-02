from glossy2.normalize import normalize


def test_thorn_eth_and_ycoe_codes_merge():
    assert normalize("Ðǣm") == normalize("þæm") == normalize("+t+am")


def test_palatal_dots_stripped():
    assert normalize("ġēar") == normalize("gear")
    assert normalize("ċirre") == normalize("cirre")


def test_y_i_kept_apart():
    assert normalize("hyra") != normalize("hira")


def test_capitals_and_macrons():
    assert normalize("Ælfrēd") == normalize("ælfred") == normalize("+Alfred")


def test_hyphens_and_ycoe_emendation_marks_removed():
    assert normalize("sǣ-d-e") == normalize("sæde")
    assert normalize("$gesetenis") == "gesetenis"


def test_dot_below_stripped():
    assert normalize("ġẹond") == "geond"
