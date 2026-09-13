# Source Discovery

How to find the development-data sources for a jurisdiction you've never researched before. Work top to bottom; stop when you have a usable source for each tier. Budget roughly 5–10 lookups — this is a one-time cost per area, and the result gets saved as a profile.

---

## 1. Identify the governing bodies

Answer these before searching for anything:

- What **city or town** is this in, if any?
- What **county**?
- Is the site **inside city limits** or **unincorporated**?

Searches that resolve it:

```
"<city> TN city limits map"
"<county> building codes unincorporated"
"<address or intersection> parcel <county> assessor"
```

Most counties state plainly that they permit unincorporated areas only, and list which municipalities run their own. Get that list — small incorporated towns inside a metro county are easy to miss and often where the new growth is.

A county **assessor / property lookup** is the most reliable arbiter: search the parcel and read which taxing city it reports.

---

## 2. Tier 0 — Find open data or GIS endpoints

Highest value per request. Try all three; many jurisdictions have one and don't advertise it.

### 2a. ArcGIS REST services

Most cities and counties run an ArcGIS server, and the services directory is usually public and unauthenticated.

Find the host by looking for a "GIS", "Maps", or "Property Viewer" link on the government site — typically `maps.<domain>`, `gis.<domain>`, or `<domain>/gis`. Then probe the services root:

```bash
curl -s "https://<gis-host>/server/rest/services?f=json"
curl -s "https://<gis-host>/arcgis/rest/services?f=json"
```

One of those two paths usually answers. You get back a `folders` list — scan it for anything like `Permits`, `BuildingCodes`, `Planning`, `DevelopmentServices`, `CommunityDevelopment`, `Zoning`, `Parcels`. Then descend:

```bash
curl -s "https://<gis-host>/server/rest/services/<Folder>?f=json"          # services in folder
curl -s "https://<gis-host>/server/rest/services/<Folder>/<Svc>/MapServer?f=json"   # layers
curl -s "https://<gis-host>/server/rest/services/<Folder>/<Svc>/MapServer/<id>?f=json"  # fields
```

Read the field list before querying — field names are wildly inconsistent between jurisdictions. Look for permit date, permit type, address parts, and any business/tenant/occupant name field.

Query a layer:

```bash
curl -s -G "https://<gis-host>/server/rest/services/<Folder>/<Svc>/MapServer/<id>/query" \
  --data-urlencode "where=ST_NAME='MEDICAL CENTER' AND PRMT_YEAR>=2025" \
  --data-urlencode "outFields=*" \
  --data-urlencode "orderByFields=PRMT_DATE DESC" \
  --data-urlencode "resultRecordCount=50" \
  --data-urlencode "returnGeometry=false" \
  --data-urlencode "f=json"
```

Useful parameters:

| Parameter | Use |
|---|---|
| `where=1=1` | Match everything |
| `returnCountOnly=true` | Cheap size check before pulling records |
| `returnDistinctValues=true` + `outFields=X` | Learn a coded field's value set |
| `outStatistics=[{"statisticType":"max","onStatisticField":"<date>","outStatisticFieldName":"mx"}]` | Find data freshness |
| `geometry` + `distance` + `units=esriSRUnit_Meter` + `spatialRel=esriSpatialRelIntersects` | True radius search around a point |
| `resultOffset` | Page past the server's max record count |

**Dates are asymmetric and this bites every time.** Query *with* a SQL date literal — `where=PERMIT_DATE > DATE '2025-08-01'` — because a raw epoch value in `where` errors out with an unhelpful message. Results come *back* as epoch **milliseconds**; convert before reporting.

Two related traps:

- A year field and a date field on the same layer often disagree on dirty rows. Filter on whichever field you're actually measuring.
- Check data freshness against **all** rows, bounded by today (`MAX(date) WHERE date <= DATE '<today>'`). An unbounded max gets thrown off by a single mistyped future date, and a max taken over a filtered subset reports that subset's coverage, not the layer's.

**ArcGIS Hub** is the other front door — try `https://hub.arcgis.com/search?q=<county>%20building%20permits` for downloadable datasets.

### 2b. Socrata

Search the catalog across every Socrata domain at once:

```bash
curl -s "https://api.us.socrata.com/api/catalog/v1?q=building%20permits&search_context=<domain>"
curl -s "https://api.us.socrata.com/api/catalog/v1?q=<city>%20permits&only=dataset&limit=20"
```

A hit gives a domain and a four-by-four dataset id. Query it with SoQL:

```bash
curl -s -G "https://<domain>/resource/<id>.json" \
  --data-urlencode "\$where=issue_date > '2025-08-01'" \
  --data-urlencode "\$q=MEDICAL CENTER" \
  --data-urlencode "\$limit=100"
```

Note: a city having a Socrata *finance* portal does not mean it publishes permits there. Check before assuming.

### 2c. CKAN / CARTO / plain downloads

```
"<city> open data portal"
"<county> data.<domain>"
site:<gov-domain> permits csv
```

Also look for a **monthly permit activity report** published as PDF or spreadsheet. These are common, often the only structured county-level source, and they list every permit issued that month with type and location.

---

## 3. Tier 1 — Find agendas and minutes

Identify the meeting platform from the URL pattern:

| Platform | URL fingerprint | Notes |
|---|---|---|
| CivicPlus AgendaCenter | `/AgendaCenter/Search/?term=&CIDs=<n>` | `CIDs` selects the body; search across archives by keyword |
| Granicus / Legistar | `<city>.legistar.com`, `granicus.com` | Has a searchable legislation database — very good for rezoning case history |
| CivicClerk | `<city>.civicclerk.com`, `portal.civicclerk.com` | |
| BoardDocs | `go.boarddocs.com/<st>/<org>/Board.nsf` | More common for schools |
| PrimeGov | `<city>.primegov.com/public/portal` | |
| Municode Meetings | `municode.com`, `<city>.municodemeetings.com` | |
| SharePoint / plain folder | one-off links | Awkward but common for small counties |

Searches:

```
"<city> planning commission agenda"
site:<gov-domain> "planning commission" minutes 2026
"<county> regional planning commission" agenda pdf
```

**Prefer minutes over agendas.** Agendas say "Site Plan 2026-042 — Parcel 091-05300." Minutes record the vote, the applicant's presentation, and frequently the tenant name.

Also worth finding: city council / county commission agendas (final rezoning votes), board of zoning appeals, and any published development-project tracker or dashboard.

---

## 4. Tier 2 — Identify the permit portal

Find it from the government's own Building/Codes/Permits page, then record the exact URL. **Never guess a vendor tenant code** — Accela agency codes in particular are opaque three- and four-letter strings that resolve to completely unrelated jurisdictions.

| Vendor | Fingerprint |
|---|---|
| Accela Citizen Access | `aca-prod.accela.com/<AGENCY>/` |
| Tyler EnerGov | `energov`, `<city>.tylerhost.net`, `selfservice` in path |
| CityView | `cityviewportal`, `<city>.cityviewportal.com` |
| OpenGov / ViewPoint | `opengov.com`, `viewpointcloud.com` |
| CitizenServe | `citizenserve.com/Portal` |
| eTRAKiT | `etrakit`, `<city>.etrakit.com` |
| Cityworks | `cityworksonline.com/CLIENT_<Name>-public` |
| BluePrince | `blueprinceportal.com` |
| SmartGov | `smartgovcommunity.com` |

Portal search tips that generalize:

- Search by **street name alone**. Full addresses fail on suffix and directional mismatches.
- Use a **date range**, not a permit number.
- Look for a "Development Review" or "Planning" tab alongside "Permits" — it holds site plans and rezonings.
- Results are usually paginated with a hard cap; narrow the date range rather than paging forever.

If no browser is available, record the portal URL in the profile anyway and report the tier as unchecked.

---

## 5. Tiers 3–4 — Tenant and confirmation sources

**Commercial listings.** LoopNet, Crexi, CommercialCafe, CommercialSearch. Also find the dominant regional brokerages — search `"<metro> retail leasing" broker` — since their own sites often post site plans with named anchors well before anything else.

**News.** Identify the actual local outlets rather than assuming. Search:

```
"<city>" new business opening 2026
"<city>" development "planning commission" approved
"<road name>" construction "<city>"
```

Look for: the daily paper, a local radio or TV newsroom, a regional business journal (these cover CRE deals closely), and any independent local news site.

**Economic development.** The city/county EDC, the chamber of commerce, and the state's economic development department announce large employers, incentives, and groundbreakings — often the only source for an industrial or corporate project.

---

## 6. Save the profile

Fill in `references/jurisdictions/_template.md` and **offer** to save it as `references/jurisdictions/<city>-<county>-<st>.md`. Record what failed as well as what worked — a note saying "no Socrata, no public ArcGIS, portal is EnerGov and requires a browser" saves the next run from repeating all of it.
