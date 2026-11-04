"""Pure parsing of one Infyner company page. parse(html) -> dict, strip(html) -> smaller html to store."""
import html as H
import re

TAG = re.compile(r"<[^>]+>")
NUM = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}


def strip(doc):
    return re.sub(r"<script.*?</script>|<style.*?</style>|<svg.*?</svg>", " ", doc, flags=re.S | re.I)


def lines(s):
    return [x for x in (l.strip().strip("|").strip() for l in H.unescape(TAG.sub("\n", s)).split("\n")) if x]


def after(ls, key, n=1):
    for i, l in enumerate(ls):
        if l == key and i + n < len(ls):
            return ls[i + n]


def directors(ls):
    rows, inside = [], False
    for i, l in enumerate(ls):
        if l.startswith("Current Directors of"):
            inside = True
            continue
        if inside and (l.startswith("Financial Performance") or l.startswith("Past Directors") or l.startswith("Signatories")):
            break
        if inside and l == "DIN:" and i + 1 < len(ls) and re.fullmatch(r"\d{8}", ls[i + 1]):
            back = ls[max(0, i - 6):i]
            since = next((b.replace("Since ", "") for b in back if b.startswith("Since ")), None)
            k = next((j for j, b in enumerate(back) if b.startswith("Since ")), len(back))
            back2 = [b for b in back[:k] if b != "|"]
            name, des = (back2[-2], back2[-1]) if len(back2) >= 2 else (None, None)
            rows.append({"name": name, "din": ls[i + 1], "designation": des, "since": since})
    return rows


def common(t):
    a = t.find("Companies With Common Directors")
    if a < 0:
        return []
    b = min([x for x in (t.find("Relevant Competitors", a), t.find("Financial Ratios", a)) if x > 0] or [len(t)])
    sec = t[a:b]
    marks = list(re.finditer(r'<a\b[^>]*href="/company/[^"/]+/([A-Z0-9-]+)"[^>]*>', sec))
    out = []
    for i, m in enumerate(marks):
        part = lines(sec[m.end():marks[i + 1].start() if i + 1 < len(marks) else len(sec)])
        n = next((int(re.match(r"\d+", x).group()) for x in part if re.match(r"\d+ Shared Director", x)), None)
        shared = [x for x in part if len(x) > 2 and not re.match(r"\d+ Shared", x)]
        names = shared[0] if shared else None
        out.append({"cin": m.group(1), "name": names, "n_shared": n, "shared": shared[1:] if n else []})
    return out


def parse(doc):
    t = strip(doc)
    ls = lines(t)
    about = next((l for i, l in enumerate(ls) if l.startswith("About ") and i + 2 < len(ls) and "Company identity" in ls[i + 1]), None)
    i = ls.index(about) if about else -1
    tx = " ".join(p for p in (ls[i + 2:i + 8] if about else [])).split("Read More")[0].strip()
    fn = re.search(r"(?:earlier|formerly|previously) known as ([^.]+?)\.", tx)
    fd = re.search(r"((?:One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten|\d+) former directors? (?:is|are) on record[^.]*\.)", tx)
    ll = re.search(r"to leave was ([^.]+?) in ", tx)
    act = None
    if "Activity Group" in ls:
        k = ls.index("Activity Group")
        act = " / ".join(ls[k + 3:k + 6])
    return {"title": ls[0].split(" - Owner")[0] if ls else None,
            "brand": next((l[len("Current Directors of "):].rsplit(" (", 1)[0] for l in ls if l.startswith("Current Directors of ")), None),
            "about": tx[:1500], "former_name": fn.group(1) if fn else None, "former_directors": fd.group(1) if fd else None, "last_left": ll.group(1) if ll else None,
            "revenue": after(ls, "REVENUE"), "pnl": after(ls, "PROFIT / LOSS"), "networth": after(ls, "NET WORTH"), "assets": after(ls, "TOTAL ASSETS"), "fy": after(ls, "REVENUE", 3),
            "employees": after(ls, "EMPLOYEE COUNT"), "paidup": after(ls, "PAID-UP CAPITAL"), "authorised": after(ls, "AUTHORISED CAPITAL"), "active_gst": after(ls, "ACTIVE GST"),
            "open_charges": after(ls, "OPEN CHARGES"), "last_filing": after(ls, "LAST FILING WITH ROC"), "website": after(ls, "Website"), "address": after(ls, "Location"), "activity": act,
            "directors": directors(ls), "common": common(t)}
