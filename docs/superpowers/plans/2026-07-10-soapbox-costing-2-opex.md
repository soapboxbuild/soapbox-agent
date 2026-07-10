# Soapbox Costing — Plan 2: OpEx tools (EIA + OpenEI URDB)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Add the two OpEx tools to the costing MCP — `get_energy_prices` (EIA retail electricity + natural-gas prices) and `get_tariff` (OpenEI URDB rate structures incl. demand charges) — the redistributable, public-domain backbone for a measure's `opex_delta_yr`.

**Architecture:** Extend the `~/soapbox-costing` MCP (Plan 1). Add per-source client modules under `src/sources/` and per-domain tool-registration modules under `src/tools/`; `registerTools()` in `index.ts` calls each. Tools call the live APIs at request time with a small in-memory TTL cache. No curated store yet (that's Plan 4).

**Tech Stack:** same as Plan 1 (TS ESM, `@modelcontextprotocol/sdk`, `node --test`). `fetch` is global (Node ≥20).

## Global Constraints (verified 2026-07-10 against the live hosts)

- **EIA API v2**, host `https://api.eia.gov/v2`, requires `api_key` query param (free). Env var: **`EIA_API_KEY`**. Electricity retail price path: `/electricity/retail-sales/data/` with facets `stateid`, `sectorid` (`COM`/`RES`/`IND`), `data[0]=price`, `frequency=monthly`. Natural-gas delivered price path: `/natural-gas/pri/sum/data/` (confirm exact facet/series path against a live response during Task 3 — EIA's NG endpoints use series/facets; adjust the parser if the shape differs).
- **OpenEI URDB**, host `https://api.openei.org/utility_rates`, requires `api_key` (the NREL/NLR developer key). Env var: **`NREL_API_KEY`** (the SAME key is reused for REopt in Plan 3). Params: `version=latest&format=json&api_key=…&sector=Commercial&address=…` or `&ratesforutility=…`.
- **NREL rebrand (verified):** `developer.nrel.gov` no longer resolves; the lab is now "National Laboratory of the Rockies" at `developer.nlr.gov`. **URDB itself is on `api.openei.org` (unaffected).** Only the *key registration* portal moved to `nlr.gov`; the API host stays `api.openei.org`.
- Keys are read from env at request time. If a required key is missing, the tool returns a clear MCP error telling the operator which env var to set — it must NOT crash the server or fabricate data.
- Every tool response carries `source` (e.g. `"EIA API v2"`, `"OpenEI URDB"`) and `retrieved_period` / freshness info, consistent with the design's provenance rule.
- Unit tests MUST mock `fetch` (no network, no key) and assert both URL construction (correct host, path, `api_key`, facets) and response parsing. A live smoke check is separate and gated on env keys.
- Do not collapse to a single blended $/kWh where demand charges exist — `get_tariff` must surface demand-charge structure.

---

### Task 1: EIA client + `get_energy_prices` tool

**Files:**
- Create: `src/sources/eia.ts`
- Create: `src/tools/energy-prices.ts`
- Modify: `src/index.ts` (call `registerEnergyPriceTools(server)` from `registerTools`)
- Test: `src/sources/eia.test.ts`

**Interfaces:**
- Produces: `registerEnergyPriceTools(server: McpServer): void`; `fetchEiaPrice(opts): Promise<PriceResult>` where `PriceResult = { fuel, sector, region, price: {value:number, units:string, period:string}, series: {period:string, value:number}[], source:"EIA API v2" }`.
- Consumes: `process.env.EIA_API_KEY`.

- [ ] **Step 1: Write the failing test** — `src/sources/eia.test.ts`

```ts
import { test } from "node:test";
import assert from "node:assert/strict";
import { fetchEiaPrice } from "./eia.js";

// Minimal shape of an EIA v2 electricity retail-sales response.
const EIA_FIXTURE = {
  response: {
    data: [
      { period: "2025-02", stateid: "CA", sectorid: "COM", price: 24.11, "price-units": "cents per kilowatt-hour" },
      { period: "2025-01", stateid: "CA", sectorid: "COM", price: 23.87, "price-units": "cents per kilowatt-hour" },
    ],
  },
};

test("fetchEiaPrice builds the correct v2 URL and parses the latest price", async () => {
  let calledUrl = "";
  const fakeFetch = async (url: string) => {
    calledUrl = url;
    return { ok: true, json: async () => EIA_FIXTURE } as any;
  };
  const r = await fetchEiaPrice(
    { fuel: "electricity", sector: "COM", region: "CA" },
    { apiKey: "TESTKEY", fetchImpl: fakeFetch },
  );
  assert.ok(calledUrl.startsWith("https://api.eia.gov/v2/electricity/retail-sales/data/"), calledUrl);
  assert.match(calledUrl, /api_key=TESTKEY/);
  assert.match(calledUrl, /facets\[stateid\]\[\]=CA/);
  assert.match(calledUrl, /facets\[sectorid\]\[\]=COM/);
  assert.equal(r.price.value, 24.11);         // latest period first
  assert.equal(r.price.period, "2025-02");
  assert.equal(r.source, "EIA API v2");
  assert.equal(r.series.length, 2);
});

test("fetchEiaPrice throws a clear error when the key is missing", async () => {
  await assert.rejects(
    () => fetchEiaPrice({ fuel: "electricity", sector: "COM", region: "CA" }, { apiKey: "", fetchImpl: (async () => ({}) as any) }),
    /EIA_API_KEY/,
  );
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd ~/soapbox-costing && npm run build && node --test dist/sources/eia.test.js`
Expected: FAIL (module not found).

- [ ] **Step 3: Implement `src/sources/eia.ts`**

```ts
export type Fuel = "electricity" | "natural_gas";
export type Sector = "COM" | "RES" | "IND";

export interface PriceResult {
  fuel: Fuel; sector: Sector; region: string;
  price: { value: number; units: string; period: string };
  series: { period: string; value: number }[];
  source: "EIA API v2";
}

interface Opts { apiKey?: string; fetchImpl?: typeof fetch }

const BASE = "https://api.eia.gov/v2";

export async function fetchEiaPrice(
  q: { fuel: Fuel; sector: Sector; region: string },
  opts: Opts = {},
): Promise<PriceResult> {
  const apiKey = opts.apiKey ?? process.env.EIA_API_KEY ?? "";
  if (!apiKey) throw new Error("EIA_API_KEY is not set — cannot query EIA price data.");
  const f = opts.fetchImpl ?? fetch;

  // Electricity retail-sales; natural gas uses a different route (see note).
  const path = q.fuel === "electricity"
    ? "/electricity/retail-sales/data/"
    : "/natural-gas/pri/sum/a_epg0_pcs_sil_dpmcf/data/"; // verify against live in Task 3
  const params = new URLSearchParams({
    api_key: apiKey, frequency: "monthly", "data[0]": "price",
    sort: JSON.stringify([{ column: "period", direction: "desc" }]) as any,
    length: "24",
  });
  // facets differ slightly by route; electricity uses stateid+sectorid.
  const url = `${BASE}${path}?${params.toString()}`
    + `&facets[stateid][]=${encodeURIComponent(q.region)}`
    + (q.fuel === "electricity" ? `&facets[sectorid][]=${encodeURIComponent(q.sector)}` : "");

  const res = await f(url);
  if (!res.ok) throw new Error(`EIA API error ${res.status} for ${q.fuel}/${q.region}`);
  const json: any = await res.json();
  const rows: any[] = json?.response?.data ?? [];
  if (rows.length === 0) throw new Error(`EIA returned no data for ${q.fuel}/${q.region}/${q.sector}`);
  const series = rows.map((d) => ({ period: String(d.period), value: Number(d.price) }));
  const latest = series[0];
  return {
    fuel: q.fuel, sector: q.sector, region: q.region,
    price: { value: latest.value, units: String(rows[0]["price-units"] ?? "cents per kWh"), period: latest.period },
    series, source: "EIA API v2",
  };
}
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd ~/soapbox-costing && npm run build && node --test dist/sources/eia.test.js` → PASS.

- [ ] **Step 5: Implement the tool `src/tools/energy-prices.ts`**

```ts
import { z } from "zod";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { fetchEiaPrice, type Fuel, type Sector } from "../sources/eia.js";

export function registerEnergyPriceTools(server: McpServer): void {
  server.tool(
    "get_energy_prices",
    "Current retail energy price (electricity or natural gas) for a US state and sector, from EIA API v2 — the OpEx-delta price basis. Returns the latest price plus a 24-month series.",
    {
      region: z.string().describe("US state code, e.g. 'CA', 'NY'"),
      sector: z.enum(["COM", "RES", "IND"]).describe("Commercial, Residential, Industrial"),
      fuel: z.enum(["electricity", "natural_gas"]).default("electricity"),
    },
    async ({ region, sector, fuel }) => {
      try {
        const r = await fetchEiaPrice({ region, sector: sector as Sector, fuel: fuel as Fuel });
        return { content: [{ type: "text", text: JSON.stringify(r) }] };
      } catch (e) {
        return { isError: true, content: [{ type: "text", text: (e as Error).message }] };
      }
    },
  );
}
```

- [ ] **Step 6: Wire into `src/index.ts`** — import and call inside `registerTools`:

```ts
import { registerEnergyPriceTools } from "./tools/energy-prices.js";
// inside registerTools(server):
registerEnergyPriceTools(server);
```

- [ ] **Step 7: Full build + test + round-trip still green**

Run: `cd ~/soapbox-costing && npm run build && node --test dist/**/*.test.js dist/index.test.js`
Expected: all PASS; `tools/list` now includes `get_energy_prices` (extend `index.test.ts`'s tools/list assertion to include it).

- [ ] **Step 8: Commit** — `git add src/sources/eia.ts src/tools/energy-prices.ts src/index.ts src/sources/eia.test.ts src/index.test.ts && git commit -m "feat: get_energy_prices tool (EIA API v2 electricity + natural gas)"`

---

### Task 2: URDB client + `get_tariff` tool

**Files:**
- Create: `src/sources/urdb.ts`
- Create: `src/tools/tariff.ts`
- Modify: `src/index.ts` (call `registerTariffTools`)
- Test: `src/sources/urdb.test.ts`

**Interfaces:**
- Produces: `registerTariffTools(server)`; `fetchUrdbTariffs(opts): Promise<TariffResult>` with `TariffResult = { query, count, tariffs: Tariff[], source:"OpenEI URDB" }` and `Tariff = { label, utility, name, sector, energy_charge_summary, demand_charge_summary, has_demand_charges:boolean, uri }`.
- Consumes: `process.env.NREL_API_KEY`.

- [ ] **Step 1: Write the failing test** — `src/sources/urdb.test.ts`

```ts
import { test } from "node:test";
import assert from "node:assert/strict";
import { fetchUrdbTariffs } from "./urdb.js";

const URDB_FIXTURE = {
  items: [
    {
      label: "abc123", utility: "Pacific Gas & Electric Co",
      name: "A-10 TOU Medium General Demand", sector: "Commercial",
      energyratestructure: [[{ rate: 0.18, unit: "kWh" }]],
      demandratestructure: [[{ rate: 22.5, unit: "kW" }]],
      uri: "https://apps.openei.org/USURDB/rate/view/abc123",
    },
  ],
};

test("fetchUrdbTariffs builds URL with api_key + parses demand charges", async () => {
  let calledUrl = "";
  const fakeFetch = async (url: string) => { calledUrl = url; return { ok: true, json: async () => URDB_FIXTURE } as any; };
  const r = await fetchUrdbTariffs({ utility: "Pacific Gas & Electric Co", sector: "Commercial" }, { apiKey: "K", fetchImpl: fakeFetch });
  assert.ok(calledUrl.startsWith("https://api.openei.org/utility_rates"), calledUrl);
  assert.match(calledUrl, /api_key=K/);
  assert.match(calledUrl, /version=latest/);
  assert.equal(r.tariffs[0].has_demand_charges, true);
  assert.equal(r.source, "OpenEI URDB");
});

test("fetchUrdbTariffs errors clearly without a key", async () => {
  await assert.rejects(() => fetchUrdbTariffs({ utility: "x" }, { apiKey: "", fetchImpl: (async () => ({}) as any) }), /NREL_API_KEY/);
});
```

- [ ] **Step 2: Run → FAIL** (`node --test dist/sources/urdb.test.js`).

- [ ] **Step 3: Implement `src/sources/urdb.ts`**

```ts
export interface Tariff {
  label: string; utility: string; name: string; sector: string;
  energy_charge_summary: string; demand_charge_summary: string;
  has_demand_charges: boolean; uri: string;
}
export interface TariffResult { query: string; count: number; tariffs: Tariff[]; source: "OpenEI URDB" }
interface Opts { apiKey?: string; fetchImpl?: typeof fetch }

const BASE = "https://api.openei.org/utility_rates";

function summarizeRate(structure: any[][] | undefined, unit: string): string {
  if (!Array.isArray(structure) || structure.length === 0) return "none";
  const rates = structure.flat().map((p) => p?.rate).filter((x) => typeof x === "number");
  if (rates.length === 0) return "none";
  const min = Math.min(...rates), max = Math.max(...rates);
  return min === max ? `${min}/${unit}` : `${min}–${max}/${unit}`;
}

export async function fetchUrdbTariffs(
  q: { utility?: string; sector?: string; address?: string; limit?: number },
  opts: Opts = {},
): Promise<TariffResult> {
  const apiKey = opts.apiKey ?? process.env.NREL_API_KEY ?? "";
  if (!apiKey) throw new Error("NREL_API_KEY is not set — cannot query OpenEI URDB.");
  const f = opts.fetchImpl ?? fetch;
  const params = new URLSearchParams({
    version: "latest", format: "json", api_key: apiKey,
    detail: "full", limit: String(q.limit ?? 10),
  });
  if (q.sector) params.set("sector", q.sector);
  if (q.utility) params.set("ratesforutility", q.utility);
  if (q.address) params.set("address", q.address);
  const url = `${BASE}?${params.toString()}`;
  const res = await f(url);
  if (!res.ok) throw new Error(`URDB API error ${res.status}`);
  const json: any = await res.json();
  if (json?.error) throw new Error(`URDB error: ${json.error?.message ?? JSON.stringify(json.error)}`);
  const items: any[] = json?.items ?? [];
  const tariffs: Tariff[] = items.map((it) => {
    const demand = summarizeRate(it.demandratestructure, "kW");
    return {
      label: String(it.label ?? ""), utility: String(it.utility ?? ""),
      name: String(it.name ?? ""), sector: String(it.sector ?? ""),
      energy_charge_summary: summarizeRate(it.energyratestructure, "kWh"),
      demand_charge_summary: demand, has_demand_charges: demand !== "none",
      uri: String(it.uri ?? ""),
    };
  });
  return { query: q.utility ?? q.address ?? q.sector ?? "", count: tariffs.length, tariffs, source: "OpenEI URDB" };
}
```

- [ ] **Step 4: Run → PASS.**

- [ ] **Step 5: Implement `src/tools/tariff.ts`** (mirror the energy-prices tool pattern; zod params `utility?`, `sector?` (default "Commercial"), `address?`, `limit?`; wrap `fetchUrdbTariffs`; return `isError` on throw).

- [ ] **Step 6: Wire into `registerTools`** (`registerTariffTools(server)`).

- [ ] **Step 7: Build + full test + extend `tools/list` assertion to include `get_tariff`.** All PASS.

- [ ] **Step 8: Commit** — `git add src/sources/urdb.ts src/tools/tariff.ts src/index.ts src/sources/urdb.test.ts src/index.test.ts && git commit -m "feat: get_tariff tool (OpenEI URDB rate structures incl. demand charges)"`

---

### Task 3: Deploy — set keys + live smoke ⚠️ OUTWARD-FACING (needs the two API keys; controller sets Railway env)

**Files:** none (infra + live verification).

- [ ] **Step 1:** Confirm the two keys exist (from the key-registration step): `EIA_API_KEY`, `NREL_API_KEY`.
- [ ] **Step 2:** Set them as Railway service variables on `costing-mcp` in the `soapbox-mcps` project (via `railway variables --set` linked to the service, or the Railway API). Do NOT commit keys to the repo.
- [ ] **Step 3:** Trigger a redeploy (push already auto-deploys; a var change also redeploys). Wait for Online.
- [ ] **Step 4: Live smoke** (the real verification the field cares about):
  - `curl -s -X POST https://costing.mcp.soapbox.build/mcp -H 'content-type: application/json' -H 'accept: application/json, text/event-stream' -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"get_energy_prices","arguments":{"region":"CA","sector":"COM"}}}'` → returns a price value with `source: EIA API v2`, not a key error.
  - Same for `get_tariff` with `{"sector":"Commercial","limit":1}` → returns a tariff with a demand-charge summary.
  - **If EIA's natural-gas route or URDB field names differ from the fixtures, fix the parser now** (this is the point where the live shape is verified against the mocked fixtures) and re-commit.
- [ ] **Step 5:** Record the verified live outputs in the report.

---

## Self-Review

- **Spec coverage:** implements the design's OpEx tools (EIA + URDB incl. demand charges) and the provenance rule (`source` on every response). CapEx/DER/service-capacity are later plans.
- **Placeholder scan:** the two "verify against live in Task 3" notes (EIA NG route, URDB field names) are deliberate live-verification points, not placeholders — the mocked fixtures let the code be built and unit-tested first, and Task 3 reconciles them to reality.
- **Type consistency:** `registerEnergyPriceTools` / `registerTariffTools` match the `registerTools` extension point from Plan 1; `PriceResult`/`TariffResult`/`Tariff` are the produced interfaces later plans (Plan 5 skill) consume.
- **Key handling:** keys from env only; missing-key → clear MCP error, never a crash or fabricated number; keys never committed.
