---
name: utility-split-estimation
description: >
  Estimate the landlord/tenant (owner/tenant) utility-cost split for an asset — per fuel
  (electricity, gas, water) — so the landlord share can be used as the SAVINGS BASIS for
  retrofit economics. This gates every retrofit IRR: savings only accrue to whoever pays
  the bill, so the split must be estimated properly from evidence, never defaulted to
  100%-owner or a round number. Combines building form, jurisdiction pass-through
  (RUBS) rules, the asset's OWN documents (leases, OMs, PCAs, audits), and live leasing
  evidence (apartments.com etc.), then records the estimate as an adjudicable verifier
  finding. Extensible by asset type — multifamily is shipped; office/retail/industrial are
  stubbed with their determining factors.
  Triggers on: "utility split", "landlord/tenant split", "owner/tenant utility split",
  "landlord share", "who pays the utilities", "utility responsibility", "RUBS",
  "utility recovery", "utilities included", "tenant pays electric", "savings basis",
  "master metered vs individually metered".
version: 1.0.2
---

# Utility-Split Estimation

Estimate what fraction of each utility (electricity, gas, water) is paid by the **landlord
(owner)** versus the **tenant (resident)** for one asset. Produce a per-fuel split with the
evidence for each, labeled **PRESUMED** vs **CONFIRMED**, a confidence note, and the single
question to ask the owner to confirm. Record the estimate as a verifier finding so it is
adjudicable, and — when Audette is in play — flag that Audette's landlord-share settings
must be updated to match the confirmed split.

## Why this matters (do not skip, do not default)

Retrofit savings accrue **only to the party that pays the bill**. If residents pay 90% of
the electric load, an electric-efficiency measure returns ~10% of its dollar savings to the
owner — and its IRR collapses accordingly. The landlord share is therefore the **savings
basis** for every measure's economics. A wrong or defaulted split silently mis-prices the
entire measure plan. **Never assume 100%-owner, never assume a round number, never carry a
prior asset's split forward.** Estimate it from this asset's evidence.

This is frequent, load-bearing work: it feeds `decarb-plan` P3 economics and any retrofit
IRR. Run it whenever an asset's owner/tenant utility split is unknown, stale, or unconfirmed.

## Core method (all asset types)

Work these four evidence sources **in order**, stopping to record what each yields. Sources
lower in the list refine or confirm what higher sources presumed; a document or a bill that
states responsibility outranks an inference from building form.

1. **SEARCH THE ASSET'S OWN DOCUMENTS FIRST.** Before any inference or web search, look in
   the asset's uploaded files — leases and lease abstracts, the Offering Memorandum (OM),
   PCAs, energy/water audits, operating statements (T-12), and utility bills frequently
   state utility responsibility outright ("resident pays electricity", "owner pays gas
   heating and hot water", a RUBS line item, an expense-stop clause). Use `list_files` /
   `search_files` then `read_file` / `search_documents` with queries like *"utilities",
   "resident responsible", "tenant pays", "RUBS", "master metered", "individually metered",
   "expense stop", "recoveries"*. A document statement is the strongest evidence short of
   the owner confirming — mark those fuels **CONFIRMED** with the document cited.

2. **Building form** (asset-type-specific — see the module for this asset's type below).
   Metering configuration and central-plant layout set the *presumed* split when documents
   are silent. Example (multifamily): garden-style, individually-metered units → most
   electricity/gas billed directly to residents → **low landlord share**; mid/high-rise with
   central plants (central boiler/chiller, house-metered common systems) → **higher landlord
   share**. Building form yields a **PRESUMED** split, never a confirmed one.

3. **Jurisdiction pass-through / RUBS regulations.** Whether and how a landlord may bill
   utility costs back to residents is regulated locally (submetering rules, Ratio Utility
   Billing System allowances and caps, prohibitions on certain pass-throughs, tenant
   protections). This bounds what the split *can* be regardless of building form — a
   master-metered building in a RUBS-permitted jurisdiction may still pass most cost through;
   the same building where RUBS is barred leaves the cost with the owner. Search the
   reference library first, then web search; cite every rule with its source and URL.

4. **Live leasing evidence.** Pull the property's current listings/brochures (apartments.com,
   the property's own site, Zillow rentals, etc.) via web search. Listings routinely state
   "utilities included" or itemize "resident pays electric/gas/water" — this is real,
   current, market-facing evidence of what residents actually pay and often confirms or
   corrects the building-form presumption. Cite the listing and its URL.

**Resolve per fuel, not per building.** Electricity, gas, and water frequently split
differently (e.g. residents pay in-unit electric, owner pays central gas heat + common-area
water). Estimate each fuel independently against the evidence above.

## Asset-type modules

Read the module matching this asset's property type before finalizing the building-form step.
Each lists the determining factors and how they map to a presumed split.

| Asset type | Module | Status |
| --- | --- | --- |
| Multifamily | `asset-types/multifamily.md` | **shipped** — full method |
| Office | `asset-types/office.md` | stub — determining factors listed |
| Retail | `asset-types/retail.md` | stub — determining factors listed |
| Industrial | `asset-types/industrial.md` | stub — determining factors listed |

If the asset type has only a stub, use the listed determining factors plus the core method
to produce a best estimate, mark the result **PRESUMED** with **low** confidence, and be
explicit in the owner question that the split is unconfirmed. Do not fabricate precision the
module does not yet support.

## Granularity rule (critical)

### Consumption allocation (when distributing whole-property utility data across building models)
Never split evenly by default. Allocate in this order: (1) carve out identified common/amenity loads
first (pool heater, clubhouse, exterior/corridor lighting — use the audit's end-use breakdown) and
assign them to the building/line-item where they belong; (2) allocate the remainder across residential
buildings weighted by GFA (adjust for known differences: floors, vintage, equipment); (3) state the
allocation method with the upload. An even split is only acceptable when buildings are genuinely
identical in GFA and use — and must still be labeled "GFA-weighted (identical buildings)".

Apply the split at the FINEST granularity the model supports — per building and per end-use — never as
one blended property-wide percentage. A blended % misattributes savings both ways: in-unit measures get
phantom landlord credit, and fully-landlord amenity measures get under-credited.

- Residential buildings with tenant-metered fuel: landlord share for that fuel = 0% in those building
  models. House-meter loads (corridor/exterior lighting, common HVAC) that live inside residential
  buildings keep a per-building landlord share for that fuel (typically electricity).
- Amenity/clubhouse/pool buildings (no tenants): landlord share = 100% for their fuels.
- **Master-metered ≠ 100% landlord.** A master-metered residential load is only ~100% owner if the
  owner ABSORBS it. If the jurisdiction permits RUBS, assume the owner rebills up to ~90% → net
  landlord share ≈ 10% for that load, unless documents show a true gross lease / no rebill. Never
  set a master-metered residential load to 100% by default. **The RUBS assumption is CONDITIONAL on
  the jurisdiction permitting RUBS — confirm it in step 3 (cite the statute); if RUBS is BARRED, the
  owner bears the cost (~100% on master-metered), not ~10%.**
- **Solar under Virtual Net Metering (VNM):** assume 80% of solar output value flows to the landlord
  (owner-captured) — but **ONLY after confirming the state/utility actually offers VNM / aggregated
  NEM / community-solar export** (check the reference library → PUC/utility tariff → cite the rule +
  URL). **If only behind-the-meter (BTM) net metering is available (no virtual/export aggregation),
  solar value = BTM self-consumption offset only** — owner-share on the owner-paid loads it displaces
  — NOT the 80% VNM credit. Never assume VNM without the jurisdiction check.
- If the model has NO separate amenity building (e.g. a property modeled as N identical residential
  buildings), set the tenant-metered fuel to 0% landlord across all modeled buildings and evaluate
  common-load measures (pool heater, clubhouse equipment) as standalone owner-paid line items outside
  the building models. Say explicitly which loads were handled this way.
- Only fall back to a blended % when the modeling tool cannot express per-building shares — and label
  the blend and its composition.

## Output contract

Produce, for the asset:

**Per-fuel split table** — one row each for **electricity, gas, water**:

| Fuel | Landlord share | Tenant share | Label | Evidence |
| --- | --- | --- | --- | --- |
| Electricity | e.g. 15% | 85% | PRESUMED / CONFIRMED | the specific document line / listing / building-form + jurisdiction basis, cited |
| Gas | … | … | … | … |
| Water | … | … | … | … |

- **Landlord share** is the fraction of that fuel's annual **cost** the owner pays (this is
  the savings basis). If only a metering configuration is known and not a dollar split,
  state the presumed configuration and the share it implies, and mark it PRESUMED.
- **Label each fuel** independently: **CONFIRMED** = a lease/OM/audit/bill or the owner
  states it; **PRESUMED** = inferred from building form, jurisdiction, or listings.
- **Evidence** cites the exact source for that fuel (document + page/line, or listing URL,
  or the building-form + jurisdiction rule). No uncited splits.

**Confidence note** — one short paragraph: how strong the overall evidence is, which fuels
are weakest, and what would move a PRESUMED fuel to CONFIRMED.

**The single question to ask the owner** — one precise, closed question that, once answered,
confirms the presumed fuels. Example: *"For each of electricity, gas, and water — are these
individually metered and billed directly to residents, master-metered and paid by ownership,
or billed back via RUBS? If RUBS, what allocation formula?"* Tailor it to what is actually
still open.

## Record as a verifier finding (adjudicable)

Record the estimate so it can be adjudicated (mirrors `decarb-plan` P2 conflict handling).
Call `verifier__record_finding` with:

- `asset_id` = the **Soapbox asset id** (not the Audette uid).
- `kind`: `data-quality`.
- `severity`: by materiality to the measure economics — **high** when the split is
  unconfirmed and drives a large electric or gas load (i.e. it swings IRRs materially),
  otherwise medium.
- `evidence[]`: the per-fuel splits with their labels and the source behind each.
- `sources[]`: every document, listing URL, and jurisdiction rule cited.
- A summary that states the per-fuel landlord shares and their PRESUMED/CONFIRMED labels.

Store the returned `finding_id`. In a `decarb-plan` engagement this finding is adjudicated at
**Gate 1** alongside the other baseline conflicts — do not duplicate an existing open
split finding; reference it (see the Cortland gas-split finding pattern in
`decarb-plan` P1/P2). Resolve it via `verifier__resolve_finding` once the owner confirms.

## Audette landlord-share settings

When Audette is in play for this asset, the confirmed split must be reflected in Audette's
account/asset-level **landlord-share settings** — Audette applies landlord share to compute
which savings accrue to the owner, so a mismatch there re-introduces the same mis-pricing
this skill exists to prevent. After the owner confirms the split, note (in the engagement
state / to the user) that the Audette landlord-share settings must be updated to match the
confirmed per-fuel split. Do not treat the split as fully applied until Audette reflects it.
