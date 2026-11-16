"""Inspect Remotive's category page structure (debugging)."""
import re, requests
UA = {"User-Agent": "Mozilla/5.0 (job-radar personal job search)"}
r = requests.get("https://remotive.com/remote-jobs/product", headers=UA, timeout=30)
b = r.text
for m in list(re.finditer(r'"title"', b))[:3]:
    print("CTX:", b[max(0, m.start()-300): m.start()+500].replace("\n", " "))
    print("-----")
links = sorted(set(re.findall(r'href="(https://remotive\.com/remote-jobs/[a-z-]+/[^"]+)"', b)))
print("abs links", len(links), links[:5])
rel = sorted(set(re.findall(r'href="(/remote-jobs/[a-z-]+/[^"#?]+)"', b)))
print("rel links", len(rel), rel[:5])
print("scripts:", re.findall(r'<script[^>]*(?:id|type)="([^"]+)"', b)[:10])
print("load-more/api hints:", sorted(set(re.findall(r'(/api/[A-Za-z0-9/_-]+)', b)))[:15])
