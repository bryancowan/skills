---
name: construction-near-me
description: Research what new buildings and businesses are proposed, approved, permitted, under construction, or recently opened near a specific location. Use when the user asks what's being built near them, what's going up on a road or at an intersection, what that construction site is, what new business is opening in a shopping center, what development is planned for a neighborhood, or wants a development pipeline check for a city, county, or corridor. Works for any US city or county — it discovers each jurisdiction's permit portal, planning agendas, and open data, then cross-references commercial real estate listings and local news to name the actual tenant. Do NOT use for hiring contractors, home remodel permits the user is pulling themselves, property valuation, or real estate investment advice.
---

# Construction Near Me

Answer "what's going up over there?" for any US location, with every claim sourced and dated.

The core difficulty: **no single source answers the question.** Planning agendas know about a project a year before permits exist but call it "Site Plan 2025-114, 4.2 acres, Parcel 091-05300." Permits know the address and contractor but usually not the tenant. Commercial listings name the tenant but not the status. News names the business but only for the big ones. The job is to pull records from each layer, **merge them into one project per site**, and report the merged picture with confidence levels.

## Scope

**Report:** new commercial construction (retail, restaurant, office, industrial, medical, hotel, mixed-use), tenant fit-outs of existing space, multifamily and apartment projects, named residential subdivisions, and major public/institutional buildings.

**Skip:** individual single-family home permits, additions, decks, pools, fences, roofing, HVAC and other trade permits, signage, and remodels. Count what you filter out and say so — "312 single-family permits filtered" is useful signal about an area.

**Window:** anything currently in the pipeline (proposed → under construction), plus anything that *opened* in the last ~12 months. Older completed projects only on request.

**Radius:** for a named point (intersection, address, "the corner of X and Y"), default to roughly **1 mile**. For a named road, cover the corridor. For a city or county, cover the whole jurisdiction but lead with the largest projects. Always state the interpreted scope in the report header; the user can override ("within 3 miles", "just that shopping center").

---

## Step 0 — Probe capabilities

Before researching, establish what this agent can actually do. This skill is designed to run on any agent, and the honest reporting of gaps matters more than pretending full coverage.

| Capability | Enables | Claude Code equivalent |
|---|---|---|
| Web search | Tiers 3–4, jurisdiction discovery | `WebSearch` |
| Fetch a URL | Agendas, news, most of everything | `WebFetch` |
| HTTP from a shell | **Tier 0 open-data APIs** — the highest-value tier | `Bash` + `curl` |
| Drive a browser | Tier 2 permit portals | `agent-browser` skill, Playwright MCP |
| Write files | Saving profiles and reports | `Write` |

If a capability is missing, keep going — every tier you *can* reach still works. Just record the gap for the Coverage section. Never silently omit a layer you couldn't check; an unchecked permit portal and an empty permit portal are very different answers.

---

## Step 1 — Resolve the location to its governing jurisdictions

**This is the step most often gotten wrong.** A site half a mile outside city limits is permitted by the county, appears on the county planning commission's agenda, and is invisible in every city system. Two adjacent corners of one intersection can fall under different governments.

1. Parse the input into a place plus its city, county, and state. If the user gave only a street name, confirm the city — street names repeat.
2. Determine whether the location is **inside city limits**, in **unincorporated county**, or **near the boundary**. Ways to check, cheapest first:
   - A city-limits layer in the jurisdiction's GIS (see `references/source-discovery.md`)
   - The county's own "we permit unincorporated areas only" map
   - Ask the user if it stays ambiguous and the answer changes which sources to use
3. **When in doubt, research both.** Tag every finding with the agency that produced it.
4. Watch for smaller incorporated towns inside the county that run their own permitting — they are easy to miss and often exactly where the growth is.

Restate the resolved scope at the top of the report.

---

## Step 2 — Load or build the jurisdiction profile

Look in `references/jurisdictions/` for a profile matching the area.

- **Found** → read it. Check `last_verified`. Spot-check one URL before trusting the rest; government sites reorganize constantly.
- **Not found** → follow `references/source-discovery.md` to find the sources, then **offer to save a new profile** using `references/jurisdictions/_template.md`. Don't save without asking.
- **Something in the profile is broken** → fix it, bump `last_verified`, and mention the correction in the report.

Profiles are the point. Discovery is the expensive part of this work, and it only has to happen once per area.

---

## Step 3 — Work the source ladder

Run tiers in order. Tiers 0–2 tell you *what and where*; tiers 3–4 tell you *who*. **You almost always need both halves** — don't stop after the permit data just because it returned rows.

### Tier 0 — Open data / GIS APIs (cheapest, best)

Many jurisdictions expose permits and planning cases as queryable endpoints: ArcGIS REST feature services, Socrata, CKAN, or CARTO. Where one exists, you get structured, filterable records in one request with no scraping. Some even carry a business-name field, which collapses tiers 2 and 3 into one call.

Query recipes and how to find these endpoints: `references/source-discovery.md`.

### Tier 1 — Planning commission and BZA agendas + minutes

The **earliest** signal. Rezonings, site plans, and subdivision plats surface 6–18 months before a permit exists. Minutes are better than agendas — they record the vote and often the discussion that names the tenant.

Also check: city council / county commission agendas (rezonings get a final vote there), design review boards, and any published monthly permit activity report.

### Tier 2 — Permit portal

Vendor-specific and usually JavaScript-driven: Accela, Tyler EnerGov, CityView, OpenGov, CitizenServe, eTRAKiT, Cityworks, BluePrince, SmartGov. Needs a browser. Use it when tier 0 has no endpoint, or to confirm status on a specific project.

Search by **street name only**, not full address — these portals match exactly and a wrong suffix returns nothing.

### Tier 3 — Commercial real estate listings

LoopNet, Crexi, CommercialCafe, CommercialSearch, plus regional brokerage sites. **This tier names tenants and anchors** before permits or news do — "junior anchor: Ross Dress for Less, delivering Q2." Also useful for finding out a center is being built at all.

### Tier 4 — News, economic development, and corporate announcements

Local outlets, the regional business journal, the chamber of commerce, and the county/state economic development agency. Best source for confirmed openings, council vote outcomes, and large employer announcements. Corporate press releases and franchise-development pages confirm chains.

---

## Step 4 — Merge records into projects

Read `references/synthesis.md` before writing anything up. It covers entity resolution, the status vocabulary, and confidence rules. In short:

- One **project per site**, not one per record. A rezoning case, three permits, a LoopNet listing, and a news story about the same corner are *one* project.
- Status vocabulary: `Proposed` · `Rezoning pending` · `Approved` · `Permitted` · `Under construction` · `Open` · `Stalled`
- Confidence: `Confirmed` (official record, or named by two independent sources) · `Likely` (one credible source) · `Unconfirmed` (single listing, rumor, or inference)
- **Never guess a tenant from a contractor name.** "Unknown tenant — commercial shell permit" is a correct and useful answer.
- Drop anything you cannot cite.

---

## Step 5 — Report

Render this in the conversation every time.

### Header

> **Construction near [interpreted location]** — ~[radius], [jurisdictions covered] · researched [YYYY-MM-DD]

### Findings table

| Project | What it is | Status | Confidence | Latest activity | Source |
|---|---|---|---|---|---|

Sort by relevance: nearest and largest first, or by status if the user asked about a stage. Keep source as a real link.

### Detail

A short paragraph per project for what doesn't fit the table — size, developer, unit or square-foot counts, expected opening, why it's uncertain. Skip this for minor entries.

### Coverage and gaps

State plainly which tiers were checked and which weren't, and why:

> Checked: city permit data through 2026-06 (ArcGIS), planning commission minutes Jan–Jul 2026, LoopNet, 4 local outlets.
> Not checked: county permit portal — no browser tool available in this session.
> Filtered: 312 single-family permits, 47 trade/sign permits.
> Known lag: city permit data typically runs 4–8 weeks behind.

### What's next

Offer, don't act:

- Write a dated report note to the Obsidian vault
- Save or update the jurisdiction profile with what was learned
- Widen the radius, extend the window, or dig into a specific project
- Name the manual checks a human could make (call the planning department, visit the site)

---

## Step 6 — Vault note (offer, never assume)

If the user wants it saved, write:

`Construction Watch — <Location> — YYYY-MM-DD.md`

```yaml
---
tags: [constructionWatch, localDevelopment]
location: "Medical Center Pkwy & Robert Rose Dr, Murfreesboro TN"
jurisdictions: [City of Murfreesboro TN]
radius: 1 mile
run_date: 2026-08-02
sources_checked: [arcgis-permits, planning-minutes, loopnet, local-news]
---
```

Then the same content as the chat report. **Propose the folder and confirm before writing** — do not file into a Johnny Decimal vault unprompted. If the vault uses JD, the `obsidian-jd-organizer` skill knows the placement rules.

The exact filename format matters because delta mode finds prior runs by it.

---

## Step 7 — Delta mode

If a prior report note exists for the same location, diff against it and mark each project:

- **NEW** — not in the prior report
- **CHANGED** — status moved (`Permitted → Under construction`); show both values
- **UNCHANGED** — still present, same status
- **DROPPED** — in the prior report, absent now. Investigate before declaring it dead; it may just be a source that went stale, which is a different finding from a cancelled project.

Lead the report with NEW and CHANGED — that's the whole reason for re-running.

---

## Rules

- **Every claim gets a date and a source link.** No source, no entry.
- **Distinguish "not found" from "not checked."** They mean opposite things to the reader.
- **Don't infer tenants.** A permit issued to a general contractor names the contractor.
- **Respect the sites.** Use published APIs where they exist, keep request volume low and sequential, and don't try to defeat logins, CAPTCHAs, or rate limits. Everything here is public record — if a source resists automated access, note it as a manual check instead.
- **Government data lags.** A permit dataset current through last quarter is normal. State the lag rather than implying the pipeline is empty.
- **Propose, don't act.** Saving profiles and writing notes are offers.

## Reference files

| File | Read it when |
|---|---|
| `references/source-discovery.md` | The area has no profile, or a profile's sources are broken |
| `references/synthesis.md` | Before writing up findings — every run |
| `references/jurisdictions/_template.md` | Saving a new profile |
| `references/jurisdictions/*.md` | The area has a profile |
