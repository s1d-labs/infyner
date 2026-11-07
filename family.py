"""Public company pages on www.infyner.com. One queue item = 50 companies. The lists in data/ are CIN + name from the MCA master."""
import gzip, json
from pathlib import Path

HERE = Path(__file__).parent
FAMILY = json.loads((HERE / "scrape.json").read_text())["family"]
SIZE = 50


def items(list_name):
    rows = [l.rstrip("\n").split("\t") for l in gzip.open(HERE / "data" / f"{list_name}.tsv.gz", "rt", encoding="utf-8")]
    out = []
    for i in range(0, len(rows), SIZE):
        part = rows[i:i + SIZE]
        out.append({"key": f"{list_name}-{i // SIZE:06d}", "payload": {"companies": part, "expected": len(part)}})
    return out


PROJECTS = [
    {"name": f"{FAMILY}-gem-sellers", "title": "Company pages: GeM sellers", "list": "gem_sellers", "task": "pages", "target": "www.infyner.com", "env": {},
     "probe": f"{FAMILY}:www.infyner.com", "unit_label": "batch", "record_label": "company", "max_workers": 4, "threads": 2, "delay_ms": 300},
    # From the s1d entity graph (s1d-labs/graph gaps.py): registered companies that take public money (GeM, GePNIC, MGNREGA,
    # MPLADS, World Bank, PWD) or fund parties (bonds, donations) and have no director record yet. Biggest money first.
    {"name": f"{FAMILY}-graph", "title": "Company pages: public-money companies without directors (graph gaps)", "list": "graph_priority",
     "task": "pages", "target": "www.infyner.com", "env": {}, "probe": f"{FAMILY}:www.infyner.com", "unit_label": "batch",
     "record_label": "company", "max_workers": 16, "threads": 4, "delay_ms": 300},
    # Alternate director source (corporatedir.com), for the same graph-gap companies: it serves the slug /company/ page over
    # plain HTTP, so this runs on GitHub runners (no India server, no proxy). Used when infyner is unavailable.
    {"name": f"{FAMILY}-corpdir", "title": "corporatedir directors: public-money companies without directors (graph gaps)",
     "list": "graph_priority", "task": "corpdir", "target": "www.corporatedir.com", "env": {},
     "probe": f"{FAMILY}:www.corporatedir.com", "unit_label": "batch", "record_label": "company", "max_workers": 10,
     "threads": 3, "delay_ms": 400},
]
PROBES = [{"name": f"{FAMILY}:www.infyner.com", "url": "https://www.infyner.com/robots.txt", "expect": "Disallow"},
          {"name": f"{FAMILY}:www.corporatedir.com", "url": "https://www.corporatedir.com/robots.txt", "expect": "ser"}]
