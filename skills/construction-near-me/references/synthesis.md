# Synthesis

Turning scattered records into a list of projects. Read this before writing up any run.

---

## 1. Merge records into projects

The raw material is one row per *record* — a rezoning case, four permits, a listing, a news story. The report needs one row per **project**. Merging is judgment work; these signals do most of it.

**Strong evidence two records are the same project** (any one is usually enough):

- Same **parcel ID** — the single most reliable key. Planning cases and permits both carry it in many jurisdictions.
- Same street address, allowing for `1574 Medical Center Pkwy` vs `1574 MEDICAL CENTER PKWY` vs `1574 Medical Ctr Parkway`.
- Same **project or site-plan name** across an agenda and a listing ("Gateway Island Phase II").
- Same developer or property owner at adjacent addresses within a short window.

**Weaker evidence** — combine at least two, and mark the result `Likely`:

- Addresses on the same block with related permit dates
- A news story naming a business at a corner where a shell permit exists
- A listing describing a center that matches a subdivision plat

**Do not merge on:**

- Same contractor. Contractors build many unrelated sites.
- Proximity alone. Two permits 200 feet apart on a busy corridor are usually two projects.

**Multi-building sites.** A shopping center is one project with named tenants inside it, not eight projects — unless the user asked about a specific tenant. Outparcels (the freestanding pads at the front) are usually worth listing separately since they're what people actually notice going up.

**Phases.** Report phases separately when their statuses differ ("Phase I open, Phase II permitted"), together when they don't.

---

## 2. Identify the tenant

The single most valuable thing this skill produces, and the most common place to go wrong.

**Permits name the permit holder** — a general contractor, a developer LLC, or a property owner. That is not the tenant. `Commercial Restoration Company` is a contractor. `Gateway Island Holdings LLC` is an ownership entity.

Legitimate ways to establish a tenant:

1. A **business-name field** in the permit data itself, where the jurisdiction publishes one
2. A **CRE listing** naming the anchor or signed tenant
3. **News** or a **corporate/franchise announcement**
4. **Planning minutes** where the applicant described the user
5. A **sign permit** or **business license** at the address

When none of those exist, write `Tenant unknown` and describe what's known instead: "commercial shell, ~7,500 sq ft, retail zoning." That is a genuinely useful answer. An invented tenant is worse than none.

**Chain shells are recognizable but not certain.** A 2,200 sq ft building with a double drive-through on an outparcel is a coffee or fast-food user — say that as an inference, marked `Unconfirmed`, and never name a specific brand without a source.

---

## 3. Status vocabulary

Use exactly these. Consistency is what makes delta mode work.

| Status | Means | Typical evidence |
|---|---|---|
| `Proposed` | Announced or filed, no approval yet | Agenda item, news, listing |
| `Rezoning pending` | Needs a zoning change that hasn't passed | Planning commission agenda, council first reading |
| `Approved` | Site plan or rezoning approved, no permit yet | Minutes recording the vote |
| `Permitted` | Building permit issued, work not visibly started | Permit record |
| `Under construction` | Work underway | Inspection records, news, recent photos |
| `Open` | Operating | News, business listing, hours posted |
| `Stalled` | Approved or permitted but expired, withdrawn, or long-dormant | Expired permit, withdrawn case, no activity 18+ months |

Pick the **furthest-along** status supported by evidence, and date it. A project can be `Open` while a later phase is `Permitted` — that's two rows.

Note when the *record* status and reality likely diverge: a permit issued 14 months ago with no follow-up inspections is probably `Stalled`, not `Permitted`. Say which one you're inferring.

---

## 4. Confidence

| Level | Bar |
|---|---|
| `Confirmed` | An official government record, **or** named consistently by two independent sources |
| `Likely` | One credible source — a single news story, a single listing, an agenda item without follow-through |
| `Unconfirmed` | Inference, a rumor, a stale listing, or a single unverifiable mention |

Confidence applies to the **claim being made**. A permit proves a building; it does not prove the tenant. It's normal and correct to write: *"Building: Confirmed. Tenant (Ross): Likely — LoopNet listing only."*

**Drop anything with no citable source.** No exceptions — this is the rule that keeps the output trustworthy.

Two independent sources means genuinely independent. Three outlets reprinting the same press release is one source.

---

## 5. Apply the scope filter last

Gather everything, then filter, so you can report what was excluded.

**Keep:** commercial of any kind, tenant fit-outs, multifamily, named subdivisions, hotels, medical, industrial, institutional, and major public buildings.

**Drop:** single-family permits, additions, decks, pools, fences, roofs, trade permits (electrical/plumbing/mechanical only), signs, demolition without a replacement, and remodels with no change of use.

**Judgment calls:**

- A **demolition** permit at a commercial site is worth keeping — it's the leading indicator of a redevelopment.
- A **change of use** permit is worth keeping even when small; it usually means a new business.
- **Mail kiosks, sales centers, and amenity buildings** are subdivision infrastructure. They confirm a residential project is real and under construction, so use them as evidence for the subdivision rather than listing them as their own projects.
- A **single-family permit cluster** — 40 permits on one new street — is a subdivision. Report it as one project.

Count what you filtered and report the totals.

---

## 6. Rank the output

Lead with what the user would actually notice:

1. Largest and most visible projects nearest the location
2. Named businesses over unnamed shells
3. Nearer over farther
4. In delta mode, `NEW` and `CHANGED` above everything else

Put low-confidence and minor entries at the bottom under a "Also seen" heading rather than dropping them, so the user can judge for themselves.

---

## 7. Sanity checks before writing up

- Did you check at least one *naming* source (tier 3 or 4)? Permit data alone answers "what" but not "who."
- Is every row dated and linked?
- Does any row's status contradict its evidence date?
- Did anything obviously get double-counted across tiers?
- Are date conversions right? ArcGIS returns epoch **milliseconds**; a 1970 or 2050 date means a unit or data-entry error.
- Is the newest record much older than today? That's data lag — report it rather than implying nothing is happening.
- Are there dirty values (future permit dates, null addresses)? Filter them and mention it.
