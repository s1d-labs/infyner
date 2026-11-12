"""Task `corpdir`: fetch corporatedir.com /company/<slug> pages, store the raw pages as a tar and the parsed directors
(DIN, name, designation, appointed, status) as one record per company. Alternate director source to the infyner pages.

Only the public /company/ slug page, which corporatedir serves over ordinary HTTP. The challenge-platform script is
preloaded on every page but does not gate the slug URL; a real "Just a moment" interstitial (seen on other routes or a
flagged IP) is treated as a block: the worker waits and takes the hub's lower speed, and never tries to pass it.
One queue item = N companies ([cin, name] pairs); the slug is derived from the name.
"""
import gzip, io, os, re, sys, tarfile, threading, time
from concurrent.futures import ThreadPoolExecutor

import requests
from scrape_hub_client import HubClient, timed_get

from corpdir_parse import parse, strip

PROJECT = os.environ["SCRAPE_POOL_PROJECT"]
DEADLINE = time.time() + float(os.environ.get("SCRAPE_MAX_HOURS", "1")) * 3600 - 180
SITE = "https://www.corporatedir.com"
UA = "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"
CHALLENGE = re.compile(r"(?i)just a moment|are you a human|checking your browser|cf-chl-|enable javascript and cookies")
tl = threading.local()
wait_until = [0.0]


def slug(name):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", name.lower())).strip("-")


def session():
    if not hasattr(tl, "s"):
        tl.s = requests.Session()
        tl.s.headers["User-Agent"] = UA
    return tl.s


def fetch(hub, cin, name):
    """-> (status, html): ok, missing, block, error."""
    s = slug(name)
    if not s:
        return "missing", None
    # counts n_http, t_http_s, http_<code> (404 too), http_error + hub.error(); 403/429/503 -> hub.block()
    r = timed_get(hub, session(), f"{SITE}/company/{s}", timeout=45)
    if r is None:
        return "error", None
    if r.status_code in (403, 429, 503) or (r.status_code == 200 and CHALLENGE.search(r.text[:20000])):
        if r.status_code == 200:           # a challenge page: timed_get counted no code and no block
            hub.metric("http_challenge"); hub.block()
        ra = r.headers.get("Retry-After", "")
        wait_until[0] = max(wait_until[0], time.time() + (int(ra) if ra.isdigit() else 120))
        return "block", None
    if r.status_code == 404:
        return "missing", None
    if r.status_code != 200:
        hub.error()                        # timed_get counted http_<code>
        return "error", None
    r.encoding = "utf-8"
    return "ok", r.text


def work_item(hub, item, pool, delay):
    rows = item["payload"]["companies"]

    def one(row):
        if time.time() < wait_until[0]:
            return row[0], "skip", None
        st, doc = fetch(hub, row[0], row[1])
        time.sleep(delay)
        return row[0], st, doc

    res = list(pool.map(one, rows))
    tarb = io.BytesIO(); ok = 0; pages = 0
    with tarfile.open(fileobj=tarb, mode="w") as tf:
        for cin, st, doc in res:
            if st == "ok":
                d = parse(doc)
                # keep only pages that actually name the company or its directors; a bare slug-miss page is "missing"
                if d["found"]:
                    raw = gzip.compress(strip(doc).encode("utf-8"), 6)
                    ti = tarfile.TarInfo(f"{cin}.html.gz"); ti.size = len(raw)
                    tf.addfile(ti, io.BytesIO(raw)); pages += 1
                    # the CIN on the page must match the one we asked for, else the slug resolved to another company
                    d["cin_match"] = (d.get("cin_on_page") == cin)
                    hub.record(cin, {"cin": cin, **d})
                else:
                    hub.record(cin, {"cin": cin, "missing": True})
                ok += 1
            elif st == "missing":
                hub.record(cin, {"cin": cin, "missing": True})
                ok += 1
    if pages:                           # a closed empty tar still has 10 KB of end blocks: upload only real pages
        hub.upload_many([(f"corpdir/{item['key']}.tar", tarb.getvalue(), "application/x-tar")])
    bad = [c for c, st, _ in res if st in ("block", "error", "skip")]
    if len(bad) > len(rows) // 5:
        hub.complete([item["key"]], "failed", error=f"{len(bad)} of {len(rows)} pages did not load")
    else:
        hub.complete([item["key"]], "done", fetched=ok)


def main():
    hub = HubClient(PROJECT, job_index=int(os.environ.get("SCRAPE_JOB_INDEX", 0)), total_jobs=int(os.environ.get("SCRAPE_TOTAL_JOBS", 1)))
    try:
        while time.time() < DEADLINE:
            if hub.settings.get("paused"):
                time.sleep(30); continue
            if time.time() < wait_until[0]:
                time.sleep(min(30, wait_until[0] - time.time())); continue
            items = hub.claim(1, steal=True, retry_failed=True)
            if not items:
                break
            n = max(1, int(hub.settings.get("threads", 2)))
            with ThreadPoolExecutor(n) as pool:
                work_item(hub, items[0], pool, hub.settings.get("delay_ms", 0) / 1000)
        hub.close()
    except BaseException as e:
        hub.close("failed", f"{type(e).__name__}: {e}"[:200]); raise


if __name__ == "__main__":
    sys.exit(main())
