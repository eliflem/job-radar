"""Print a sample of raw listings from each remote board (for debugging filters)."""
import json, sys, requests
UA = {"User-Agent": "Mozilla/5.0 (job-radar personal job search)"}
def show(name, url, params=None, pick=lambda j: j):
    try:
        r = requests.get(url, params=params, headers=UA, timeout=30)
        print(f"== {name} {r.status_code} {r.headers.get('content-type')} len={len(r.text)}")
        data = pick(r.json())
        print("count", len(data))
        for x in data[:8]:
            print("  ", json.dumps({k: (str(v)[:70]) for k, v in x.items() if k in ("title","jobTitle","company_name","companyName","category","category_name","candidate_required_location","jobGeo","location","jobIndustry","jobLevel","tags")}, ensure_ascii=False))
    except Exception as e:
        print(f"== {name} ERROR {e}")
show("remotive product", "https://remotive.com/api/remote-jobs", {"category": "product"}, lambda d: d.get("jobs", []))
show("remotive search", "https://remotive.com/api/remote-jobs", {"search": "product manager"}, lambda d: d.get("jobs", []))
show("remotive categories", "https://remotive.com/api/remote-jobs/categories", None, lambda d: d.get("jobs", []))
show("jobicy product", "https://jobicy.com/api/v2/remote-jobs", {"count": 50, "tag": "product manager"}, lambda d: d.get("jobs", []))
show("jobicy industry", "https://jobicy.com/api/v2/remote-jobs", {"count": 50, "industry": "management"}, lambda d: d.get("jobs", []))
show("workingnomads", "https://www.workingnomads.com/api/exposed_jobs/", None, lambda d: d)
r = requests.get("https://weworkremotely.com/categories/remote-business-exec-management-jobs.rss", headers=UA, timeout=30)
print("== wwr exec", r.status_code, r.text[:200].replace("\n"," "))
