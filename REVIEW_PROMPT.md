# Daily review — instructions for Claude

You are running Elif's daily Job Radar review. Work quietly and finish with a short summary.

Artifact (the table Elif uses): https://claude.ai/artifact/AY7ZUbNJnguHpBF6JGLmSW
Repo: eliflem/job-radar (cloned at the path the add_repo result gives)

## 1. Load state
- Read `review_rules.md` (the judgment rules) and `config.yaml`.
- Read the artifact database with the ArtifactData tool:
  - collection `meta`, doc `state` → `{processed: [list of candidate file names], feedbackSeenAt: ISO time}` (may not exist yet).
  - collection `jobs` → every row (page with `query.limit: 1000` / `cursor`). Rows have
    `added, company, title, url, location, mode, why, source, key, vote ("up"|"down"|null), note, feedbackAt`.

## 2. Learn from feedback
Look at rows whose `feedbackAt` is newer than `state.feedbackSeenAt`.
- Read the 👍/👎 votes and notes as Elif's own words. Look for patterns (a company, an industry, a role type,
  seniority, a work setup) — not one-offs.
- Add each clear pattern as one short line under "## Learned from feedback" in `review_rules.md`
  (e.g. "👎 PM roles at agencies/consultancies — prefers in-house product teams").
- If a pattern is mechanical, also tighten `config.yaml`: add a company to `excluded_companies`, a regex to
  `title_exclude`, or a search term that should be added. Keep changes small and explainable.
- Commit with a message saying what changed and why, then push (`git pull --rebase` first).
  Pushing a config change re-runs the scan; that's expected.

## 3. Review new candidates
- List `data/candidates/*.json` (pull first). Process every file not in `state.processed`.
- For each candidate apply `review_rules.md` strictly, reading title, company, location and description.
  Use what you know about each company (does it have a Berlin office?) and the description for the language and
  remote rules. Skip anything whose `key` (company|title) already exists in `jobs`.
- For each one that passes, write a row to collection `jobs` with `ArtifactData` `batch` (≤50 writes per call, `op: "set"`, no `if_version` for new docs):
  - `doc_id`: first 16 hex chars of sha1(key) — compute with a one-line python call
  - `added`: today's date (YYYY-MM-DD, Europe/Berlin)
  - `company`, `title`, `url`, `source`, `key` from the candidate
  - `location`: short, human ("Berlin", "Remote · EU", "Remote · worldwide")
  - `mode`: "Remote", "Hybrid" or "On-site"
  - `why`: one short line on why it fits or what to double-check (≤ 110 chars, plain words)
  - `vote`: null, `note`: ""
- Never touch `vote`, `note` or `feedbackAt` on existing rows — those are Elif's.

## 4. Save state
Write `meta/state` with the updated `processed` list (keep the last 60 names) and `feedbackSeenAt` = now
(use `if_version` from your read when the doc exists).

## 5. Health check
Read `data/last_run.json`. If a whole source failed (errors for every board search, Arbeitsagentur errors, or many
companies "not found"), fix what you can in `config.yaml` (e.g. a company's ATS slug you can verify via its careers
page), push, and mention it in the summary.

## 6. Summary
Finish with 2–4 lines: how many new roles were added (name the 2–3 strongest), how many were skipped and the main
reasons, and anything you changed from feedback. If nothing new passed, say so in one line.
