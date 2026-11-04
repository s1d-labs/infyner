"""Put this family's projects in the pool and register its health checks. Run by the Setup workflow. Safe to run again: queue items that exist are kept.
Note: running Setup sets workers and speed back to the values in family.py."""
from scrape_hub_client import register_project, seed_queue, set_pool, set_probes

from family import FAMILY, PROBES, PROJECTS, items

print("health checks:", set_probes(FAMILY, PROBES))
for p in PROJECTS:
    its = items(p["list"])
    register_project(p["name"], title=p["title"], unit_label=p["unit_label"], record_label=p["record_label"],
                     expected_units=len(its), expected_records=sum(i["payload"]["expected"] for i in its))
    set_pool(p["name"], FAMILY, p["task"], target=p["target"], env=p["env"], probe=p["probe"], max_workers=p["max_workers"], threads=p["threads"], delay_ms=p["delay_ms"])
    for k in range(0, len(its), 500):
        print(p["name"], "queue:", seed_queue(p["name"], its[k:k + 500]))
