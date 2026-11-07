"""Pure parsing of one corporatedir.com /company/<slug> page. parse(html) -> dict. No network.

The page carries a plain directors table (Name with an /officer/<din> link, DIN, Designation, Appointed, Share %, Status)
and a few company facts. corporatedir serves this over ordinary HTTP; the slug URL is not behind a challenge.
"""
import html as H
import re

TAG = re.compile(r"<[^>]+>")
TR = re.compile(r"<tr>(.*?)</tr>", re.S | re.I)
TD = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.S | re.I)
OFFICER = re.compile(r"/officer/(\d+)")
DIN8 = re.compile(r"\b\d{6,8}\b")
CIN = re.compile(r"\bCIN:?\s*([LU][0-9]{5}[A-Z]{2}[0-9]{4}[A-Z]{3}[0-9]{6})")


def txt(s):
    return H.unescape(TAG.sub("", s or "")).strip()


def strip(doc):
    return re.sub(r"<script.*?</script>|<style.*?</style>|<svg.*?</svg>", " ", doc, flags=re.S | re.I)


def _fact(doc, label):
    m = re.search(re.escape(label) + r"\s*</[^>]+>\s*<[^>]+>\s*([^<]{1,80})", doc, re.I)
    return txt(m.group(1)) if m else None


def _clean(v):
    return v if v and v not in ("-", "") else None


def parse(doc):
    """-> {found, cin_on_page, directors:[{name, din, designation, appointed, status}], company_status, reg_date, n_directors}.
    found=False when the page is served but names no company (corporatedir's own 404 body, or a slug that is not a company)."""
    dirs, seen, cols = [], set(), None
    for tr in TR.finditer(doc):
        body = tr.group(1)
        cells = [txt(c) for c in TD.findall(body)]
        if not cells:
            continue
        low = [c.lower() for c in cells]
        if "din" in low and "name" in low:                       # the header row names the columns
            cols = {name: i for i, name in enumerate(low)}
            continue
        if cols is None or "/officer/" not in body.lower():
            continue
        get = lambda k: cells[cols[k]] if k in cols and cols[k] < len(cells) else None
        dm = DIN8.search(get("din") or "") or OFFICER.search(body)
        if not dm:
            continue
        din = dm.group(0 if dm.re is DIN8 else 1).zfill(8)
        if din in seen:
            continue
        seen.add(din)
        dirs.append({"name": get("name"), "din": din, "designation": _clean(get("designation")),
                     "appointed": _clean(get("appointed")), "status": _clean(get("status"))})
    cinm = CIN.search(doc)
    return {"found": bool(dirs) or cinm is not None, "cin_on_page": cinm.group(1) if cinm else None,
            "directors": dirs, "company_status": _fact(doc, "Status"), "reg_date": _fact(doc, "Incorporation"),
            "n_directors": len(dirs)}
