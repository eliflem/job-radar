"""Job Radar: daily collector.

Pulls fresh listings from job boards (JobSpy), the Arbeitsagentur Jobbörse and
company career pages (public ATS feeds), applies hard title filters, drops
anything seen before, and writes today's new candidates to
data/candidates/YYYY-MM-DD.json for the daily Claude review.

Every source is isolated: one failing source never stops the run.
"""
from __future__ import annotations

import base64
import datetime as dt
import html
import json
import logging
import re
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import requests
import yaml

ROOT = Path(__file__).parent
DATA = ROOT / "data"
CANDIDATES = DATA / "candidates"
SEEN_FILE = DATA / "seen.json"
ATS_CACHE_FILE = DATA / "ats_cache.json"
RUN_REPORT_FILE = DATA / "last_run.json"

TODAY = dt.date.today().isoformat()
UA = {"User-Agent": "Mozilla/5.0 (job-radar personal job search; +https://github.com)"}
DESC_LIMIT = 6000
SEEN_RETENTION_DAYS = 120

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("job-radar")
session = requests.Session()
session.headers.update(UA)

report: dict = {"date": TODAY, "sources": {}, "errors": []}


# ---------------------------------------------------------------- helpers
def load_json(path: Path, default):
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def save_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=1))


def clean_text(raw) -> str:
    if not raw or not isinstance(raw, str):
        return ""
    text = html.unescape(raw)
    text = re.sub(r"<(br|/p|/li|/h\d)[^>]*>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text.strip()[:DESC_LIMIT]


GENDER_TAG = re.compile(r"\((?:[mwfdxnhgi*]\s*[/|,]\s*)+[mwfdxnhgi*]\)|\((?:all genders?|gn|w/m/d|m/f/d|d/f/m)\)|\[gn\]", re.I)


def norm(s: str) -> str:
    s = (s or "").lower()
    s = GENDER_TAG.sub(" ", s)  # drop (m/w/d), (f/m/x), (all genders) ...
    s = re.sub(r"\b(gmbh|ag|se|inc|ltd|llc|bv|sas)\b", " ", s)
    return re.sub(r"[^a-z0-9]+", "", s)


def get(url, **kw):
    kw.setdefault("timeout", 25)
    return session.get(url, **kw)


def job(source, company, title, url, location="", remote=None, posted="", description="", ext_id=""):
    return {
        "id": f"{source}:{ext_id or url}",
        "key": f"{norm(company)}|{norm(title)}",
        "source": source,
        "company": (company or "").strip(),
        "title": (title or "").strip(),
        "url": url,
        "location": (location or "").strip(),
        "remote": remote,
        "posted": str(posted or "")[:10],
        "description": clean_text(description),
    }


# ---------------------------------------------------------------- filters
class Filters:
    def __init__(self, cfg):
        self.include = re.compile("|".join(cfg["title_include"]), re.I)
        self.exclude = re.compile("|".join(cfg["title_exclude"]), re.I)
        self.bad_companies = {norm(c) for c in cfg.get("excluded_companies", [])}

    def title_ok(self, title: str) -> bool:
        return bool(title) and bool(self.include.search(title)) and not self.exclude.search(title)

    def company_ok(self, company: str) -> bool:
        return norm(company) not in self.bad_companies


LOCATION_OK = re.compile(
    r"berlin|germany|deutschland|remote|anywhere|worldwide|global|europe|emea|\beu\b|distributed|home ?office",
    re.I,
)


def location_plausible(location: str, remote) -> bool:
    """Cheap prefilter for company feeds; the real judgment happens in the Claude review."""
    if remote:
        return True
    return not location or bool(LOCATION_OK.search(location))


# ---------------------------------------------------------------- job boards (JobSpy)
def linkedin_description(job_id: str) -> str:
    try:
        r = get(f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}")
        if r.status_code != 200:
            return ""
        m = re.search(r'class="show-more-less-html__markup[^"]*"[^>]*>(.*?)</div>', r.text, re.S)
        return m.group(1) if m else ""
    except Exception:
        return ""


REMOTE_WORD = re.compile(r"\bremote\b|work from anywhere|fully distributed|home[- ]based", re.I)


def looks_remote(row) -> bool:
    """LinkedIn's remote filter is loose: drop on-site jobs from the remote-only searches."""
    if row.get("is_remote") is True:
        return True
    text = " ".join(str(row.get(k) or "") for k in ("title", "location")) + " " + str(row.get("description") or "")[:4000]
    return bool(REMOTE_WORD.search(text))


def collect_boards(cfg, flt: Filters) -> list[dict]:
    try:
        from jobspy import scrape_jobs
    except ImportError:
        report["errors"].append("jobspy not installed")
        return []

    out, raw_count = [], 0
    for loc in cfg["board_locations"]:
        for term in cfg["search_terms"]:
            remote_only = loc["remote_only"]
            if remote_only:
                sites = [s for s in cfg["sites"] if s in ("linkedin", "google")]
                google_q = f"remote {term} jobs since yesterday"
            else:
                sites = list(cfg["sites"])
                google_q = f"{term} jobs near Berlin, Germany since yesterday"
            kwargs = dict(
                site_name=sites,
                search_term=term,
                google_search_term=google_q,
                location=loc["name"],
                results_wanted=cfg["results_per_search"],
                hours_old=cfg["hours_old"],
                country_indeed="germany",
                verbose=0,
            )
            if remote_only:
                kwargs["is_remote"] = True
            try:
                df = scrape_jobs(**kwargs)
            except Exception as e:  # rate limits etc.
                report["errors"].append(f"jobspy {loc['name']} / {term}: {e}"[:300])
                time.sleep(10)
                continue
            raw_count += len(df)
            for row in df.to_dict("records"):
                title, company = row.get("title") or "", row.get("company") or ""
                if not flt.title_ok(title) or not flt.company_ok(company):
                    continue
                if remote_only and not looks_remote(row):
                    continue
                url = row.get("job_url_direct") or row.get("job_url") or ""
                out.append(job(
                    source=row.get("site") or "board",
                    company=company,
                    title=title,
                    url=row.get("job_url") or url,
                    location=row.get("location") or "",
                    remote=bool(row.get("is_remote")) if row.get("is_remote") is not None else None,
                    posted=row.get("date_posted") or "",
                    description=row.get("description") or "",
                    ext_id=str(row.get("id") or url),
                ))
            time.sleep(3)
    report["sources"]["boards"] = {"raw": raw_count, "after_title_filter": len(out)}
    return out


def enrich_linkedin(jobs: list[dict]) -> None:
    """Fetch descriptions only for LinkedIn jobs that survived all filters (keeps requests low)."""
    fetched = 0
    for j in jobs:
        if j["source"] != "linkedin" or j["description"]:
            continue
        m = re.search(r"(\d{6,})", j["id"])
        if not m:
            continue
        j["description"] = clean_text(linkedin_description(m.group(1)))
        fetched += 1
        time.sleep(1.5)
    report["sources"]["linkedin_descriptions_fetched"] = fetched


# ---------------------------------------------------------------- Arbeitsagentur
BA_BASE = "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service"
BA_HEADERS = {"X-API-Key": "jobboerse-jobsuche"}


def collect_arbeitsagentur(cfg, flt: Filters) -> list[dict]:
    ba = cfg.get("arbeitsagentur", {})
    if not ba.get("enabled"):
        return []
    out = []
    for s in ba["searches"]:
        params = {"was": s["was"], "angebotsart": 1, "veroeffentlichtseit": 2, "size": 100, "page": 1}
        if s.get("wo") and s["wo"] != "Deutschland":
            params["wo"] = s["wo"]
            params["umkreis"] = s.get("umkreis", 25)
        if s.get("homeoffice"):
            params["arbeitszeit"] = "ho"
        try:
            r = get(f"{BA_BASE}/pc/v6/jobs", params=params, headers=BA_HEADERS)
            r.raise_for_status()
            offers = r.json().get("stellenangebote", []) or []
        except Exception as e:
            report["errors"].append(f"arbeitsagentur {s}: {e}"[:300])
            continue
        for o in offers:
            title, company = o.get("titel") or o.get("beruf") or "", o.get("arbeitgeber") or ""
            if not flt.title_ok(title) or not flt.company_ok(company):
                continue
            refnr = o.get("refnr", "")
            place = (o.get("arbeitsort") or {}).get("ort", "")
            out.append(job(
                source="arbeitsagentur", company=company, title=title,
                url=f"https://www.arbeitsagentur.de/jobsuche/jobdetail/{refnr}",
                location=place, remote=True if s.get("homeoffice") else None,
                posted=o.get("aktuelleVeroeffentlichungsdatum", ""), ext_id=refnr,
            ))
    for j in out:  # descriptions for survivors only
        refnr = j["id"].split(":", 1)[1]
        try:
            enc = base64.b64encode(refnr.encode()).decode()
            r = get(f"{BA_BASE}/pc/v4/jobdetails/{enc}", headers=BA_HEADERS)
            if r.ok:
                j["description"] = clean_text(r.json().get("stellenangebotsBeschreibung", ""))
        except Exception:
            pass
        time.sleep(0.5)
    report["sources"]["arbeitsagentur"] = {"after_title_filter": len(out)}
    return out


# ---------------------------------------------------------------- company career pages (ATS)
def ats_greenhouse(slug):
    r = get(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs", params={"content": "true"})
    if r.status_code != 200:
        return None
    return [dict(title=x.get("title"), url=x.get("absolute_url"), location=(x.get("location") or {}).get("name", ""),
                 remote=None, posted=x.get("updated_at", ""), description=x.get("content", ""), ext_id=x.get("id"))
            for x in r.json().get("jobs", [])]


def ats_lever(slug):
    found_empty = False
    for host in ("api.lever.co", "api.eu.lever.co"):
        r = get(f"https://{host}/v0/postings/{slug}", params={"mode": "json"})
        if r.status_code != 200 or not isinstance(r.json(), list):
            continue
        if not r.json():
            found_empty = True  # try the other region before giving up
            continue
        return [dict(title=x.get("text"), url=x.get("hostedUrl"),
                     location=(x.get("categories") or {}).get("location", "") or "",
                     remote=(x.get("workplaceType") == "remote") or None,
                     posted=dt.datetime.utcfromtimestamp(x.get("createdAt", 0) / 1000).date().isoformat(),
                     description=x.get("descriptionPlain", "") + "\n" + x.get("additionalPlain", ""),
                     ext_id=x.get("id")) for x in r.json()]
    return [] if found_empty else None


def ats_ashby(slug):
    r = get(f"https://api.ashbyhq.com/posting-api/job-board/{slug}")
    if r.status_code != 200 or "jobs" not in r.json():
        return None
    return [dict(title=x.get("title"), url=x.get("jobUrl"),
                 location=", ".join(filter(None, [x.get("location")] + [s.get("location") for s in x.get("secondaryLocations", []) or []])),
                 remote=x.get("isRemote"), posted=x.get("publishedAt", ""),
                 description=x.get("descriptionPlain", ""), ext_id=x.get("id"))
            for x in r.json()["jobs"]]


def ats_personio(slug):
    r = None
    for tld in ("de", "com"):
        try:
            r = get(f"https://{slug}.jobs.personio.{tld}/xml", params={"language": "en"})
        except Exception:
            r = None
        if r is not None and r.status_code == 200 and "<position" in r.text or (r is not None and "<workzag-jobs" in r.text):
            break
        r = None
    if r is None:
        return None
    base = r.url.split("/xml")[0]
    root = ET.fromstring(r.content)
    jobs = []
    for p in root.findall("position"):
        pid = p.findtext("id")
        offices = [p.findtext("office") or ""] + [o.text or "" for o in p.findall("additionalOffices/office")]
        desc = "\n".join((d.findtext("name") or "") + "\n" + (d.findtext("value") or "")
                         for d in p.findall("jobDescriptions/jobDescription"))
        jobs.append(dict(title=p.findtext("name"), url=f"{base}/job/{pid}",
                         location=", ".join(filter(None, offices)), remote=None,
                         posted=p.findtext("createdAt") or "", description=desc, ext_id=pid))
    return jobs


def ats_smartrecruiters(slug):
    r = get(f"https://api.smartrecruiters.com/v1/companies/{slug}/postings", params={"limit": 100})
    if r.status_code != 200 or not r.json().get("totalFound"):
        return None
    return [dict(title=x.get("name"), url=f"https://jobs.smartrecruiters.com/{slug}/{x.get('id')}",
                 location=", ".join(filter(None, [(x.get("location") or {}).get(k) for k in ("city", "country")])),
                 remote=(x.get("location") or {}).get("remote"), posted=x.get("releasedDate", ""),
                 description="", ext_id=x.get("id")) for x in r.json().get("content", [])]


def ats_workable(slug):
    r = get(f"https://apply.workable.com/api/v1/widget/accounts/{slug}")
    if r.status_code != 200 or "jobs" not in r.json():
        return None
    return [dict(title=x.get("title"), url=x.get("url") or x.get("shortlink"),
                 location=", ".join(filter(None, [x.get("city"), x.get("country")])),
                 remote=x.get("telecommuting"), posted=x.get("published_on", ""),
                 description="", ext_id=x.get("shortcode")) for x in r.json()["jobs"]]


def ats_recruitee(slug):
    # slug is either the Recruitee company name or a custom careers domain (e.g. careers.hostaway.com)
    base = f"https://{slug}" if "." in slug else f"https://{slug}.recruitee.com"
    r = get(f"{base}/api/offers/")
    if r.status_code != 200 or "offers" not in r.text[:200]:
        return None
    return [dict(title=x.get("title"), url=x.get("careers_url") or f"{base}/o/{x.get('slug')}",
                 location=x.get("location") or ", ".join(filter(None, [x.get("city"), x.get("country")])),
                 remote=x.get("remote"), posted=x.get("published_at", ""),
                 description=(x.get("description") or "") + "\n" + (x.get("requirements") or ""),
                 ext_id=x.get("id")) for x in r.json().get("offers", [])]


ATS = {
    "greenhouse": ats_greenhouse, "lever": ats_lever, "ashby": ats_ashby,
    "personio": ats_personio, "smartrecruiters": ats_smartrecruiters, "workable": ats_workable,
    "recruitee": ats_recruitee,
}


def collect_companies(cfg, flt: Filters) -> list[dict]:
    """slug may be one value or a list of candidates; ats may be fixed or 'auto'.
    The first (ats, slug) pair with open roles wins and is cached in data/ats_cache.json as 'ats|slug'."""
    cache = load_json(ATS_CACHE_FILE, {})
    out, status = [], {}
    for c in cfg.get("companies", []):
        name, ats = c["name"], c.get("ats", "auto")
        slugs = [str(x) for x in (c["slug"] if isinstance(c["slug"], list) else [c["slug"]])]
        cached = cache.get(name, "")
        if "|" in cached and cached.split("|", 1)[0] in ATS:
            pairs = [tuple(cached.split("|", 1))]
        else:
            atss = [ats] if ats in ATS else list(ATS)
            pairs = [(a, sl) for sl in slugs for a in atss]
        postings, found, empty_hit = None, None, None
        for a, sl in pairs:
            try:
                res = ATS[a](sl)
            except Exception:
                res = None
            if res:  # a board with open roles wins
                postings, found = res, (a, sl)
                break
            if res is not None and empty_hit is None:
                empty_hit = (a, sl)  # valid-looking but empty (some ATS answer 200 for unknown slugs)
        if found is None and empty_hit and ats in ATS:
            postings, found = [], empty_hit  # explicitly configured ATS with no open roles today
        if found is None:
            status[name] = "no open roles found (check slug/ats in config.yaml)"
            cache.pop(name, None)
            continue
        if postings:
            cache[name] = f"{found[0]}|{found[1]}"
        kept = 0
        for p in postings:
            if not flt.title_ok(p.get("title") or ""):
                continue
            if not location_plausible(p.get("location") or "", p.get("remote")):
                continue
            out.append(job(source=f"career:{found[0]}", company=name, **p))
            kept += 1
        status[name] = f"{found[0]}/{found[1]}: {len(postings)} open, {kept} relevant"
        time.sleep(0.2)
    save_json(ATS_CACHE_FILE, cache)
    report["sources"]["companies"] = status
    return out


# ---------------------------------------------------------------- main
def main():
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text())
    flt = Filters(cfg)
    seen = load_json(SEEN_FILE, {})

    collected = []
    for fn in (collect_companies, collect_arbeitsagentur, collect_boards):
        try:
            collected += fn(cfg, flt)
        except Exception as e:
            report["errors"].append(f"{fn.__name__}: {e}"[:300])

    # dedupe: within this run and against everything seen before (by id and by company+title)
    new, keys_this_run = [], set()
    for j in collected:
        if j["id"] in seen or j["key"] in seen or j["key"] in keys_this_run:
            continue
        keys_this_run.add(j["key"])
        new.append(j)

    enrich_linkedin(new)

    for j in new:
        seen[j["id"]] = TODAY
        seen[j["key"]] = TODAY
    cutoff = (dt.date.today() - dt.timedelta(days=SEEN_RETENTION_DAYS)).isoformat()
    seen = {k: v for k, v in seen.items() if v >= cutoff}

    # one file per run, so a second run on the same day is never mistaken for an already-reviewed file
    out_file = CANDIDATES / f"{dt.datetime.utcnow():%Y-%m-%dT%H%M}.json"
    if new:
        save_json(out_file, new)
    save_json(SEEN_FILE, seen)
    report["new_candidates"] = len(new)
    report["collected_after_filters"] = len(collected)
    save_json(RUN_REPORT_FILE, report)
    log.info("collected %d, new %d -> %s", len(collected), len(new), out_file)
    for e in report["errors"]:
        log.warning(e)


if __name__ == "__main__":
    main()
