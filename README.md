# Job Radar

Personal daily job finder for product roles (PM, PO, founding PM, EIR, venture builder, chief of staff, technical project manager).

## How it works

1. **GitHub Actions** (`.github/workflows/daily.yml`) runs `scrape.py` every morning (~05:17 Berlin).
2. `scrape.py` collects listings from:
   - **Job boards** via [JobSpy](https://github.com/speedyapply/JobSpy): LinkedIn, Indeed, Google Jobs — Berlin (any work mode) + remote searches for Germany, EU and worldwide.
   - **Bundesagentur für Arbeit Jobbörse** via its public Jobsuche API.
   - **Company career pages** (Greenhouse, Lever, Ashby, Personio, SmartRecruiters, Workable feeds) for the watchlist in `config.yaml`.
3. Hard filters (title include/exclude, excluded companies) and dedupe against `data/seen.json`.
4. New candidates land in `data/candidates/YYYY-MM-DD.json`. Run stats in `data/last_run.json`.
5. A daily **Claude scheduled task** reviews the candidates (language requirements, location/remote rules, fit), adds the matches to the Job Radar table, and reads feedback from the table to tune `config.yaml` and its review notes (`review_rules.md`).

## Tuning

- Search terms, title filters, watchlist companies: `config.yaml`
- Judgment rules used in the Claude review: `review_rules.md`
- Company feed status (which slugs were found): `data/last_run.json` → `sources.companies`

Manual run: Actions tab → *Daily job scan* → *Run workflow*.
