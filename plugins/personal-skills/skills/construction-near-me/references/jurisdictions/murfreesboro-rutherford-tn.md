---
slug: murfreesboro-rutherford-tn
jurisdictions:
  - City of Murfreesboro, TN
  - Rutherford County, TN (unincorporated)
last_verified: 2026-08-02
---

# Murfreesboro / Rutherford County, TN

Fast-growing metro southeast of Nashville. The city and the county run entirely separate permitting systems, and **Smyrna, La Vergne, and Eagleville each run their own as well** — so resolving jurisdiction is the first move on every query here.

The city is the best-instrumented jurisdiction in this profile: it publishes building permits as a **public, unauthenticated, queryable ArcGIS layer that includes a business-name field**. That single endpoint answers most questions about city sites without touching a browser.

## Boundary check

- **City limits layer:** `https://maps.murfreesborotn.gov/server/rest/services/City_Limits/MapServer` (also `Cityworks/City_Limits`)
- **Public GIS viewer:** <https://maps.murfreesborotn.gov/PublicGIS/>
- Rutherford County Building Codes issues permits for **unincorporated county only**. Anything inside Murfreesboro, Smyrna, La Vergne, or Eagleville goes through that municipality.
- County building-code zones: `https://maps.rutherfordcountytn.gov/server/rest/services/BuildingCodes/Building_Code_Zones/MapServer`
- Growth here is mostly at the edges, so a large share of queries land near a boundary. **Check both city and county when the site is on an arterial at the fringe** — Blackman, Barfield, Rockvale, Christiana, Walter Hill.

## Tier 0 — Open data / GIS

### City of Murfreesboro — building permits (primary source)

- **Endpoint:** `https://maps.murfreesborotn.gov/server/rest/services/BuildingCodes/Permits/MapServer/1`
- **Capabilities:** `Query, Map, Data` — public, no auth
- **Size:** 30,659 records, of which 30,347 are sanely dated. By year — 2023: 855, 2024: 836, 2025: 727, 2026 (partial): 325
- **Coverage/lag:** newest permit **2026-05-28** as of 2026-08-03 — roughly a **2-month lag**. 2026 monthly volume runs 43–92 permits. Don't read a quiet recent month as "nothing happening"; re-check freshness each run:

```bash
# Note the DATE literal — a raw epoch value in `where` errors out
curl -s -G "https://maps.murfreesborotn.gov/server/rest/services/BuildingCodes/Permits/MapServer/1/query" \
  --data-urlencode "where=PRMT_DATE <= DATE '2026-08-03'" \
  --data-urlencode "outStatistics=[{\"statisticType\":\"max\",\"onStatisticField\":\"PRMT_DATE\",\"outStatisticFieldName\":\"mx\"}]" \
  --data-urlencode "f=json"
```

**Key fields:**

| Field | Meaning |
|---|---|
| `PRMT_TYPE` | `101` = single-family detached · `102` = attached/multi-unit residential · `103` = commercial / non-residential |
| `BUS_NAM` | **Business name** — populated on most `103` records. This is the tenant, not the contractor. |
| `PRMT_DATE` | Epoch **milliseconds** |
| `PRMT_YEAR` | Integer — cheaper to filter on than the date |
| `ADD_NO` | Street number (detached sites) |
| `ADD_NOS` | Hyphen-joined address range (attached/multi-unit, e.g. `3504-3506-3508-3510`) |
| `ST_NAME` | Street name, **uppercase, no suffix** (`MEDICAL CENTER`, not `Medical Center Pkwy`) |
| `ST_TYPE` | Suffix, abbreviated (`PKWY`, `BLVD`, `PIKE`, `TRL`) |
| `UNIT_NO` | Unit count — how you spot multifamily |
| `GISLINK` | Parcel key — use for entity resolution |

Scope filter maps directly onto `PRMT_TYPE`: keep `103` and `102`, drop `101` unless a cluster indicates a subdivision.

**Working query** — commercial permits with named businesses, newest first:

```bash
curl -s -G "https://maps.murfreesborotn.gov/server/rest/services/BuildingCodes/Permits/MapServer/1/query" \
  --data-urlencode "where=PRMT_TYPE=103 AND PRMT_YEAR>=2025 AND BUS_NAM IS NOT NULL AND BUS_NAM <> ''" \
  --data-urlencode "outFields=PRMT_DATE,ADD_NO,ADD_NOS,ST_NAME,ST_TYPE,BUS_NAM,UNIT_NO,GISLINK" \
  --data-urlencode "orderByFields=PRMT_DATE DESC" \
  --data-urlencode "resultRecordCount=50" \
  --data-urlencode "returnGeometry=false" --data-urlencode "f=json"
```

**By street** — remember `ST_NAME` excludes the suffix:

```bash
--data-urlencode "where=ST_NAME='MEDICAL CENTER' AND PRMT_YEAR>=2025"
```

**True radius search** — pass a point and distance instead of a street filter:

```bash
--data-urlencode "geometry={\"x\":-86.44,\"y\":35.85,\"spatialReference\":{\"wkid\":4326}}" \
--data-urlencode "geometryType=esriGeometryPoint" --data-urlencode "inSR=4326" \
--data-urlencode "distance=1609" --data-urlencode "units=esriSRUnit_Meter" \
--data-urlencode "spatialRel=esriSpatialRelIntersects"
```

**Resolving "the corner of X and Y"** — `Cityworks/Named_Intersections/MapServer/0` maps intersection names to points. The name field is **`IntRds`** (format: `GATEWAY BLVD and MEDICAL CENTER PKWY`), and the layer is multipoint, so geometry arrives as `geometry.points[0]`.

```bash
curl -s -G "https://maps.murfreesborotn.gov/server/rest/services/Cityworks/Named_Intersections/MapServer/0/query" \
  --data-urlencode "where=IntRds LIKE '%MEDICAL CENTER%'" \
  --data-urlencode "outFields=IntRds" --data-urlencode "returnGeometry=true" \
  --data-urlencode "outSR=4326" --data-urlencode "f=json"
```

The `POINT_X`/`POINT_Y` attribute fields are **State Plane feet**, not lat/long — pass `outSR=4326` and read the geometry instead. Feed the result straight into the radius query above. Verified chain: intersection → WGS84 point → 1-mile permit search returns results.

**Other useful city layers** (same server): `Cityworks/Parcels`, `Cityworks/Zoning`, `Cityworks/Streets`, `Cityworks/Addresses`, `Planning/MTSU_Overlay`.

Services root for re-checking: `https://maps.murfreesborotn.gov/server/rest/services?f=json`

### Rutherford County

- **GIS root:** `https://maps.rutherfordcountytn.gov/server/rest/services?f=json`
- **No public permits layer.** Useful ones: `Planning/Planning_Zoning_Subdivisions` (zoning + subdivision plats), `Planning/Smyrna_and_LaVergne_Zoning`, `BuildingCodes/Building_Code_Zones`, `Cityworks/PlanningEngCodes`.
- County permit data is PDF-only — see Tier 1.

### Socrata

**None for permits.** The Socrata catalog returns zero permit datasets for this area. `murfreesboro.finance.socrata.com` exists but is a **finance/budget** portal only — don't waste a lookup on it.

## Tier 1 — Agendas, minutes, and reports

**City of Murfreesboro Planning Commission** (CivicPlus AgendaCenter, `CIDs=4`):
<https://www.murfreesborotn.gov/AgendaCenter/Search/?term=&CIDs=4,&startDate=&endDate=&dateRange=&dateSelector=>

- Meets **1st Wednesday 6:00pm** and **3rd Wednesday 1:00pm**, City Hall, 111 W. Vine St.
- Landing page: <https://www.murfreesborotn.gov/939/Planning-Commission>
- The AgendaCenter search accepts a keyword `term`, so search by street name to find every case on a corridor at once. Minutes name applicants and tenants far more often than agendas do.

**City monthly building permit summary** (PDF, by report code):
<https://www.murfreesborotn.gov/DocumentCenter/View/11466/City-of-Murfreesboro-Building-Report-by-Month>

**Rutherford County Regional Planning Commission:**

- Department: <https://rutherfordcountytn.gov/planning-engineering> · <https://rutherfordcountytn.gov/planningdept>
- Members/landing: <https://rutherfordcountytn.gov/planningcommissionmembers>
- Meets monthly — subdivision plats, site plans, rezonings. The submittal-deadline and meeting-date calendar is published as a standalone PDF each year under `rutherfordcountytn.gov/vertical/sites/.../uploads/`.
- **Agendas and minutes live in a SharePoint folder**, not on the county site — awkward to fetch and links rotate. Expect to fall back to search or manual checking.
- Zoning Board of Appeals: <https://rutherfordcountytn.gov/zoning>

**County monthly Building Permit Activity Reports** (PDF, unincorporated only, FY2019 → present):
<https://rutherfordcountytn.gov/bldg-code-reports>

Same page also carries **School Facility Tax Activity Reports**, which is a development-tax report and a good independent read on new residential construction volume.

**County construction projects page:** <https://rutherfordcountytn.gov/construction-projects>

**PlanRutherford** — the county comprehensive plan, useful for growth-area context: <https://www.planrutherford.org/plan>

## Tier 2 — Permit portals

**The city does not use Accela.** It uses:

- **Cityworks** — `https://app06.cityworksonline.com/CLIENT_MurfreesboroTN-public/login` ("Murfreesboro Plans Submittal", commercial plan review)
- **BluePrince** — `https://www.blueprinceportal.com/login` (permit & inspection registration)

Both are login-gated submittal portals rather than open public search. **Prefer the Tier 0 ArcGIS layer**, which is public and needs no browser.

County: no public online permit search found — permits are obtained in person at 1 South Public Square, Room 101, Murfreesboro. County activity is visible only through the monthly PDF reports.

## Tier 3 — Commercial real estate

National sites work here (LoopNet, Crexi, CommercialCafe, CommercialSearch). The Nashville metro brokerage market covers Murfreesboro well — search Colliers, CBRE, Cushman & Wakefield, and Avison Young Nashville retail listings for corridor site plans with named anchors.

High-activity corridors worth naming in searches: Medical Center Pkwy, Gateway, Rutherford Blvd, Memorial Blvd, Old Fort Pkwy, New Salem Hwy, Veterans Pkwy, Blackman Rd, Shelbyville Pike, Manson Pike.

## Tier 4 — News and economic development

- **Murfreesboro Voice**
- **WGNS Radio** — heavy local government coverage, including planning commission outcomes
- **Daily News Journal** (DNJ)
- **Main Street Media of Tennessee** — Murfreesboro Post, Rutherford Source
- **WKRN / WSMV / News Channel 5** (Nashville TV, covers larger projects)
- **Nashville Business Journal** — best CRE and corporate-relocation coverage
- **Rutherford County Chamber of Commerce** and the county economic development office — employer and groundbreaking announcements
- **TDOT Region 3** for road projects, e.g. N Thompson Lane (SR-268) and New Salem Hwy (SR-99)

## Gotchas

- ⚠️ **`aca-prod.accela.com/COR` is not Murfreesboro.** An earlier version of this research used it; Murfreesboro has no Accela instance at all. `aca-prod.accela.com/ccmd/` is **Carroll County, Maryland**. Accela agency codes are opaque — never guess one.
- ⚠️ **`planning.rutherfordcountytn.gov` no longer resolves** (DNS failure as of 2026-08-02) despite still appearing in search results. Use `rutherfordcountytn.gov/planning-engineering`.
- **`buildingcodes.rutherfordcountytn.gov` 302-redirects** to `rutherfordcountytn.gov` — follow redirects.
- **Date literals are required.** `where=PRMT_DATE > 1754179200000` (raw epoch) returns an error with no useful message. Use `where=PRMT_DATE > DATE '2026-08-03'`. Values come *back* as epoch milliseconds regardless.
- **One dirty future-dated row.** Unfiltered `MAX(PRMT_DATE)` returns 2027-09-27 — a single data-entry error. Always bound the max with `PRMT_DATE <= DATE '<today>'` or freshness looks a year ahead of reality.
- **`PRMT_YEAR` and `PRMT_DATE` disagree on some rows.** Filtering `PRMT_YEAR<=2026` still admits the 2027-dated record, so `PRMT_YEAR` is fine for cheap period buckets but useless for bounding dates. Filter on the field you're measuring.
- **`BUS_NAM IS NOT NULL` skews freshness.** Ordering the business-name subset by date suggests coverage ends in Feb 2026; the full layer actually runs to late May 2026. Check freshness against all rows, not a filtered subset.
- **`ST_NAME` holds no suffix and is uppercase.** Querying `'MEDICAL CENTER PKWY'` returns nothing; query `'MEDICAL CENTER'`.
- **Street number lives in two fields.** `ADD_NO` for detached, `ADD_NOS` for attached ranges. Coalesce both — `ADD_NOS` is null on most `103` records.
- **Mail kiosks and sales centers** appear as `103` permits with a business name (`CLARI PARK MAIL KIOSK`, `MEADOWLARK SALES CENTER`). They aren't businesses — they're proof a subdivision is actively building. Roll them into the subdivision.
- **The city permit layer lags ~5 months.** For anything more recent, planning commission minutes and local news are the only options.
- County records are PDF-only and cover unincorporated areas exclusively — a quiet county report doesn't mean a quiet area if the site is inside a municipality.
