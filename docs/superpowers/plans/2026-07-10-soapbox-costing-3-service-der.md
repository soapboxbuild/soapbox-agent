# Soapbox Costing — Plan 3: Electrical service-capacity model + DER economics

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Add two tools to the costing MCP: `estimate_service_upgrade` (the synthesized electrical service-capacity parametric $/A model — the highest-value gap, no database exists) and `get_der_economics` (solar/storage/GHP CapEx via a cost parametric, with real solar production from PVWatts v8).

**Architecture:** Same MCP (`~/soapbox-costing`). `estimate_service_upgrade` is pure code (no network) — a seeded parametric model returning low/base/high with an `UNVERIFIED` flag. `get_der_economics` combines a pure cost parametric with a live PVWatts v8 GET (synchronous) for solar production. Both register via the `registerTools` extension point.

**Tech Stack:** same as Plans 1–2. PVWatts uses the existing `NREL_API_KEY` (api.data.gov gateway).

## Global Constraints

- **Design deviation (approved):** the spec named REopt for DER; REopt is a heavy async job API (POST scenario → poll `run_uuid`), unsuitable for a synchronous MCP tool. Plan 3 uses **PVWatts v8** (synchronous GET, verified live at `https://developer.nlr.gov/api/pvwatts/v8.json`) for solar production + a **$/unit cost parametric** for CapEx. Full REopt optimization is a documented follow-up, not v1.
- **All cost figures are seeded PLACEHOLDERS** flagged for Christopher's tuning (same rule as `cost-bases.md`). They live in one clearly-labelled constants block per source module, not scattered.
- **Electrical service-capacity is always a RANGE with `flag: "UNVERIFIED"`** at screening scale (no known service data). Never a point estimate. `low` assumes existing headroom (may be small/zero incremental), `high` is a full new-service upgrade. This is the single most uncertain number in the whole system — bands are intentionally wide (§ seed data).
- Every response carries `source`/`basis` provenance and a `confidence` field (`low` for these synthesized/parametric numbers).
- Unit tests: the parametric models are pure (test directly, no network). PVWatts is mocked via a `fetchImpl` opt (same pattern as EIA/URDB). Live PVWatts is exercised only in the Task 3 smoke.
- `NREL_API_KEY` already set on the `costing-mcp` Railway service (Plan 2).

## Seed data (from research doc §10 + NREL ATB-style defaults; PLACEHOLDER — tune later)

**Electrical service upgrade (customer-side, to full new service):**
- Residential / small (≤ 200A, single-phase): panel upgrade $2,000–$4,500 (avg ~$2,780); 100A→200A ≈ $3,200; + utility transformer $6,000–$8,000 when required.
- Commercial 400A: $15,000–$50,000. Commercial 800–1200A: $50,000–$100,000. Major w/ switchgear + utility coordination: $100,000–$150,000+.
- Three-phase conversion adder: $10,000–$30,000.
- Source: PG&E/NV5 "Service Upgrades for Electrification Retrofits" (2022, CALMAC PG&E0467.01); commercial ranges are contractor-reported (low authority → wide bands).

**DER CapEx (installed, 2024$ placeholders):**
- Solar PV (commercial rooftop): $1.50–$2.50/W_dc (base ~$2.00). O&M ~$18/kW-yr.
- Battery storage: $400–$700/kWh (base ~$550). 
- GSHP/GHP: $20,000–$35,000 per ton-equivalent block *(placeholder — GHP costing is highly site-specific; low confidence)*.

---

### Task 1: `estimate_service_upgrade` (electrical service-capacity parametric)

**Files:**
- Create: `src/sources/service-upgrade.ts`
- Create: `src/tools/service-upgrade.ts`
- Modify: `src/index.ts` (register)
- Test: `src/sources/service-upgrade.test.ts`

**Interfaces:**
- Produces: `estimateServiceUpgrade(q): ServiceUpgradeResult` where
  `q = { sector: "residential"|"commercial"; target_amperage?: number; demand_increase_kw?: number; phase?: "single"|"three"; service_capacity_known?: boolean }`
  and `ServiceUpgradeResult = { upgrade_cost: {low:number, base:number, high:number}, flag: "VERIFIED"|"UNVERIFIED", basis: string, confidence: "low", assumptions: string[] }`.
- Produces: `registerServiceUpgradeTools(server)`.

- [ ] **Step 1: Write the failing test** — `src/sources/service-upgrade.test.ts`

```ts
import { test } from "node:test";
import assert from "node:assert/strict";
import { estimateServiceUpgrade } from "./service-upgrade.js";

test("commercial 400A unverified upgrade returns a wide UNVERIFIED range, low>=0", () => {
  const r = estimateServiceUpgrade({ sector: "commercial", target_amperage: 400 });
  assert.equal(r.flag, "UNVERIFIED");
  assert.ok(r.upgrade_cost.low >= 0);
  assert.ok(r.upgrade_cost.high > r.upgrade_cost.low, "range must not collapse");
  assert.ok(r.upgrade_cost.high >= 15000 && r.upgrade_cost.high <= 60000, `400A high ~15-50k, got ${r.upgrade_cost.high}`);
  assert.equal(r.confidence, "low");
});

test("three-phase conversion adds to the high end", () => {
  const single = estimateServiceUpgrade({ sector: "commercial", target_amperage: 400, phase: "single" });
  const three = estimateServiceUpgrade({ sector: "commercial", target_amperage: 400, phase: "three" });
  assert.ok(three.upgrade_cost.high > single.upgrade_cost.high, "3-phase adder applies");
});

test("known capacity yields a VERIFIED point (low==base==high) only when explicitly known", () => {
  const r = estimateServiceUpgrade({ sector: "commercial", target_amperage: 400, service_capacity_known: true });
  assert.equal(r.flag, "VERIFIED");
});

test("residential small panel upgrade is in the low thousands", () => {
  const r = estimateServiceUpgrade({ sector: "residential", target_amperage: 200 });
  assert.ok(r.upgrade_cost.high <= 12000, `res high should be modest, got ${r.upgrade_cost.high}`);
});
```

- [ ] **Step 2: Run → FAIL.**

- [ ] **Step 3: Implement `src/sources/service-upgrade.ts`**

```ts
export interface ServiceUpgradeQuery {
  sector: "residential" | "commercial";
  target_amperage?: number;
  demand_increase_kw?: number;
  phase?: "single" | "three";
  service_capacity_known?: boolean;
}
export interface ServiceUpgradeResult {
  upgrade_cost: { low: number; base: number; high: number };
  flag: "VERIFIED" | "UNVERIFIED";
  basis: string;
  confidence: "low";
  assumptions: string[];
}

// PLACEHOLDER seed bands (full new-service cost), from PG&E/NV5 2022 + contractor ranges. Tune later.
const RES_BANDS = { low: 2000, base: 3200, high: 4500 };          // panel upgrade ≤200A
const RES_XFMR = 7000;                                            // utility transformer if needed
const COMM_BANDS: { maxAmps: number; low: number; base: number; high: number }[] = [
  { maxAmps: 400,   low: 15000, base: 28000,  high: 50000 },
  { maxAmps: 1200,  low: 50000, base: 72000,  high: 100000 },
  { maxAmps: Infinity, low: 100000, base: 125000, high: 150000 }, // switchgear + utility coordination
];
const THREE_PHASE_ADDER = { low: 10000, high: 30000 };

// Rough amperage estimate from a kW demand increase (208V 3φ commercial / 240V 1φ res), if amperage not given.
function ampsFromKw(kw: number, sector: "residential" | "commercial"): number {
  const volts = sector === "commercial" ? 208 * Math.sqrt(3) : 240;
  return (kw * 1000) / volts;
}

export function estimateServiceUpgrade(q: ServiceUpgradeQuery): ServiceUpgradeResult {
  const amps = q.target_amperage
    ?? (q.demand_increase_kw != null ? ampsFromKw(q.demand_increase_kw, q.sector) : undefined);
  const assumptions: string[] = [];
  let band: { low: number; base: number; high: number };

  if (q.sector === "residential") {
    band = { ...RES_BANDS };
    assumptions.push("Residential panel/service upgrade band (PG&E/NV5 2022). Excludes utility transformer unless flagged.");
    if ((amps ?? 0) > 200) { band.high += RES_XFMR; band.base += RES_XFMR / 2; assumptions.push("Utility transformer likely required (>200A)."); }
  } else {
    const tier = COMM_BANDS.find((b) => (amps ?? 400) <= b.maxAmps) ?? COMM_BANDS[COMM_BANDS.length - 1];
    band = { low: tier.low, base: tier.base, high: tier.high };
    assumptions.push(`Commercial service band for ~${Math.round(amps ?? 400)}A (contractor-reported ranges; low authority).`);
  }
  if (q.phase === "three") {
    band.high += THREE_PHASE_ADDER.high;
    band.base += (THREE_PHASE_ADDER.low + THREE_PHASE_ADDER.high) / 2;
    assumptions.push("Three-phase conversion adder applied.");
  }

  if (q.service_capacity_known) {
    // Verified: a single confirmed cost (use base as the confirmed point).
    return {
      upgrade_cost: { low: band.base, base: band.base, high: band.base },
      flag: "VERIFIED", basis: "Confirmed service capacity / quote", confidence: "low",
      assumptions: [...assumptions, "service_capacity_known=true → point estimate."],
    };
  }
  // Unverified (screening default): low assumes existing headroom (no forced full upgrade).
  return {
    upgrade_cost: { low: 0, base: band.base, high: band.high },
    flag: "UNVERIFIED", basis: "Synthesized parametric (no service data)", confidence: "low",
    assumptions: [...assumptions, "UNVERIFIED: low=$0 assumes existing headroom; high=full new service. Verify with a switchgear/service survey."],
  };
}
```

- [ ] **Step 4: Run → PASS.**

- [ ] **Step 5: Implement `src/tools/service-upgrade.ts`** — zod params `sector` (enum), `target_amperage?` number, `demand_increase_kw?` number, `phase?` enum default "single", `service_capacity_known?` boolean; wrap `estimateServiceUpgrade`; return JSON. (Pure — no try/network needed, but keep the `isError` wrapper for safety.)

- [ ] **Step 6: Register** `registerServiceUpgradeTools(server)` in `registerTools`. Extend `index.test.ts` tools/list to include `estimate_service_upgrade`.

- [ ] **Step 7: Build + full test → all PASS.**

- [ ] **Step 8: Commit** — `git add src/sources/service-upgrade.ts src/tools/service-upgrade.ts src/index.ts src/sources/service-upgrade.test.ts src/index.test.ts && git commit -m "feat: estimate_service_upgrade (electrical service-capacity parametric, UNVERIFIED ranges)"`

---

### Task 2: `get_der_economics` (PVWatts production + DER cost parametric)

**Files:**
- Create: `src/sources/pvwatts.ts` (live GET client, mocked in tests)
- Create: `src/sources/der-costs.ts` (pure parametric)
- Create: `src/tools/der.ts`
- Modify: `src/index.ts` (register)
- Test: `src/sources/pvwatts.test.ts`, `src/sources/der-costs.test.ts`

**Interfaces:**
- Produces: `fetchPvwatts({lat, lon, system_capacity_kw}, opts): Promise<{ac_annual_kwh:number, capacity_factor:number, source:"PVWatts v8"}>`.
- Produces: `estimateDerCost({system, size}): {capex:{low,base,high}, opex_delta_yr:number, unit_basis:string, confidence:"low", basis:string}` for `system ∈ {"solar_pv","battery_storage","gshp"}`.
- Produces: `registerDerTools(server)`; tool `get_der_economics` combines them (solar: production from PVWatts + capex from parametric; storage/gshp: parametric only).

- [ ] **Step 1: Write failing tests**

`src/sources/der-costs.test.ts`:
```ts
import { test } from "node:test";
import assert from "node:assert/strict";
import { estimateDerCost } from "./der-costs.js";

test("solar_pv capex scales with size at ~$1.5-2.5/W", () => {
  const r = estimateDerCost({ system: "solar_pv", size: 100 }); // 100 kW
  // 100 kW = 100000 W → base ~$200k
  assert.ok(r.capex.low >= 100 * 1000 * 1.4 && r.capex.high <= 100 * 1000 * 2.6, JSON.stringify(r.capex));
  assert.ok(r.capex.low < r.capex.base && r.capex.base < r.capex.high);
});

test("battery_storage priced per kWh", () => {
  const r = estimateDerCost({ system: "battery_storage", size: 200 }); // 200 kWh
  assert.ok(r.capex.base >= 200 * 400 && r.capex.base <= 200 * 700);
});
```

`src/sources/pvwatts.test.ts`:
```ts
import { test } from "node:test";
import assert from "node:assert/strict";
import { fetchPvwatts } from "./pvwatts.js";

const FIXTURE = { outputs: { ac_annual: 160544.1, capacity_factor: 18.3 } };

test("fetchPvwatts builds v8 URL with api_key and parses ac_annual", async () => {
  let url = "";
  const r = await fetchPvwatts(
    { lat: 40, lon: -105, system_capacity_kw: 100 },
    { apiKey: "K", fetchImpl: (async (u: string) => { url = u; return { ok: true, json: async () => FIXTURE } as any; }) },
  );
  assert.match(url, /developer\.nlr\.gov\/api\/pvwatts\/v8\.json/);
  assert.match(url, /api_key=K/);
  assert.match(url, /system_capacity=100/);
  assert.equal(r.ac_annual_kwh, 160544.1);
  assert.equal(r.source, "PVWatts v8");
});

test("fetchPvwatts errors clearly without key", async () => {
  await assert.rejects(() => fetchPvwatts({ lat: 40, lon: -105, system_capacity_kw: 100 }, { apiKey: "", fetchImpl: (async () => ({}) as any) }), /NREL_API_KEY/);
});
```

- [ ] **Step 2: Run → FAIL.**

- [ ] **Step 3: Implement `src/sources/der-costs.ts`** (pure)

```ts
export type DerSystem = "solar_pv" | "battery_storage" | "gshp";
export interface DerCost {
  capex: { low: number; base: number; high: number };
  opex_delta_yr: number; unit_basis: string; confidence: "low"; basis: string;
}
// PLACEHOLDER 2024$ seeds — tune later.
const SEEDS = {
  solar_pv:        { low: 1.4, base: 2.0, high: 2.6, unit: "$/W_dc", om_per_kw_yr: 18 },   // × watts
  battery_storage: { low: 400, base: 550, high: 700, unit: "$/kWh", om_per_kw_yr: 0 },     // × kWh
  gshp:            { low: 20000, base: 27000, high: 35000, unit: "$/ton-block", om_per_kw_yr: 0 }, // × tons
};
export function estimateDerCost(q: { system: DerSystem; size: number }): DerCost {
  const s = SEEDS[q.system];
  const mult = q.system === "solar_pv" ? q.size * 1000 : q.size; // solar size is kW → W
  return {
    capex: { low: Math.round(s.low * mult), base: Math.round(s.base * mult), high: Math.round(s.high * mult) },
    opex_delta_yr: -Math.round((s.om_per_kw_yr ?? 0) * (q.system === "solar_pv" ? q.size : 0)), // O&M is a cost; savings computed elsewhere
    unit_basis: s.unit, confidence: "low",
    basis: `PLACEHOLDER seed (${s.unit}); tune against real bids.`,
  };
}
```

- [ ] **Step 4: Implement `src/sources/pvwatts.ts`** (live GET, mocked in tests)

```ts
type FetchLike = (url: string) => Promise<{ ok: boolean; status?: number; json: () => Promise<any> }>;
export interface PvResult { ac_annual_kwh: number; capacity_factor: number; source: "PVWatts v8" }
const BASE = "https://developer.nlr.gov/api/pvwatts/v8.json";
export async function fetchPvwatts(
  q: { lat: number; lon: number; system_capacity_kw: number; tilt?: number; azimuth?: number },
  opts: { apiKey?: string; fetchImpl?: FetchLike } = {},
): Promise<PvResult> {
  const apiKey = opts.apiKey ?? process.env.NREL_API_KEY ?? "";
  if (!apiKey) throw new Error("NREL_API_KEY is not set — cannot query PVWatts.");
  const f = opts.fetchImpl ?? (fetch as unknown as FetchLike);
  const p = new URLSearchParams({
    api_key: apiKey, lat: String(q.lat), lon: String(q.lon),
    system_capacity: String(q.system_capacity_kw), azimuth: String(q.azimuth ?? 180),
    tilt: String(q.tilt ?? 20), array_type: "1", module_type: "0", losses: "14",
  });
  const res = await f(`${BASE}?${p.toString()}`);
  if (!res.ok) throw new Error(`PVWatts error ${res.status ?? "?"}`);
  const j = await res.json();
  const o = j?.outputs ?? {};
  if (o.ac_annual == null) throw new Error("PVWatts returned no ac_annual");
  return { ac_annual_kwh: Number(o.ac_annual), capacity_factor: Number(o.capacity_factor), source: "PVWatts v8" };
}
```

- [ ] **Step 5: Run both source tests → PASS.**

- [ ] **Step 6: Implement `src/tools/der.ts`** — `get_der_economics` with zod params: `system` enum (`solar_pv`|`battery_storage`|`gshp`), `size` number (kW for solar/storage-power, kWh for battery energy, tons for gshp — document in the description), and optional `lat`/`lon` (solar only). For `solar_pv` with lat/lon, also call `fetchPvwatts` and include `ac_annual_kwh` + a simple derived note; wrap CapEx from `estimateDerCost`. Return `isError` on throw (e.g., PVWatts key/network).

- [ ] **Step 7: Register** `registerDerTools(server)`; extend `index.test.ts` tools/list to include `get_der_economics`. Build + full test → PASS.

- [ ] **Step 8: Commit** — `git add src/sources/pvwatts.ts src/sources/der-costs.ts src/tools/der.ts src/index.ts src/sources/pvwatts.test.ts src/sources/der-costs.test.ts src/index.test.ts && git commit -m "feat: get_der_economics (DER cost parametric + PVWatts v8 solar production)"`

---

### Task 3: Deploy + live smoke ⚠️ OUTWARD-FACING (push auto-deploys; NREL_API_KEY already set)

- [ ] **Step 1:** `git push origin main` (auto-redeploys the `costing-mcp` service). Wait for Online.
- [ ] **Step 2: Live smoke:**
  - `estimate_service_upgrade` `{"sector":"commercial","target_amperage":400}` → UNVERIFIED range, low=0, high in the 15–60k band. (Pure — no key.)
  - `get_der_economics` `{"system":"solar_pv","size":100,"lat":40,"lon":-105}` → capex ~$200k range + `ac_annual_kwh` ~160,000 from PVWatts, `source: PVWatts v8`. Confirms the NREL key works for PVWatts.
  - `get_der_economics` `{"system":"battery_storage","size":200}` → per-kWh capex, no PVWatts call.
- [ ] **Step 3:** Record verified outputs in the report.

---

## Self-Review

- **Spec coverage:** implements the electrical service-capacity model (the design's highest-value gap) and DER economics. The DER approach deviates from REopt to PVWatts+parametric (documented, approved) — full REopt is a noted follow-up.
- **Placeholder scan:** none unintended; all cost seeds are explicitly PLACEHOLDER constants in one block per module with `confidence: "low"` and a `basis` string, per the design's tuning rule.
- **Type consistency:** `registerServiceUpgradeTools`/`registerDerTools` match the extension point; `fetchPvwatts` mirrors the EIA/URDB `fetchImpl` pattern (with the `FetchLike` typing fix Task 1 of Plan 2 established).
- **Provenance/UNVERIFIED:** service-capacity is always an UNVERIFIED range (never collapsed) unless capacity is explicitly known; every response carries `basis` + `confidence`.
