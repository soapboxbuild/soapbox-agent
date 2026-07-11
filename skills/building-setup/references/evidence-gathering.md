# Evidence Gathering — Building Profile Recipes

Detailed recipes for Step 2 of the `building-setup` skill: consolidating one cited building
profile from documents, lease listings, and general web research, ranked
**documents > listings/records > general web**.

## a. Documents (highest authority)

Use `search_documents` against the asset's uploaded files, then read the relevant matches
(as-builts — HVAC/electrical/plumbing/structural; PCA; utility data; rent roll; OM). Extract
every building attribute present:

- Gross floor area (GFA)
- Number of floors
- Year built
- Construction type / building class (A/B/C)
- Systems & equipment (HVAC, envelope, DHW, controls)
- Occupancy / tenancy
- Address (confirm against other sources)

Cite each extracted field with the source **document filename** and the **retrieval date**
(the date you read it in this session).

## b. Lease listings

brave-search CRE listing sites (LoopNet, Crexi, CoStar-class) by asset name + address. Pull:

- Specs (GFA, floors, year built, class) to corroborate or fill gaps from documents.
- Tenancy & lease structure: single-tenant vs multi-tenant, NNN vs gross, WALT (weighted
  average lease term).
- Asking rent / sale comps, when present.

Cite each field with the **listing URL** and **retrieval date**.

## c. General web research

brave-search broadly for anything documents and listings didn't cover:

- County assessor / property records (parcel data, assessed value, legal description).
- Owner or property websites.
- Permits (renovation history, system replacements).
- News (ownership changes, major capital events).

Cite each field with the **web URL** and **retrieval date**.

## Reconciliation rules

- Consolidate all three sources into **one** building profile — not three separate profiles.
- **Provenance on every field**: source (document filename / listing URL / web URL) +
  retrieval date. A field with no source is not in the profile.
- **Ranking**: when sources disagree, prefer **documents > listings/records > general web**
  as the suggested resolution.
- **Conflicts are surfaced, not silently overwritten** — when two sources disagree (e.g. GFA
  from the PCA vs GFA from the LoopNet listing), report both values with their sources to the
  user rather than picking one and discarding the other.
- **Gaps stay unknown** — if no source has a value for an attribute, leave it unknown and flag
  it in the profile summary. **Never invent** a value to fill a gap.
