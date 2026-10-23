# Review rules (applied by Claude in the daily review)

These are judgment rules a keyword filter can't apply. Claude reads each candidate's
title, company, location and description and adds it to the table only if it passes.
Claude updates the "Learned from feedback" section as Elif leaves 👍/👎 notes.

## Who this is for
Elif — Product Manager, 7+ years (data, AI, automation-heavy products; ex-Taxfix self-employed product, now Babbel).
Based in Berlin, authorized to work in Germany. Languages: English and Turkish only.

## Must pass all
1. **Role**: product management or close cousins — PM, PO, technical/AI/data PM, founding PM,
   entrepreneur in residence, venture builder, founder associate, chief of staff, product ops,
   technical project/program manager in a product or tech context. Startup-flavoured generalist roles are welcome.
   Not: marketing, sales, account management, engineering, design, construction/industrial project management.
2. **Seniority**: mid-level or senior. Skip junior/intern/working student and head/director/VP/principal.
   "Lead" titles: include only if the description reads as a senior IC role, not people leadership of a PM org.
3. **Language**: skip if German (or any language other than English/Turkish) is required or clearly expected
   ("fluent German", "German C1", "Deutsch verhandlungssicher", "sehr gute Deutschkenntnisse").
   "German is a plus / nice to have" is fine. An ad written entirely in German counts as German required
   unless it explicitly says the working language is English.
4. **Location**:
   - Company has an office in Berlin → remote, hybrid or on-site in Berlin are all fine.
   - Company has no Berlin office → fully remote only. Remote may be worldwide, EU or Germany, but must be open to
     someone living in Germany (skip "remote, US only", "must be based in UK", required time zones far from CET).
     Occasional travel / monthly HQ visits are fine.
   - Hybrid or on-site in another city → skip.
5. **Not already in the table** (same company + essentially the same title).
6. **Never**: Babbel (current employer).

## When unsure
If the description is missing or ambiguous on language/location, include it and add a short note in the
`why` field (e.g. "No description — check language"). Missing a good job is worse than one extra row.

## Learned from feedback
(Claude appends patterns here, e.g. "👎 agency/consultancy PM roles", "👍 AI-native startups".)
- 👍 Elif flagged Finmid's "Entrepreneur in Residence (GTM)" as the kind of role she wants: startup EIR / founder-adjacent generalist roles spanning product, GTM and operations count even when they aren't pure PM.
- 👎 German-language job ads (PAQATO: "job post is in german") — apply rule 3 strictly: if the ad text is in German, skip it even when the title is English.
- 👍 AI-native product roles (applied to Typeform "AI Product Operations Lead" and Voyfai "Senior Product Manager (Builder)") — hands-on builder / AI product-ops roles at AI-focused companies are a strong fit; rank them up in `why`.
- 👎 Energy-domain PM roles that need sector expertise (1KOMMA5° "Heartbeat": "no relevant experience (Energy Management Systems, IoT…)"; Aurora Energy Research: "energy markets") — skip roles at energy/cleantech companies whose description requires energy-market, EMS/IoT or control-systems background; generic PM roles at such companies still count.
- ⚠️ Roles requiring deep ML expertise (NLP, computer vision, recommender systems) are a stretch (Air Apps: "I don't have this") — still include AI PM roles, but flag a hard ML/research requirement in `why`.
- ⚠️ Temporary / interim / fixed-term contracts (Darwin Recruitment 6-month interim PM: 👍 "içerik okay ama temp" — content fine, but temp) — still include if the role fits, but start `why` with "Temp:" so the contract length is visible.
- 👍 Marketplace / consumer e-commerce PM roles (Vinted "Marketplace", az "E-Commerce Web & Mobile", Cint "Exchange", AIOS consumer engagement) — a good fit; some US-hours overlap on a fully remote role (AIOS) was fine.
