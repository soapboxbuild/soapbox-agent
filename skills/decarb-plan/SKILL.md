---
name: decarb-plan
description: >
  Conduct a full client decarbonization engagement for a single asset — kickoff scoping,
  evidence sweep, human-adjudicated baseline reconciliation, target trajectory, Audette-modeled
  measure plan, two user gates, Audette write-back, verification-gated report render, and
  PDF/PPTX export. Durable phase state at projects/<asset-key>/decarb-plan.json lets any
  session resume mid-engagement. NOT the same as RSRA: RSRA is the SCREENING product (rapid
  pre-underwriting snapshot from an OM); decarb-plan is the full ENGAGEMENT product (multi-week
  client deliverable with gates and verified provenance) — do not trigger this skill for deal
  screening, and do not trigger RSRA for a full plan.
  Triggers on: "decarbonization report", "decarb plan", "decarbonization roadmap",
  "full decarb report", "net zero plan for [asset]", "BPS compliance plan".
version: 1.8.5
---

# Decarb-Plan Engagement

You are conducting a **full decarbonization engagement** for one asset. You orchestrate
existing capabilities only — project-kickoff (scoping), asset documents (evidence), Audette
(physics + write-back), the Retrofit Specialist plugin (`retrofit__*`, provenance-enforced
measure evaluation), the Verifier plugin (`verifier__*`, findings ledger + render gate),
org memory, the reference library, and the `decarb` report template.

**Non-negotiable ground rules — apply in every phase:**

1. **No LLM arithmetic.** Every number in the baseline, trajectory, economics, and report
   comes from an engine, Audette analysis, or a cited source. CRREM pathway points come from
   crrem tooling; BPS milestones and fine exposure come from engines/Audette compliance
   analysis (`run_compliance_analysis`); simple percent-reduction math may use the
   cashflow/DCF engines. You never compute a reported number yourself. ⛔ **NEVER reimplement,
   "replicate," or port `compute_plan_economics` (or any MCP engine) into Python/bash and run the
   plan through your own code — even validated to the penny against a live call.** A local replica
   is a hand-rolled, non-provenanced figure that silently drifts when an input differs and fails
   the `evaluate_measure` provenance gate. Call the real tool; if its result is long, read the
   fields you need directly — long output is a display artifact, not a reason to route around it.
2. **The hierarchy is suggestion-only.** The reconciliation precedence — **measured
   utility/ESPM actuals > audit-reported 12-mo > Audette modeled > estimates** — produces the
   *suggested* resolution for each conflict. The human adjudicates ALL conflicts at Gate 1.
   Nothing is auto-resolved.
3. **The render gate is HARD and fails closed.** No report render without asset-scoped
   verification passing, or a documented override `{finding_id, override_reason, approved_by}`
   in state for every open high-severity finding **on THIS asset**.
   **⚠️ Check verification ASSET-SCOPED — always pass `asset_id`.** The render gate itself is
   asset-scoped (`verifier__list_findings({asset_id})`). But `verifier__verification_status` with
   NO `asset_id` is **portfolio-wide** and will surface high-severity findings from *other* assets
   (e.g. a different building's ESPM id) that do NOT block your render — do not chase or resolve
   them, and do not let them make you think you're blocked. Call `verifier__list_findings` /
   `verification_status` **with `asset_id` = this asset**; only open-high findings on THIS asset gate
   your render. (Chasing another asset's findings wastes the render's time budget and can cause the
   run to be cut off before it renders.)
4. **NEVER game or bypass the render gate.** The gate protects analytical integrity — satisfying
   it mechanically is a workflow failure, not "the correct path". Specifically:
   - **No self-certification.** Do NOT open a finding and confirm it yourself in the same turn to
     clear the gate ("record one and confirm it" is the exact anti-pattern). Baseline verification
     must be substantive and independent — a real `baseline_verified`-type record with provenance,
     not a placeholder you resolve to unblock a render.
   - **No `save_file` bypass.** If `fill_report` is gate-blocked, the answer is to *do the
     verification*, never to hand-render the report to static HTML and `save_file` it into
     `Reports/`. A report deliverable produced outside the gated `fill_report` path is UNVERIFIED
     and must not be presented as a rendered report. (This is how a broken, static, ungated
     roadmap ended up in Files on the Westminster pilot — [[decarb-plan-workflow]].)
   - **Headline-metric reconciliation.** Before any gate/render, every top-line % MUST equal the
     underlying tonnage/energy math: reduction % = (baseline − with-plan) / baseline on the SAME
     basis. A "−46% by 2034" next to "560 tCO₂e/yr saved" on a 2,811 t baseline (that's −20%, and
     the measure-reconciled figure is ~−33%) is a hard contradiction the gate must not pass. If a
     grid-inclusive vs measure-only figure differ, label each; never mix bases in one headline.
   - **CRREM provenance.** Pull the pathway from the `crrem` MCP `get_pathway` for the asset's
     actual region (US NA regional pathways are live — [[crrem-plugin]]). Put those points ONLY in
     `targets.crrem_pathway` (+ set `targets.crrem_meta` = country/property_type/region/scenario so
     the server can re-fetch and verify). There is NO inline per-year CRREM field — the legacy
     `trajectory[].crrem_target` was REMOVED and the render gate now BLOCKS any payload that uses it
     or ships a `crrem_pathway` that doesn't match `get_pathway` within tolerance. Never hand-type,
     interpolate, or eyeball CRREM values — if you can't reach the tool, STOP and say so rather than
     fabricating a curve. A directional/reference curve (e.g. LBNL/ULI Appendix G) may only appear if
     explicitly labeled "directional — pending asset-specific CRREM tool run"; never present a
     directional stranding year as a firm result.
     **On a RE-RENDER you MUST re-call get_pathway and repopulate targets.crrem_pathway — never
     rebuild the CRREM curve from saved state.** Stored state may predate the curve fix; the render
     gate now BLOCKS a decarb report whose crrem_meta is set but crrem_pathway is empty (it would
     otherwise silently drop the curve), so a from-state rebuild without a fresh fetch will fail.
   - **Grid emission factor — the CRREM carbon basis (HARD).** The building's carbon intensity in
     `targets.trajectory[]` (both BAU and with-plan) MUST be computed on a **forward, DECLINING** grid
     emission factor sourced from the **cambium MCP** — `get_emission_factors(gea_region=<asset US state
     abbrev, e.g. 'WA'>, scenario=<org default, else mid_case>, year)` — call `list_scenarios` if unsure
     which scenario applies. Use the returned **AER** (average rate) for **each year** of the intensity
     and BAU trajectory, and **LRMER** (long-run marginal) for per-measure carbon savings.
     **Never** compute the building's CRREM intensity from a **static, current-year eGRID subregion
     *average* held flat across all years** — that is the #1 cause of a false "already stranded"
     verdict. Two failure modes the gate/verifier must reject:
     - **Wrong / stale factor.** An all-electric building on a low-carbon grid (e.g. **Seattle City
       Light** ≈ all-hydro, ~0.03 kgCO₂e/kWh) is far cleaner than a static eGRID subregion average
       (NWPPc ≈ 0.29). Cambium's forward WECCNW curve (`mid_case` AER ≈ 0.16 kg/kWh in 2026 declining
       to ~0.01 by 2050) is the correct, region-consistent basis — it captures grid decarbonization
       that a single static eGRID mean does not. Do not use the regional eGRID mean as the headline.
     - **Flat BAU.** Cambium AER declines year over year, so the BAU carbon curve MUST slope **down**
       as the grid greens even with zero measures — a flat BAU against a declining CRREM pathway mixes
       bases and is a hard data error (compounds the "non-increasing trajectory" rule below).
     The eGRID/ESPM **location-based** GHG number (what ESPM reports, what a GRESB/lender sees) may be
     shown as a clearly-labeled **secondary disclosure**, but it is NOT the CRREM stranding verdict and
     must never be the headline carbon intensity plotted against the CRREM curve. If the two bases give
     opposite stranding conclusions, show both, labeled — never let the regional-average number stand
     alone as "stranded."
   - **Compliance overlays (CRREM + BPS).** Determine the asset's jurisdiction, then
     **auto-include** every standard that applies there **plus** CRREM (e.g. an asset in Seattle
     auto-gets Seattle BEPS + WSCBA + CRREM) — the user may override with an explicit instruction
     ("show only WSCBA", "drop CRREM"). The two overlay families populate different fields and
     must not be conflated:
     - **Carbon standards** (Seattle BEPS, Boston BERDO, NYC LL97) are stepped GHGI targets: populate
       per-year `targets.trajectory[].bps_target`, plus `targets.bps_label` (legend text, e.g.
       "Seattle BEPS (GHGI target)") and `targets.bps_source` (citation for those values). CRREM is
       unaffected by this and continues to flow through `targets.crrem_pathway` exactly as described
       above — never merge a carbon BPS target into the CRREM series or vice versa.
     - **Energy standards** (e.g. WA Clean Buildings Act / WSCBA, Energize Denver) are EUI-based,
       not GHGI-based: populate one entry per applicable standard in `targets.eui_compliance[]`
       (`standard`, `unit`, `building_eui`, `target_eui`, optional `compliance_year`, `status`,
       `source`). Never route an energy standard's target through `bps_target` — WSCBA has no
       stepped carbon trajectory value.
     - **When a fine regime applies, show the AFTER and the annual fine — not just current vs
       target.** On any `eui_compliance[]` entry with `status: "non-compliant"`, ALSO populate:
       (a) `projected_eui` — the building's post-plan EUI (the "after", in `unit`), so the panel
       shows current → target → after; and (b) `annual_fine_avoided` — the stabilized owner-borne
       fine ($/yr) the plan eliminates; and (c) `fine_schedule[]` = `{year, bau_fine, plan_fine}`
       per year across the compliance horizon, which renders the fine-avoidance **area chart**
       (BAU fine vs with-plan fine trending to $0 once the plan's `projected_eui` drops under the
       then-current target — step `bau_fine` up at each phased milestone, e.g. Energize Denver
       interim/final). Every dollar figure traces to the jurisdiction's fine formula cited in
       `source` — never fabricate. Fines are owner-borne (never rebilled to tenants), so the
       avoided fine flows 100% to the landlord in the value bridge (`pv_bps_fine_avoidance`).
     - **Every value is sourced, never fabricated.** Pull BPS target numbers from the
       `bps-compliance` skill's reference tables (BERDO/DC BEPS/WSCBA/LL97) and verify against the
       official jurisdiction portal before use. Every `targets.eui_compliance[]` entry carries a
       `source` citation; any trajectory year that sets `bps_target` requires `targets.bps_source`.
       If a value can't be sourced, do not guess it — say so and stop.
     - **Exempt is still shown.** A standard the asset is exempt from (e.g. below a size/age
       threshold) still gets an `eui_compliance[]` entry with `status: "exempt"` rather than being
       omitted — the exemption itself is the useful signal to the reader.
   - **RE-RENDER = REGENERATE, never re-render a stored data object verbatim.** A stored/previously-
     rendered `data` object (e.g. embedded in a prior report HTML or a saved "vN" state) may PREDATE
     template/schema/content changes. On any revision or re-render you MUST rebuild the full `data`
     object and re-apply EVERY pre-render rule below — do not assume the saved object "already has all
     changes." Concretely, re-running an old object silently drops: new fields (`annual_owner_savings`
     → blank RoC%/Landlord Savings columns), the null-vs-0 fine-avoidance rule (renders a misleading
     `$0` instead of `—`), and prose fixes (a stale editorial `dashboard.title`). If you only need a
     small presentation tweak use `patch_report`; otherwise regenerate from `state`, not from the old
     rendered payload. This is the general form of the CRREM-from-state rule above.
     **Do NOT `read_file` the prior rendered report HTML to "get the structure."** That file is a large
     (~50KB) HTML view; pulling it into context bloats the model's working set and, stacked on the
     Audette plan data, has stalled the final synthesis turn (the render hangs before it can emit
     `fill_report`). You already have the authoritative structure from the template **schema**
     (`get_report_resources` / `gather_report_data`); rebuild the `data` object from the `state` files
     (measures, findings, helper) + the live tool outputs (Audette plans, `crrem get_pathway`) only.
5. **Pre-render sanity checks (the gate/verifier MUST reject these — they are self-evidently wrong):**
   - **Emissions trajectory must be non-increasing.** A with-plan (or BAU) carbon curve that *rises*
     over time is a sign/axis bug — decarb emissions decline. Reject and fix the payload.
   - **At-RUL / bundled-capital-event incremental cost is POSITIVE.** The like-for-like replacement
     that must happen anyway is the baseline; only the *upgrade spec above it* is incremental. A
     re-roof is the baseline — only the **added insulation** is incremental (positive). A negative
     incremental ("insulation saves money vs the mandatory re-roof") is the cost model backwards.
   - **Tenant vs landlord savings are SEPARATE explicit columns** in the cashflow — never merged.
     Only landlord/owner-share savings capitalize into the value-creation bridge; tenant-side
     savings do not accrue to the owner (see owner-share discipline in recipe 8 + analytics standards).
   - **RUBS pass-through: net owner utility savings ≈ (landlord-capture %) × gross savings — often ≈$0
     (HARD — the verifier MUST check this).** Under a Ratio Utility Billing System (RUBS) the owner is
     a pass-through: it pays the master/utility bill and rebills ~(1 − capture%) to tenants, so it only
     BEARS `capture%` of the cost. A measure that cuts the bill by $X therefore returns only
     `capture% × $X` to the owner — the rest was tenant money that also disappears from the rebill.
     **Carbon ≠ cash on RUBS:** RUBS shifts who bears the COST, never who owns the EMISSIONS.
     Master-metered / RUBS-rebilled energy stays the owner's **Scope 1/2** (the owner holds the meter
     → operational control); only energy on a tenant's OWN direct utility account is Scope 3. So a
     measure on RUBS-billed common energy can cut the owner's reported carbon ~fully while returning
     only ~`capture%` of the cash. Keep the two boundaries separate — never reduce owner Scope 1/2
     just because energy is RUBS-rebilled, and never let carbon ownership follow the cost split.
     **Scope allocation follows system architecture (centralized → owner S1/S2; unitized/in-unit on
     tenant meters → tenant S3), derived from DOCUMENTS first (OM/PCA/as-builts/equipment schedule),
     then the Audette system schedule, then archetype — docs win; Audette often mis-categorizes.**
     At a 10% landlord capture, owner utility savings are ~10% of gross ≈ **$0/yr at plan scale**, NOT
     the gross figure. **Never credit the owner the gross (or 100%) utility savings, and never model the
     owner-favorable fuel-switch asymmetry** "owner keeps 100% of the gas cut while tenant meters absorb
     the new heat-pump electricity" — apply the locked `capture%` to the fuel BEING SAVED and net any
     owner-side load INCREASE from the switch. If, after applying capture, `capitalized_utility_savings`
     still dominates the bridge on a low-capture (RUBS/tenant-metered) asset, the split was not applied —
     reject and recompute. On such assets the value bridge is driven by **fine avoidance (100% owner —
     the owner pays fines, not tenants) + the capitalized exit uplift**, not operating savings.
   - **Headline value = capitalized exit uplift at the exit cap, and the waterfall must bridge to IT.**
     Report ONE value number, not two. Do not headline a PV-of-cashflows `net_value_creation` (e.g.
     $1.9M) while a separate `asset_value_impact` (annual NOI ÷ exit cap, e.g. $13M) sits in the
     per-year rows — that is two valuation methods in one report. The bridge terminates at the
     capitalized exit-value uplift = (stabilized annual NOI improvement ÷ exit cap), where the NOI
     improvement = net-owner utility savings (post-capture, per above) + owner-share ancillary +
     annual avoided fine. Fine avoidance may ALSO be shown as a cumulative/undiscounted figure for
     context (e.g. "$3.7M cumulative, ~$1.7M PV"), but the exit-value line is the headline outcome.
   - **Lead with the OPERATING return; label exit- and fine-dependence explicitly.** Report
     `irr_excl_exit` (operating IRR) alongside the exit-inclusive `irr_incremental`, and lead with
     operating. If a plan's operating IRR is BELOW the hurdle and it only clears on the capitalized
     exit uplift, say so in the headline ("clears the hurdle only on exit-value realization") — never
     present the exit-inclusive IRR as if it were the operating return (Cortland on Blake headlined
     ~40% while operating IRR was 5.7%). Never headline a plan that FAILS its BPS compliance as the
     recommendation without a compliance caveat up front.
   - **When fine avoidance dominates value, prove the fine is real and stress it.** A single avoided
     regulatory penalty must not silently drive most of net value: Congress Park capitalized a
     $583K/yr Energize Denver fine to ~$11.1M (99% of exit value) while the same plan told the owner
     to file the extension that eliminates the near-term fine. Before capitalizing any avoided fine,
     complete the BPS research (deadline, extension option, penalty rate — a **Gate-1** item, not a
     P5 afterthought) and confirm the fine is genuinely unavoidable/persistent. If fine avoidance is
     >50% of net value, present a **without-fine sensitivity** and a regulatory-persistence caveat;
     never headline value that rests almost entirely on a penalty the plan itself tells the owner how
     to avoid.
   - **Landlord-capture matches who BEARS the cost, not who pays the meter.** Two independent
     questions: (a) is the load metered per tenant, or master/common? (b) does the owner ABSORB the
     bill or REBILL it via RUBS? Do not collapse them:
     - **In-unit tenant-metered** (tenant pays the utility directly) → owner capture ~0–5%.
     - **Master-metered / landlord-paid** (central heating/DHW plant, elevators, garage/common
       ventilation, common lighting, amenity): the owner pays the master bill but that is NOT the
       same as bearing the cost. **If the jurisdiction ALLOWS RUBS, assume the owner recovers up to
       ~90% from tenants → net owner capture ≈ 10%**, unless documents show the owner absorbs it (a
       true gross lease with no RUBS, or an explicit statement). Only assume ~100% owner when the
       owner genuinely absorbs the utility. **Never read "master-metered" as "100% owner."**
     - Still do NOT price a common/central-plant load at the in-unit *blended* split (the
       elevator-regen −6%→+12% error) — but the correct number is the RUBS-recovery split (~10%
       when RUBS applies), not an automatic 100%.
     - **BPS fine avoidance is 100% owner** regardless of lease/metering.
     - **Solar under Virtual Net Metering (VNM): assume 80% of solar savings flows to the landlord**
       (unless docs state otherwise).
     - **VERIFY the RUBS and VNM legislation for the asset's jurisdiction — never assume it.** The
       ~10% RUBS capture and the 80% VNM solar credit are CONDITIONAL: check (reference library →
       web/`brave-search` + `web_fetch` → **cite statute/PUC rule + URL**) whether RUBS/submetering
       pass-through is permitted (**if BARRED → owner-borne ~100% on master-metered, not ~10%**) and
       whether Virtual Net Metering / aggregated NEM is available (**if only behind-the-meter NEM
       exists, solar = BTM self-consumption offset only, NOT the 80% VNM credit**). Record the
       RUBS + VNM determination + source as a Gate-1 finding.
     Reject any measure whose owner-capture equals the account default (commonly 15%) without this
     reasoning; record the correction as a `verifier__record_finding` (kind `data-quality`, verdict
     `conflict`) tying the measure to its true end-use capture from the 2C capture map.
   - **Measure equipment type matches the documented system.** Reject a measure whose equipment
     contradicts the PCA/as-built — e.g. an RTU/packaged-unit measure on a WSHP-loop building, or a
     DHW measure that assumes electric resistance when the PCA specifies gas boilers. Cross-check
     the Audette equipment survey against the PCA before screening; a mismatch is a
     `verifier__record_finding` conflict, not a silent screen-in.
   - **Plans are genuinely differentiated paths, not hold sensitivities.** Reject a two-plan report
     whose plans share identical capex, GHGI-reduction %, and ancillary revenue (that's one plan at
     two exit assumptions). Real plans differ on capex, carbon %, IRR, AND CRREM/stranding status
     (see recipe 8 "Plans"). The hold period maps to the path; it is not the differentiator.
   - **Both plan trajectories on the chart.** A two-path report must populate `targets.trajectory`
     with `planned_1` AND `planned_2` (+ `plan1_label`/`plan2_label`), not a single `planned` series.
   - **Soft ancillary/DR revenue is NOT capitalized as a perpetuity.** Reject `capitalized_ancillary_
     revenue = annual_DR ÷ exit_cap` on program-dependent PJM-DR/EV revenue; require risk-adjustment
     (haircut/PV over term) + a with/without-ancillary sensitivity. Flag any plan whose net value
     depends mostly on capitalized DR (fragile).
   - **Subscription measures judged on annual net, not capitalized-fee-vs-savings.** Capitalizing a
     cancellable subscription at the exit cap overstates the drag; require the annual net (savings +
     risk-adjusted DR − fee) and a one-time-RCx alternative for contrast (recipe 8).
   - **EV measures carry non-zero owner make-ready capex** (electrical/panel/trenching) — a $0-capex
     EV line under a host agreement is a red flag (host agreement zeroes hardware, not make-ready).
   - **Trajectory ↔ measure consistency (HARD — the verifier MUST check this).** Every measure with a
     material modeled energy/fuel reduction must show up as a corresponding bend in the plan curve it
     belongs to. A fuel-switch / electrification measure (e.g. gas WSHP boiler → air-source heat pump,
     gas DHW → HPWH) eliminates a large gas load and MUST visibly pull that plan's `planned_*` carbon
     line down in and after its install year. If a big electrification measure is in the measure list
     but the plan's trajectory doesn't reflect it (the curve is flat/unchanged through the install
     year), the trajectory and the measure model are inconsistent — that is a hard data error: record a
     `verifier__record_finding` (kind `data-quality`, verdict `conflict`) and fix the trajectory before
     render. Cross-check each plan's GHGI-reduction % against the sum of its measures' modeled
     reductions on the same basis; they must agree.
   - **Per-measure savings must reconcile with the measure's energy delta.** Every measure that
     removes a material energy/gas load MUST carry a proportional `emissions_savings_tco2e` AND owner
     `landlord_utility_savings` — a blank or near-zero attribution on a big fuel-switch (e.g. a gas
     boiler → ASHP eliminating ~1+ GWh) is a hard error, not an omission. If the modeled savings come
     out implausibly small, suspect an UNDER-CAPTURED BASELINE (an atypically low gas figure / GHGI for
     the building type — the classic tell) rather than a genuinely tiny measure: re-derive against the
     ESPM/utility actuals, or record a `verifier__record_finding` (data-quality) that the measure's
     impact is understated pending a meter-coverage fix — never silently ship the tiny number.
   - **No editorializing in report prose.** The deliverable states facts plainly — NO hype or
     rhetorical framing. Do not write lines like "two genuinely different strategies — same asset,
     different theses." The "genuinely differentiated plans" rule governs the MODELING (make the plans
     actually differ on capex/carbon/IRR/stranding), NOT the copy. **`dashboard.title`**, recommendation,
     summary_points, section intros, and executive_summary must be plain and specific — name the plan,
     the number, the driver; skip the adjectives and the meta-commentary. (`dashboard.title` should be
     a neutral label like "Decision summary", never a rhetorical headline.)
   - **Plan narrative goes in per-plan bullets, not a paragraph wall.** Populate
     `economics.plans[].summary_points[]` (3–5 short bullets each: what it deploys, headline
     IRR/value, the key trade-off/sensitivity) so each plan renders as a scannable list under its
     heading. Keep `executive_summary` to one short context line — do NOT cram both plans into a
     prose block there.
   - **Utility-rate escalation is applied** to the savings cashflow over the hold (e.g. ~3% elec /
     ~4% gas, or a cited regional forecast) and the assumption is stated — flat-nominal savings
     understate later years and the capitalized exit value.
   - **Regulatory/CRREM data comes from the tool, freshly.** Never carry a stale "tool unavailable"
     note from a prior session's saved state into a new report — re-attempt `crrem__get_pathway`
     (and record a finding if it genuinely errors); never ship "tool unavailable" prose as a result.
   - **Verify ALL math at report generation — do not trust LLM-computed figures.** Before render,
     recompute and reconcile every derived number in the payload: waterfall components sum to
     `net_value_creation`; each capitalization = annual ÷ exit cap; GHGI reduction % =
     (baseline − planned) / baseline; incremental = total − like-for-like; owner-share applied per
     the capture map; unit conversions correct (incl. the kWh→MWh/GWh scaling); every table total =
     Σ its line items; IRR consistent with the cashflow. Route the reconciliation through the
     verifier — any mismatch beyond rounding is a `verifier__record_finding` and **blocks the
     render** until resolved. The template's client-side sum check is a backstop, not the gate.
6. **Never fail silently.** Outages halt the phase with the standing reconnect message. And never
   fall back to hand-built report HTML when a tool/gate blocks — surface the blocker and stop.

**State ledger:** `projects/<asset-key>/decarb-plan.json`, conforming to
`skills/decarb-plan/state-schema.json`. Human-readable companion:
`projects/<asset-key>/decarb-plan.md`, registered in Files. Update BOTH at every phase
boundary. `<asset-key>` follows the project-kickoff convention: lowercase the asset name,
replace spaces with hyphens.

**Presentation standards** (apply to every number shown at a gate or in the report):

- **Energy intensity in kWh/m²; absolute energy scaled to magnitude.** Express intensity as
  kWh/m². For ABSOLUTE energy, scale the unit to keep the number readable: kWh, but switch to
  **MWh at ≥1,000 kWh and GWh at ≥1,000,000 kWh** (e.g. 5,929,000 kWh → **5.9 GWh** or **5,929 MWh**,
  never "5,929,000 kWh"). Convert gas from native units/GJ to the same energy basis. Areas in **m²**;
  carbon as **tCO₂e** and intensity as **kgCO₂e/m²**. No therms, kBtu, ft², or kBtu/ft² in output.
- **Max 2 significant figures displayed.** Round for display (e.g. 3.0 GWh, 130 kWh/m²,
  1,200 tCO₂e). Keep full precision in state/engine inputs; only the *displayed* figure is
  rounded.
- **Benchmarking: ENERGY STAR score first, then BPD.** Lead with the asset's ENERGY STAR
  score (1–100) where available. Where a peer comparison is needed, use the **Building
  Performance Database filtered by property type + climate zone** — **never national
  medians** and never an unfiltered peer set.

**Working files (helper) — read `skills/helper-files/SKILL.md`:** maintain exactly ONE growing
internal helper HTML for the engagement, saved via `save_file` to folder **`Helper Files`** as
**`[state.helper.start_date] - Helper Files - Decarb Plan.html`** (start date fixed at P0, stored
in `state.helper`). It is a rendered *view of state* — regenerate and re-save it at **every phase
checkpoint** (P2 foundation, P3 measures, P4 write-back). Fill the skeleton at
`skills/helper-files/references/skeleton.html`; the decarb **phase/gate checklist sections** are
P0 Kickoff · P1 Evidence · P2 Model Foundation (2A model · 2B baseline+calibration · 2C split ·
2D equipment) · GATE 1 · P3 Measures · GATE 2 · P4 Write-back+Verify · P5 Deliverables. **Do NOT produce standalone intermediate/gate HTML** (no `p1-baseline.html`,
no `building-model-verification.html`) — that material is checklist sections of the helper, and
**GATE 1 / GATE 2 are reviewed as the helper's checklist sections**, not as polished artifacts.
Only the **Report** and the **Delivery-Meeting Slides** are design-forward (`Reports/`, gate-only).

**Speed & efficiency (hard rules — learned from live engagements; violating these is what makes a
run slow):**

1. **Audette WRITES: batch ≤6 per turn, checkpoint state after each batch, NEVER fire a large
   parallel write burst.** The Audette OAuth token has no persisted refresh and dies mid-burst on
   ~10+ parallel calls — which kills the turn and loses any uncheckpointed progress, forcing a
   reconnect + resume. **Batch READS ≤6 per turn too (a large read burst stalls the session — see item 6); serialize/batch WRITES** (`create_building`,
   `edit_building_attributes`, `add_building_utility_data`, `submit_equipment_survey`,
   `create_custom_plan`). After each batch, write the done/pending building UIDs to state.
2. **Read the authoritative schema/reference BEFORE any structured write — never guess arg keys.**
   One `KeyError` retry-loop (e.g. the equipment-survey DHW keys) costs more than reading
   `references/audette-modeling-recipes.md` once. Blank numeric fields are `null`, never `0`.
3. **The state file is the ONE source of truth. Resume from the checkpoint; never recompute or
   re-enter values from memory.** Adjudicated values are **LOCKED** — tag them and never revert to
   a superseded number (the 15%→5% / 2031→2034 drift). Re-query IDs/UIDs from Audette; never
   hand-carry them across threads (clubhouse UIDs went stale this way).
4. **Validate the building model (count / GFA / UID set) in P2 step 2A BEFORE any upload or
   calibration.** Discovering a model error after uploads means redoing every upload.
   **Utility-data writes are CHECK-FIRST and idempotent.** Before `add_building_utility_data`, READ
   the building's existing utility data and compare — if the meters/periods are already present and
   match the source, SKIP the upload (or upload only the missing/changed periods). Never blind-upload
   data that may already be there — it double-counts consumption and corrupts the calibrated baseline.
   And if an upload call TIMES OUT or errors, do NOT blindly retry: **re-read the building first to
   see whether the write actually landed** — a timeout is frequently a false failure (the write
   succeeded server-side but the client gave up waiting), and a reflexive retry writes a duplicate.
   Only re-upload the periods that a re-read shows are genuinely missing.
5. **At each phase start, confirm the required tools/connectors are attached; STOP if missing**
   (don't fabricate — the ESPM tripwire). Checkpoint before every expensive/irreversible action so
   a dropped connection or deploy costs one batch, not the whole run.
6. **Parallelize independent READS, but cap each turn at ~6 calls** (documents, ESPM pulls,
   reference-library, memory recall, per-building plan/measure reads). One-at-a-time is too slow,
   but a large parallel burst (~10+ calls in a single turn — e.g. CRREM pathway + all 25 custom
   plans + state + template at once) stalls the managed-agent session's tool-result handshake and
   hangs the turn (this is what repeatedly stalled P5 at "fetch CRREM + plan data simultaneously").
   Fire ~6, wait, fire the next ~6.
7. **Kickoff in ONE consolidated pass.** When an engagement reference doc exists (it usually does —
   P0 step 1), pre-fill every kickoff answer from it + any needed research and present them **all at
   once for confirmation**; ask only the genuinely-open items. Do NOT walk 8 questions one-at-a-time
   across many turns (the first Westminster run burned ~30 min doing this).
8. **Resume cheaply. `switch_customer_account` ONCE per session, then cache it.** On resume, do the
   re-orientation in one or two small batches (≤6 calls each) — state file + account switch +
   required-tool presence check + the reconciled-model doc — then continue. Don't spend multiple turns re-loading
   context after every interruption (the original run re-oriented ~7 times).

---

## Resume Protocol (run this FIRST, always)

Before anything else:

```bash
cat projects/<asset-key>/decarb-plan.json 2>/dev/null
```

- **File exists:** validate it against `skills/decarb-plan/state-schema.json`
  (`phase` must be one of `P0|P1|P2|GATE1|P3|GATE2|P4|P5|done`). Resume at the recorded
  `phase`. **Never redo a completed phase** — every phase below is idempotent against the
  ledger: skip any step whose output is already recorded in state.
- **File missing:** this is a new engagement — start at P0.
- **Phase `done`:** tell the user the engagement is complete and where the exports are
  (`report.exports`); ask whether they want a revision cycle (re-enter P5) or a new engagement.
- **Post-Gate-1 baseline changes:** if resuming (or mid-flight) you discover new or changed
  baseline data after Gate 1 was passed, set `phase` back to `GATE1` and re-present **only
  the changed items** — not the full gate. Never silently update an adjudicated baseline.

---

## P0 — Kickoff

1. **FIRST, search the portfolio files for an engagement reference document.** Before asking
   the user anything, enumerate portfolio + asset files (`list_files` / `search_files`) and
   look for an **engagement reference** document (search terms: *"engagement reference",
   "engagement summary", "scope of work", "kickoff", "engagement letter"*). If one exists,
   read it and **pre-fill the kickoff answers from it** (goal, drivers, target, hold period,
   hurdle, cap rate, constraints, contacts, deadline), **citing the document** for each
   pre-filled field. Then ask the user **only what remains open** — do not re-ask questions
   the reference document already answers; surface the pre-filled values for confirmation.
2. Invoke the **project-kickoff** skill with project type **`decarb-plan`**
   (`cat skills/project-kickoff/project-types/decarb-plan.md` for the question set).
   Kickoff checks existing asset data before asking and saves
   `projects/<asset-key>/decarb-plan-kickoff.md`. Pass through the engagement-reference
   pre-fills so kickoff confirms rather than re-asks them.
3. Map the kickoff outputs into `state.kickoff` **field-by-field**:

   | Kickoff Store-as field | State ledger field |
   |---|---|
   | `goal` | `kickoff.goal` |
   | `drivers` | `kickoff.drivers` |
   | `primary_target` `{type, value, basis}` | `kickoff.target` `{type, value, basis}` |
   | `secondary_targets` | `kickoff.secondary_targets` |
   | `hold_period_years` | `kickoff.hold_period_years` |
   | `capital_events` | `kickoff.capital_events` |
   | `equipment_commitments` | `kickoff.equipment_commitments` |
   | `budget_ceiling` | `kickoff.budget_ceiling` |
   | `financing_appetite` | `kickoff.financing_appetite` |
   | `irr_hurdle` `{value, source}` | `kickoff.irr_hurdle` — source string **verbatim, never paraphrased** |
   | `turn_schedule` | `kickoff.turn_schedule` |
   | `disruption_tolerance` | `kickoff.disruption_tolerance` |
   | `existing_docs` | `kickoff.existing_docs` (also seeds `documents` in P1) |
   | `documents_expected` | `kickoff.documents_expected` |
   | `cap_rate` `{value, source}` | `kickoff.cap_rate` — source string **verbatim, never paraphrased** |
   | `utility_escalation` `{elec_pct, gas_pct, source}` | `kickoff.utility_escalation` — **pre-fill OUR DEFAULTS (3%/yr electricity, 4%/yr gas) and present for confirmation/override**; these feed the recipe-8 savings cashflow. If the user gives a figure or a doc cites one, use it (source verbatim); otherwise carry the defaults, labeled "Soapbox default". |
   | `stakeholders` | `kickoff.stakeholders` |
   | `review_cadence` | `kickoff.review_cadence` |
   | `deadline` | `kickoff.deadline` |
   | `primary_contact` | `kickoff.primary_contact` |

4. Create the state file with `asset` (`{id, name, portfolio_id}` — `id` is the **Soapbox
   asset id**), the mapped `kickoff` block, and `phase: "P0"`. Create the companion
   `decarb-plan.md` and register it in Files.
5. Set `phase: "P1"` and save.

---

## P1 — Evidence Sweep

Gather every source; record everything in state as you go.

1. **Asset documents:** enumerate with `list_files` / `search_files`, read each relevant
   document (audits, PCAs, utility data) with `read_file` / `search_documents`. Record each
   in `state.documents` as `{name, type: audit|pca|utility|other, storage_path, read}` and
   mark `read: true` once ingested.
2. **Retrofit register + findings ledger:** `retrofit__get_measure_state` for the asset's
   existing measure register; load existing open findings via `verifier__list_findings(asset_id)`
   — capture `finding_ids`; the gas-split style pre-existing findings must be adjudicated at
   Gate 1 alongside new conflicts, not duplicated — plus `verifier__verification_status` and
   `verifier__get_verification_checklist` so known data-quality issues carry into
   reconciliation.
3. **Audette pulls:** resolve the asset's Audette property, then its building model(s) —
   **one property may hold several buildings.** Pull `get_building_model_details`,
   `get_equipment_survey`, and `get_available_measures` for **every** building model on the
   property, plus any existing carbon-reduction/custom plan surfaced by the model details.
   Record the building uid(s) in `state.audette.building_uid`. When aggregating
   multi-building properties to the asset level: sum capex/savings/emissions; use
   **floor-area-weighted averages** for EUI and carbon intensity; never report one building
   as if it were the whole asset. (Never call bare `list_buildings` on a large account —
   resolve by property name.)
4. **ESPM actuals** where the asset is linked — these sit at the top of the reconciliation
   hierarchy.
5. **Memory:** `verifier__recall_expertise` for shared engagement lessons + org-bank memory
   recall for this asset/client.
6. **Research — jurisdiction rules and incentives:** `retrofit__search_reference_library`
   **FIRST**, web search second. **Every claim is cited with provenance `library|web`** in
   `state.citations` as `{claim, source, provenance, url}`. No uncited claims survive to the
   report.
7. **BPS coverage — verify at the jurisdiction's official source (DEFAULT).** Do not infer BPS
   applicability from size/type alone. Check the jurisdiction's covered-buildings registry for the
   asset's actual address — prefer a data export/open dataset where one exists (many run on the
   SEED Platform, e.g. Colorado's `co.beam-portal.org` "Covered Buildings List"), else navigate the
   specific portal/map with the **Web Browser MCP** (`browser_navigate` + `browser_snapshot`; plain
   web_fetch can't render these JS maps). Record whether the address is covered, its covered-building
   ID/baseline/targets if found, and tag `verified-at-source` vs `threshold-inferred` in
   `state.targets`. Full jurisdiction source registry + procedure live in the bps-analysis skill
   (Step 1.5).

   **7a. Compliance metric & pathway — a fine requires failing the GOVERNING pathway, not the hardest one.**
   Many BPS are **dual-pathway**: the owner elects the metric they comply on.
   - **Colorado Reg 28** (statewide, covered buildings ≥50k sqft): comply via **EITHER** the property-type
     **site-EUI** target (or the alternative % EUI reduction from the 2021 baseline) **OR** the **GHG-intensity**
     target. A building is compliant if it clears **either** pathway. Do **NOT** manufacture a penalty by
     assessing only the site-EUI pathway (the one a gas-retaining plan fails) when the plan clears the GHG
     pathway — the owner would simply elect the pathway they pass. If a plan clears any pathway, set that plan
     `compliant: true`, `waterfall.pv_bps_fine_avoidance: 0`, and no `cashflow[].bps_fine_avoidance`.
   - **Energize Denver** (Denver city only): **site-EUI** based, single metric — use EUI targets there.
   - **Metric consistency (gated).** The plotted `targets.trajectory[].bps_target` line and the plan
     trajectories (`planned`/`planned_1`/`planned_2`) MUST be on the **same metric that governs the fine**. If
     you claim a penalty (`compliant:false` or `pv_bps_fine_avoidance>0`), some series (BAU or the non-compliant
     plan) MUST visibly **exceed** `bps_target` in the penalty years — otherwise there is no fine on the plotted
     metric and the render is **blocked** (`validateFineConsistency`). If the fine is genuinely EUI-driven,
     plot the EUI trajectory vs the EUI target so the crossing shows; don't plot a carbon target and book an
     EUI fine against it. Grid decarbonization credits the GHG pathway but **not** the site-EUI pathway — keep
     that straight when deciding which pathway a plan actually elects.

Set `phase: "P2"` and save.

---

## P2 — Model Foundation (validate → calibrate → split → equipment; LOCK before Gate 1)

Establish and **LOCK all four foundation inputs before Gate 1 or any measure work.** Every rework
in prior engagements traced to a foundation input surfacing late or drifting (building set, split,
equipment, calibration). Gate 1 opens ONLY on a locked foundation. Record each with provenance in
`state`; any disagreement becomes a `verifier__record_finding` conflict for Gate 1 adjudication.

### 2A — Physical model validation (hard gate)

The Audette building count and per-building GFA are frequently auto-generated (footprint-matched
or total÷N) and WRONG. Before uploading utility/equipment data or calibrating, reconcile the model
against ground truth:

- Pull per-building footprints from the **ALTA / boundary survey** and **PCA** (search the asset's
  documents). These give real building count, per-building footprint/GFA, and structure type
  (residential vs clubhouse/amenity vs utility/mechanical).
- Confirm, and record each check as state: (a) building COUNT matches the survey; (b) each building's
  GFA matches its real footprint (not an even split); (c) the sum of building GFAs reconciles to the
  property total (flag any unexplained delta); (d) non-residential structures are identified and typed.
- If the model does NOT reconcile (wrong count, even-split GFAs, unreconciled total, mis-typed
  amenity buildings), **STOP**: record a `verifier__record_finding` (kind data-quality, asset_id,
  severity high) describing the discrepancy and surface it for adjudication. Do NOT upload utility
  data, calibrate, or generate measures against a model that fails validation — a 10–20% calibration
  "gap" is usually a building-model error, not an emission-factor difference.
- **Materialize the COMPLETE, correct building set here — before any per-building write.** If the
  model is short buildings (e.g. Audette has 17 but the survey shows 27), create ALL the missing
  buildings, assign the shared property_id, and lock the final UID set into state IN ONE validated
  step. Do not begin per-building edits/uploads on a partial set and discover the missing ones
  mid-stream (the first run churned 17→27 that way, forcing rework). Batch the `create_building`
  calls ≤6/turn per the Audette-write rule, checkpointing UIDs after each batch.
- **Never bulk-delete building models to "fix" an editable attribute — verify first, edit in place.**
  GFA IS editable: pass `gross_floor_area` (in m²) on the existing building; do NOT delete+recreate to
  change it. (Belmar deleted+recreated all 7 buildings on a false "GFA not editable" claim; Coalton
  edited the same field in place fine.) Deleting a building model is DESTRUCTIVE — it mints a new UID
  and orphans everything keyed to the old one (uploaded utility data, equipment surveys,
  carbon-reduction plans), forcing full re-upload/re-survey/re-create and compounding UID drift.
  Before ANY bulk delete: (a) confirm you are holding BUILDING-model UIDs, not the PROPERTY UID (the
  session context often surfaces the property uid — a property-uid-as-building-uid mixup plus an
  SF-read-as-m² unit confusion is what made Village "delete ~102 models" to fix a 10× GFA error that
  wasn't real); (b) confirm the attribute genuinely cannot be edited in place. Delete ONLY when the
  model SET itself is structurally wrong (e.g. per-unit auto-models you must consolidate), verified —
  and re-attach utility/survey/plan data to the new UIDs afterward.
- Only once the model reconciles (or the owner adjudicates the correct structure) proceed. Then apply
  the [[utility-split-estimation]] allocation rule: carve out common/amenity loads first, allocate the
  remainder GFA-weighted (never even), and set landlord shares per building/end-use (tenant-metered
  fuel = 0% on residential buildings, 100% on amenity buildings).
- For Audette mechanics — building rebuilds, landlord shares, equipment survey patterns — read
  `references/audette-modeling-recipes.md`.

### 2B — Measured-energy baseline + calibration

**Calibrate to measured energy — don't ask whether it's authoritative.** If measured whole-building
energy exists (ESPM actuals, utility bills) and is sane, extract it, upload it to Audette, and
adjust calibration factors until the model matches — rather than asking the user to choose between
measured and modeled. A residual 10–20% gap after calibration is almost always a building-model
error (revisit 2A), not an emission-factor difference. Pull ESPM via the energy-star tools (verify
they're attached first — the tripwire); read the energy sub-skill for the exact tool sequence.

**Calibration is a HARD gate on the economics.** An uncalibrated model inflates BOTH projected
savings and costs, so no measure IRR is trustworthy until it is calibrated. If the model's
first-year energy is **> ~10% off** measured (ESPM/bills) after calibration, **do NOT run measure
economics (P3)** — record a `verifier__record_finding` (kind `data-quality`, verdict `conflict`,
severity by materiality) and return to 2A/2B to fix it. (In the Cortland Rosslyn engagement the
raw model was **+35%** over ESPM; uploading actuals + calibrating brought it to within ~4% and
materially changed every measure's economics.) Record the post-calibration gap in `state.baseline`
with its source.

Build the baseline table in `state.baseline`. Required fields (each stored as
`{value, unit, source}`):

- Electricity: kWh/yr + $/yr
- Gas: native units (therms/m³) **and** GJ, + $/yr
- Owner/tenant utility splits
- GFA, unit count, floors, year built
- Equipment inventory with install years
- Emissions tCO2e — with the emission-factor source named (factors via Audette/CRREM tooling)

For **each field**: gather ALL candidate values with their sources.

- **All sources agree** → record the value with its source in `state.baseline`.
- **Sources disagree** → do NOT pick one. Create a conflict row in `state.conflicts`:
  `{field, candidates: [{value, source}...], suggested: {value, source, rule}, finding_id}`
  where `suggested` is computed from the hierarchy (measured utility/ESPM actuals >
  audit-reported 12-mo > Audette modeled > estimates) and `rule` names which hierarchy rule
  fired. Then call `verifier__record_finding` (kind `data-quality`, severity by materiality
  of the field to targets/economics, verdict `conflict`, with `evidence[]` — the candidate
  values and their sources — and `sources[]`) and store the returned `finding_id` on the row.

**NO auto-resolution.** Every conflict waits for Gate 1.

### 2C — Utility split (per fuel, per building)

**Read `metadata.utility_split` first** — if the asset already has a persisted split, use it (don't
re-derive, don't default to 100%). Only if absent, establish the owner/tenant utility split
**per fuel, per building** via the **utility-split-estimation** skill
(`cat skills/utility-split-estimation/SKILL.md`) — building form + jurisdiction RUBS rules + on-file
docs + leasing evidence — then **persist it to `metadata.utility_split`** (the canonical record read
by every future run; see that skill's persistence contract) in addition to `state.baseline` and the
Gate-1 finding. Never default to 100%-owner or a round
number. Tenant-metered fuel = 0% owner on residential; amenity/clubhouse buildings are typically
100% owner on both fuels. The split is the **savings basis for every retrofit IRR**, so it is a
foundation input, not a P3 afterthought. Record it in `state.baseline`; an unconfirmed or presumed
split is a `verifier__record_finding` conflict adjudicated at Gate 1.

**Capture is PER END-USE, and turns on who BEARS the cost — not one blended number per building.**
A single residential building has BOTH tenant-metered in-unit loads (in-unit electric
HVAC/appliances ≈ the tenant %) AND master-metered / landlord-paid loads (central heating/DHW
plant, elevators, garage ventilation, corridor/common lighting, amenity — spa, pool, laundry).
For the master-metered loads, do NOT apply the in-unit *blended* split — but also do NOT assume
100% owner. **Master-metered means the owner pays the meter, not that it bears the cost:**
- **If the jurisdiction ALLOWS RUBS, assume the owner rebills up to ~90% to tenants → net owner
  capture ≈ 10%**, unless documents show the owner absorbs it (true gross lease / no RUBS).
- **~100% owner only when the owner genuinely absorbs the utility** (documented gross lease, or
  RUBS not permitted). Amenity/clubhouse buildings with no tenants are the clean 100% case.
- **Solar under Virtual Net Metering (VNM): assume 80% of solar savings flows to the landlord.**
- **BPS fine avoidance is 100% owner** regardless.
Build a **capture map** in `state.capture_map` — every end-use → metering → RUBS-recovery status →
net owner-capture % — and **never inherit Audette's account-default landlord share (commonly 15%)
onto a master-metered end-use** (that under-credits it), **nor blanket it to 100%** (that
over-credits it when RUBS applies — the Cortland error). The Rosslyn central gas plant carried the
15% default when the correct figure was the RUBS-recovery split for its jurisdiction, not 15% and
not an automatic 100%. Where metering or RUBS status is unconfirmed, record a
`verifier__record_finding` conflict and resolve at Gate 1 — public listing sources (apartments.com,
Zillow) + the jurisdiction's RUBS statute are valid cited evidence.

### 2D — Equipment inventory (establish now — it drives P3 measure sequencing)

Gather the **real** equipment set + install years / remaining useful life (RUL) from the PCA / MEP
drawings / audit **now** — equipment type and RUL determine electrification timing (electrify at
end-of-life, DHW→HPWH at RUL), so the roadmap in P3 cannot be sequenced without it. Map each system
to its Audette representation per `references/audette-modeling-recipes.md` recipe 5 (e.g. hydronic
furnaces → native `hydronic_furnace`, not a fan-coil proxy; WSHP → `heat_pump.water_loop_heat_pump`).
Record capacities in **refrigeration tons** (Audette peculiarity — see recipe 5; DHW too), so the
write-back in P4 is already in the right unit. Record the inventory in `state`.
NOTE: the Audette `submit_equipment_survey` **write-back** happens in P4; here you establish the
inventory *knowledge* that feeds measure selection.

### Foundation lock

All four inputs — validated physical model (2A), calibrated measured baseline (2B), per-fuel/
per-building split (2C), equipment inventory (2D) — recorded in `state` with provenance, and every
disagreement captured as a verifier conflict. **Do not proceed to Gate 1 until the foundation is
locked.** Set `phase: "GATE1"` and save.

---

## GATE 1 — Foundation, Conflicts, Split/Exit, Targets (user)

Gate 1 opens **only on a locked Model Foundation (P2)**. Present these blocks, then **stop and wait
for the user**:

Present each adjudication/decision to the user via `ask_user_question` (one call per decision — options = the candidate values, recommended/suggested first, allow_other:true, context = the one-line why-it-matters), not as one markdown table wall. Fall back to one-decision-per-message lettered multiple-choice if the tool is unavailable.

**(a) Verified foundation** — the validated building model (count/GFA/types), calibrated baseline
(with the measured source + residual calibration gap), and every agreed field with value, unit, source.

**(b) Conflicts** — every row of `state.conflicts` as a **numbered decision**: candidates
with sources, the suggested resolution, and the hierarchy rule that produced the suggestion.
The user decides each one; the suggestion is never applied without their word.

**(c) Split & exit — the two economic-gating decisions.** Present the per-fuel/per-building
utility split (2C) and the exit assumptions (exit year + cap rate) for explicit confirmation.
These gate every IRR, so they must be adjudicated and **LOCKED here** — once locked, no later phase
re-enters a superseded value (past runs drifted 15%→5% / 2031→2034). Record the locked values with
`adjudicated_by: "user"` in `state.baseline` / `state.kickoff`.

**(d) Target trajectory** — computed from `kickoff.target.type`, engine math only:

| Target type | How the trajectory is computed |
|---|---|
| `crrem` | CRREM pathway points via crrem tooling → `state.targets.trajectory` |
| `bps-fine-avoidance` | Jurisdiction milestone table + fine-exposure via engines/Audette compliance analysis (`run_compliance_analysis`) → `state.targets.bps_milestones` + `state.targets.fine_exposure` |
| `percent` | Reduction-vs-baseline-year math via the cashflow/DCF engines |
| `net-zero-year` | Glide path to zero via engines/Audette analysis |

**Never LLM arithmetic** — if the engine for a target type is unavailable, the gate is
blocked (see Failure Handling), not approximated.

On the user's adjudications:

1. Write each decision into the conflict row's `adjudication`:
   `{value, source, adjudicated_by: "user", date}`.
2. Call `verifier__resolve_finding` for each adjudicated conflict's `finding_id`, with
   `resolution` `confirmed` or `dismissed` plus `note` (the adjudication rationale).
3. Promote adjudicated values into `state.baseline` with the adjudicated source.
4. On target confirmation, set `state.targets.confirmed_at`.

Set `phase: "P3"` and save.

---

## P3 — Measure Plan

**Ideation is delegated.** Invoke the **retrofit-advisor** skill for this asset — it reads the
Gate-1-adjudicated `state.baseline` and audit docs in `state.documents`, runs the full
measure-universe + source-audit cross-walk with provenance + confidence, and persists to the
Retrofit register. Do not re-derive measures here. When it returns, load the register with
`retrofit__get_measure_state({asset_id})` and continue.

P3 must have run the retrofit-advisor ideation (register non-empty) before building the roster —
do not assemble the Gate-2 roster from an empty or partial register.

1. Record the register's returned measure ids in `state.measures.register_ids`.
2. For candidates needing modeled physics (savings/carbon), run Audette
   `run_measure_design_analysis`. Read `retrofit__get_retrofit_playbook('baseline-discipline')`
   and **mark all modeled savings as provisional** per that playbook — modeled numbers are not
   measured numbers and are labeled as such through to the report.
3. **CapEx source — Soapbox Costing.** Before economics, source each screened-in measure's
   CapEx from the costing skill (Soapbox Costing MCP, `costing.mcp.soapbox.build`):
   `get_measure_capex` → capex low/base/high + `cost_breakdown` + `contingency_pct` + `escalation`
   + `references`; `estimate_service_upgrade` for any fuel-switch/electrification measure → the
   `electrical_capacity` UNVERIFIED range (never collapse it to a point estimate); `get_der_economics`
   for solar/storage/GHP; `get_energy_prices`/`get_tariff` for the OpEx delta feeding the same
   measure. Use `cost-bases.md` / engine defaults ONLY where the costing MCP has no coverage for
   that measure/market, and flag those cells low-confidence. This step SOURCES CapEx into
   `measure.cost` — it does not replace the plan's economics (capture, NPV/IRR, exit), which
   continue to consume these figures exactly as below. Surface the costing tool's `references`
   (citations) alongside each measure's cost so provenance survives to the report.
3b. **Incentives + revenue — search and apply by DEFAULT (never skip, never ask first).** For
   every screened-in measure, proactively search for and quantify:
   - **Incentives** — federal (IRA §48/48E ITC, §179D deduction, §45L, and direct-pay / elective-pay
     eligibility for this ownership type), state/local programs, and utility rebates. Sources:
     `retrofit__search_reference_library` (jurisdiction rules gathered in P1), the Costing MCP
     (`get_der_economics` carries ITC/DER incentives), and `brave-search` (DSIRE, utility program
     pages) as a labeled fallback.
   - **Revenue** — grid services / demand-response, SRECs/RECs, and net-metering / VNM export
     credits (solar VNM already enters at the 80% owner capture above).
   Write them into the measure's **Audette economics**: incentives REDUCE net CapEx — record
   **gross capex, incentive, and net capex separately**, each with its program citation as
   provenance; recurring revenue enters the measure cashflow. Guardrails (inherit the sanity
   checks above): **risk-adjust** program-dependent revenue (DR/EV/SREC), and **NEVER capitalize
   soft ancillary revenue as an exit perpetuity**. Every incentive/revenue figure carries a real
   source; use **null (not zero)** where none is found. This runs before step 4 so
   `evaluate_measure` consumes the net-of-incentive CapEx and the revenue line.
4. `retrofit__evaluate_measure` for **EVERY** register measure. Reminders:
   - `asset_id` = the **Soapbox asset id** (`state.asset.id`) — not the Audette uid.
   - `feasibility.score` is an **INTEGER 1–5**.
   - Every economic field must be engine- or source-provenanced; the tool refuses
     unprovenanced numbers — supply real sources, never fabricate provenance.
   - Cap rate for exit math comes from `kickoff.cap_rate` **with its verbatim source string**.
   - **Savings basis = the LOCKED per-end-use capture (from the 2C capture map, Gate 1).** A
     measure's dollar savings accrue only to the share the owner actually BEARS for **that
     end-use** — so a common-area or central-plant measure (elevators, garage ventilation, corridor
     lighting, central heating/DHW) does NOT use the building's blended in-unit split, but takes the
     end-use's **RUBS-recovery capture: ≈10% net owner where RUBS applies, ~100% only where the
     owner absorbs the utility** (documented gross lease / no RUBS). Solar under VNM = 80% owner.
     Never inherit Audette's 15% account-default, and never blanket a master-metered load to 100%.
     Set Audette's landlord-share for the measure to the end-use's locked capture or modeled owner
     savings are mis-priced. Do NOT re-derive or re-open the map here.
   - Record returned measure ids in `state.measures.register_ids`.
5. Roster labels come from the register — retrofit-advisor already screens candidates during
   ideation, so decarb-plan does not re-screen here.
6. **Roadmap phasing — sequence by decarb logic + equipment RUL, not independent IRR.** Read
   `retrofit__get_retrofit_playbook('staging')`. Order measures as: load-reduction / controls &
   retro-commissioning FIRST, then electrification of heating/DHW **timed to each system's RUL**
   (from the 2D equipment inventory) and to `kickoff.capital_events`, then supply (solar/storage)
   aligned to roof life. Screen by IRR ≥ hurdle *within* that sequence — never let a high-IRR
   measure jump ahead of the load-reduction it depends on. Write `state.measures.roadmap_phases`.
7. **Target-gap statement:** does the recommended set reach the confirmed target
   (`state.targets`)? If not, which defensive additions close the gap and at what cost —
   engine math only. Write `state.measures.gap_statement`.

Set `phase: "GATE2"` and save.

---

## GATE 2 — Roster, Roadmap, Gap (user)

Present, then **stop and wait for the user**:

Present each adjudication/decision to the user via `ask_user_question` (one call per decision — options = the candidate values, recommended/suggested first, allow_other:true, context = the one-line why-it-matters), not as one markdown table wall. Fall back to one-decision-per-message lettered multiple-choice if the tool is unavailable.

1. **Roster** — every measure under all four screening labels
   (recommended / defensive / screened-out / needs-data), each with its reason, including the
   named failing test for screened-out measures.
2. **Phased roadmap** — per-phase capex, NOI delta, and exit impact. **Engine numbers only.**
3. **Target-gap statement** — `state.measures.gap_statement`, with defensive closures priced.

The user confirms or edits the selection. Apply every edit via
`retrofit__update_measure_state` (never by editing state alone — the register is the system
of record for measure status). On confirmation set `state.measures.gate2_confirmed_at`.

Set `phase: "P4"` and save.

---

## P4 — Write-Back + Verification

1. **Audette write-back:** `create_custom_plan` with the confirmed measure set — or
   `update_custom_plan_measures` if `state.audette.custom_plan_id` already exists. Record the
   plan id in `state.audette.custom_plan_id`.
2. **Equipment survey write-back:** submit the equipment inventory established in P2 (step 2D) —
   and any Gate-1-adjudicated corrections — to Audette via `submit_equipment_survey`. (The inventory
   *knowledge* was gathered in 2D to drive P3 sequencing; this is the deferred *write*.) Record each
   submission in `state.audette.survey_corrections_submitted`.
   **BEFORE the first submit, read `references/audette-modeling-recipes.md` recipe 5** — the
   `equipment_survey` arg schema is free-form but the backend inferrer REQUIRES all 10 equipment
   groups present (each with `<group>_exists`), DHW needs `_central_distribution` +
   `_average_installation_year` keys, enum values are lowercase_snake (`hydronic_furnace`,
   `gas_heater`, …), and blank sizes/years must be `null` not `0`. Do NOT guess keys — copy the
   recipe's payload template. Hydronic furnaces map to `central_plant_heater_type=hydronic_furnace`
   (native match), never the fan-coil proxy. WSHP/water-loop heat pumps map to the `heat_pump` group
   (`water_loop_heat_pump`), never `central_plant_heat_pump` (recipe 5c). Submit in batches of ≤6
   buildings per turn (the Audette OAuth token dies on large parallel bursts) and verify each with
   `get_equipment_survey`.
   **⚠️ UNITS — every `*_size` capacity is in REFRIGERATION TONS, including DHW.** This is an Audette
   peculiarity verified from source: `KW_PER_TON=3.5169`, and the value you submit is stored and
   modelled verbatim as tons with NO conversion. Convert BEFORE submitting: MBH ÷ 12 = tons;
   kW ÷ 3.5169 = tons. Never submit kW, MBH, kBtu, litres, or gallons in a `*_size` field. The ONE
   exception is `air_handling_equipment_supply_air_rate`, which is CFM. There is **no** "schema says
   kW" comment anywhere in the Audette source or this skill — do not invent one to justify kW; if
   unsure, re-read recipe 5, do not guess.
3. **RENDER GATE (HARD):** call `verifier__verification_status` for the asset and write the
   result to `state.report.verification_status`. The deployed tool returns
   `{pass: boolean, open_high: number, open_total: number}` — store that shape verbatim.
   Enumerate open findings via `verifier__list_findings` before deciding overrides.
   - **Pass** → proceed to P5.
   - **Not pass** → resolve findings, or — only with explicit user approval — record a
     documented override `{finding_id, override_reason, approved_by}` in
     `state.report.overrides` for **each** open high-severity finding.
   - Neither → **no render. The gate fails CLOSED.** Do not dispatch the renderer, do not
     produce a partial report, do not summarize around it.

Set `phase: "P5"` and save.

---

## P5 — Report

Before dispatching any render, re-run `verifier__verification_status` and re-confirm the
gate (resume may have skipped P4's check).

1. **Assemble the report data object** per `templates/decarb/schema.json` — the authoritative
   schema the template consumes (its field names are exactly what the template's `populateReport()`
   JS reads). Include the **`economics`** object (per-plan `waterfall` 5 components + annual
   `cashflow` + `plans` + exit cap/year) built per **recipe 8** in `references/audette-modeling-recipes.md`.
   Record the object in `state.report.data`.

   The report is **dashboard-first**: the template renders a Decision Dashboard (compliance
   chip, hero KPI tiles, one-line recommendation, cumulative-cashflow J-curve sparkline)
   from `data.dashboard`, then a Scenario Comparison strip (renders whenever
   `economics.plans` has **2+ plans** — present at least 2 scenarios where applicable, e.g.
   near-term positive-IRR vs CRREM-aligned), then per-plan waterfalls + cashflows, roadmap,
   emissions trajectory, and appendices. **Populate `data.dashboard`** (every field nullable;
   values from the selected plan's engine outputs — never LLM-computed) and the per-plan
   comparison fields (`irr_incremental`, `ghgi_reduction_pct`, `compliant`). If `dashboard`
   is omitted the template falls back to the legacy executive-summary row.

   **CRREM pathway (`targets.crrem_pathway` + `targets.crrem_meta`):** source the REAL curve
   from the **crrem MCP server** — call `crrem get_pathway` with the asset's country, region,
   property type, and scenario (`get_climate_zone(zip)` returns a `crrem_region_hint`), and
   pass the points as `targets.crrem_pathway` (`[{year, carbon_kgco2_m2yr}]`) with
   `targets.crrem_meta {country, region, property_type, scenario}`. **Never fabricate,
   extrapolate, or hand-interpolate the curve.** The template draws it as a distinct dashed
   line alongside the stepped `bps_target` line — BPS drives fines, CRREM drives stranding —
   and annotates the stranding year. All trajectory series are kgCO₂e·m⁻²·yr⁻¹; convert
   per-ft² GHGI values before filling.

   **CRREM stranding is timing-only, never monetized.** Report stranding as the stranding YEAR /
   pathway alignment ONLY — never as a dollar, PV, capitalized value, cap-rate expansion, or
   brown-discount. `dashboard.downside_avoided` is the **PV of ACTUAL BPS fine avoidance ONLY**
   (real jurisdiction fines from `state.targets` fine exposure / the fines engine) — do NOT add a
   stranding-risk dollar value to it. If the asset faces no actual fines, there is no capitalized
   downside — set `downside_avoided` to 0 (or omit the tile); do not invent one from stranding.

   **Baseline/BAU carbon curve:** use the **actual Audette-modeled baseline carbon curve**
   (`state.targets` trajectory from Audette engine outputs, including grid-factor drift)
   for `bau`/`planned` wherever available — never a fabricated flat line.

   Section→source mapping:

   | Data key | Source in state |
   |---|---|
   | property / baseline | `state.baseline` (validated model + calibrated baseline, values + sources) |
   | dashboard | selected plan in `state.economics` + `state.targets` (compliance status, net value, IRR vs hurdle, capital ask, GHGI change, downside avoided, CF-positive year) |
   | targets / trajectory | `state.targets` (Audette baseline/planned carbon curves, BPS milestones, fine exposure) |
   | targets.crrem_pathway / crrem_meta | crrem MCP server `get_pathway` (region via `get_climate_zone(zip)` hint) — real curve only |
   | measures / roadmap | measure register via `state.measures.register_ids` + `state.measures.roadmap_phases` |
   | economics (waterfall + cashflow + plans, incl. per-plan `ghgi_reduction_pct`/`compliant`) | `state.economics` (recipe 8 — owner-share, incremental-over-LfL, fines as PV, capitalized savings/ancillary) |
   | data_quality | a **client-facing** confidence summary (`summary` + `items[]` dots) derived from `state.conflicts` / verifier findings — see the EXTERNAL-DELIVERABLE rule below. Do **NOT** pass an `adjudications[]` array (the internal reconciliation ledger is not rendered and must not be sent). |
   | sources | `state.citations` (cite the CRREM pathway export run) |

   **Choosing the recommended plan (`economics.selected_plan`) — by financial outcome, not decarb depth.**
   Set `selected_plan` to the plan with the better value-creation-bridge outcome — **net value creation at
   exit first, then incremental IRR** — NOT automatically the deepest-decarbonization plan. A capital-light
   plan that strands against CRREM but delivers materially higher net value / IRR (e.g. Plan 1 at +$351K /
   ~55% IRR vs a deep-electrification plan at −5% IRR) is usually the correct recommendation for a typical
   hold — select it and say so plainly. `dashboard.recommendation` must **lead with the chosen plan and the
   financial reason**, then note the alternative's tradeoff (stranding / ESG-mandate cases) — do NOT make
   "it depends on hold period" the headline. Give each plan a one-line `plans[].thesis` (the recommendation
   renders these as separated bulleted blocks); keep `plans[].summary_points[]` for the detailed bullets.

   **Value bridge & incremental IRR — CALL the cashflow engine `compute_plan_economics`. NEVER hand-compute IRR, capitalization, or PV (upholds "No LLM arithmetic", principle 1).**
   For EACH plan, call the `cashflow` MCP tool **`compute_plan_economics`** with the plan's per-year OWNER-SHARE
   line items and the exit terms; put the returned `cashflow`, `waterfall`, and `irr_incremental` into
   `economics.plans[]` **verbatim** — do not adjust or recompute them.
   - Inputs: `flows: [{year, incremental_capex, owner_utility_savings, ancillary_revenue, incentives, bps_fine_avoidance}]`
     (one row per hold year), `exit_cap_rate`, `exit_year`, optional `discount_rate` (default 0.08 for the fine PV).
   - `owner_utility_savings` is the **landlord share only** — from each Audette measure's
     `annual_mean_landlord_utility_cost_savings` (tenant share never capitalizes into the bridge). Apply the
     utility-rate escalation (recipe-8 defaults 3%/yr elec, 4%/yr gas) when building the per-year `flows`.
   - `bps_fine_avoidance` is nonzero ONLY when the plan is non-compliant on the **governing** pathway (see 7a).
   - The engine returns the derived money-math (noi/unlevered/cumulative, terminal exit-value delta =
     exit-year NOI uplift ÷ cap, capitalized owner savings & ancillary, PV of the fine schedule, net value
     creation, and IRR). A plan whose owner-share savings never cover its incremental capex comes back with a
     **null or negative IRR — that is a real, reportable outcome** (report it plainly), not a tool failure.
   - The decarb engagement does **not** carry the asset's going-in NOI/purchase price — so do **NOT** use
     `run_dcf` / `run_intervention_irr` (those model a base-DCF + single measure and need going-in NOI);
     `compute_plan_economics` is the plan-level incremental engine for decarb.
   - If the tool returns a validation error, FIX the inputs and re-call — never fall back to hand-computing the
     bridge, and never report "cashflow engine unavailable." The server-side render gate independently
     recomputes IRR/net-value via this same engine and BLOCKS on divergence, so a hand-entered figure will fail.

   **⚠️ EXTERNAL DELIVERABLE — no internal-process language anywhere in the report data.**
   The report is sent to external parties (owners, lenders, buyers) who have **no context**
   for our internal workflow. Nothing you put in ANY field — exec summary, dashboard, plan
   `label`/`name`, `data_quality.summary`/`items[]`, methodology, findings — may reference our
   internal process. Banned terms/patterns: **"Gate 1/2" / "Gate-1"/"Gate-2" / "at Gate…" /
   "locked at gate"**, **"adjudicated" / "adjudication" / "adjudicated_by"**, **"verifier" /
   "verification gate" / "Confirmed finding &lt;id&gt;" / raw finding IDs**, **"P0–P5" / "phase N"
   / "workflow" / "roster"**. Rephrase in client terms: instead of *"Utility split: Locked at
   Gate 1 — audit confirms…"* write *"Utility split confirmed by the AEI energy audit
   (475250-EA1)."*; instead of a plan label *"Solar (No ITC) — full Gate-2 roster ✓ Selected"*
   write *"Solar (No ITC) — Recommended"*. Confidence and provenance are welcome; the internal
   machinery that produced them is not.

2. **Render via `fill_report` — the SAME path RSRA uses (default; do not hand-write HTML or draw
   charts).** Call `fill_report(template: 'decarb', data: <the object from step 1>, title: "<Asset> — Decarbonization Roadmap")`.
   The server injects the JSON into the template's `<script id="report-data">` block and the
   template's own JavaScript renders every section and every chart from it — the **decision
   dashboard + J-curve sparkline**, the **scenario comparison strip**, the **value-creation
   waterfall SVG** per plan, and the **emissions trajectory with the CRREM pathway curve**.
   You write NO report HTML and draw NO charts — your only job is to compute the data
   object. (This mirrors rsra exactly. The old `[[TOKEN]]` / `get_report_template` + agent-fill
   path is retired — `templates/decarb/layout-agent.html` is now a client-render template.) The
   render is verifier-gated server-side; if blocked, fix findings and retry. Record
   `state.report.render_iterations` starting at 0.

3. **Revision loop — DATA-ONLY.** On user revisions, recompute the data object and call
   `fill_report(same artifact_id, template, updated_data)` — and NOTHING else (increment
   `state.report.render_iterations`); on approval export **PDF and/or PPTX**. NEVER `save_file` a
   hand-built report and NEVER hand-edit or reproduce the template's inlined HTML / chart /
   waterfall renderers to "apply" a revision — the template owns all rendering and is re-fetched
   fresh on every `fill_report` (so a re-fill also picks up any template fixes; a baked artifact
   does not). Hand-rebuilding mangles charts, drops blocks, reintroduces overflow, and bypasses the
   gate. You only ever touch the data payload.

   **Small presentation-layer tweaks → `patch_report`, not a full re-render.** For a minor edit
   after the report exists — reword a sentence, adjust a `data_quality`/`methodology` note, fix a
   non-cascading value (address, year built, a citation), or hide a section (set its key to
   `null`) — call **`patch_report(artifact_id, patch)`** with ONLY the changed fields (a JSON
   Merge Patch). It loads the persisted data object, merges your delta, and re-renders in place —
   no recomputation of the whole data object, far cheaper, and it re-runs the same verifier gate.
   `patch_report` rejects analytical fields (`economics`, `targets`, `dashboard`, …): any change
   to a headline number — or renaming a plan / reordering sections — still goes through a full
   `fill_report(same artifact_id, updated_data)` so the figures re-derive from state and re-pass
   the gate.
4. **Register the deliverable in Files.** `fill_report` already persists the fully-rendered HTML
   report to `Reports/` for you (server-side) — do **NOT** `save_file` the report HTML yourself
   (you don't hold the rendered ~80KB string, so a manual save would only write a broken stub).
   Just write all export paths (PDF/PPTX) to `state.report.exports`.
5. **Retain lessons:** call `verifier__retain_shared_expertise` with the generalizable,
   client-anonymous lessons from this engagement (reconciliation patterns, playbook gaps,
   jurisdiction findings). It will refuse content that identifies the client or asset —
   **never rephrase, strip, or restructure content to work around a refusal.** A refusal
   means the lesson is not generalizable; drop it.

Set `phase: "done"`, update the companion `decarb-plan.md`, and save.

---

## Failure Handling

Named blockers, never silent: Audette/verifier/renderer outages halt the phase with the
standing reconnect message; the state file always reflects the last completed step. The
render gate fails CLOSED. Conflicting data discovered after Gate 1 reopens Gate 1 rather
than silently updating the baseline.

In practice:

- **Audette outage** mid-P1/P3/P4: stop the phase, tell the user the Audette integration
  needs reconnecting, save state at the last completed step. Do not substitute estimates for
  the modeled physics and continue.
- **Verifier outage** at P2/Gate 1/P4: stop — conflicts cannot be recorded/resolved and the
  render gate cannot be evaluated without it. Never proceed on the assumption it would pass.
- **Renderer outage** at P5: stop after saving `state.report.data_json_path` — the data JSON
  is durable; rendering resumes when the renderer is back.
- **Gate-1 reopen:** any post-Gate-1 change to baseline data sets `phase: "GATE1"` and
  re-presents only the changed items (see Resume Protocol). Adjudicated values are never
  overwritten without the user re-adjudicating.
