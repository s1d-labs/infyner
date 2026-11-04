import gzip, pathlib
from parse import parse, strip

P = pathlib.Path(__file__).parent / "pages"


def test_company_page():
    r = parse(gzip.open(P / "U80302DL2011PLC213843.html.gz", "rt", encoding="utf-8").read())
    assert {d["din"] for d in r["directors"]} == {"02005761", "01909098", "01200719"}
    assert r["former_name"] == "Edutronics Innovative Education Limited"
    assert r["last_left"] == "Sudhanshu Sharma"
    assert r["paidup"] == "5.00 Lakh"
    assert any(c["name"] == "Prepgenius Llp" and c["n_shared"] == 1 for c in r["common"])


def test_strip_keeps_fields():
    d = gzip.open(P / "U80302DL2011PLC213843.html.gz", "rt", encoding="utf-8").read()
    assert parse(strip(d))["directors"] == parse(d)["directors"]
