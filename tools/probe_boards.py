"""Probe feed URLs for remote job boards (debugging)."""
import re, requests
UA = {"User-Agent": "Mozilla/5.0 (job-radar personal job search)"}
urls = [
 "https://remotive.com/remote-jobs/feed/product",
 "https://remotive.com/remote-jobs/feed",
 "https://remotive.com/feed",
 "https://remotive.com/remote-jobs/product/feed",
 "https://remotive.com/api/remote-jobs?category=product&limit=200",
 "https://remotive.com/remote-jobs/product",
 "https://jobicy.com/api/v2/remote-jobs?count=100&industry=management",
 "https://jobicy.com/api/v2/remote-jobs?count=100&industry=product",
 "https://jobicy.com/feed/job_feed?job_categories=product-operations",
]
for u in urls:
    try:
        r = requests.get(u, headers=UA, timeout=30)
        body = r.text
        titles = re.findall(r"<title>(.*?)</title>", body)[:6] or re.findall(r'"(?:title|jobTitle)":\s*"(.*?)"', body)[:6]
        print(f"== {u}\n   {r.status_code} {r.headers.get('content-type')} len={len(body)} items~{body.count('<item>') or body.count('jobTitle') or body.count('\"title\"')}")
        print("   ", titles)
        if "remote-jobs/product" in u and "html" in (r.headers.get("content-type") or ""):
            print("   job links:", len(set(re.findall(r'href="(/remote-jobs/product/[^"]+)"', body))), "next-data:", "__NEXT_DATA__" in body, "ld+json:", body.count("application/ld+json"))
    except Exception as e:
        print("==", u, "ERROR", e)
