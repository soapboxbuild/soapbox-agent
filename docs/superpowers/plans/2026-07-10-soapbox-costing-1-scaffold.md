# Soapbox Costing — Plan 1: Plugin + MCP Scaffold

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the `soapbox-costing` plugin repo and a deployable MCP server skeleton (health + tool-registry plumbing, no cost tools yet) so Plans 2–6 have a working, deployed foundation to add tools to.

**Architecture:** TypeScript ESM MCP server using `@modelcontextprotocol/sdk` `StreamableHTTPServerTransport` over `node:http` (the `crrem-mcp` house pattern), built with `tsc` to `dist/`, deployed to the existing **`soapbox-mcps` Railway project** at `costing.mcp.soapbox.build`. Packaged as a Claude plugin (`.claude-plugin/plugin.json` + `.mcp.json`) mirroring `crrem-skills`.

**Tech Stack:** Node ≥20, TypeScript 5, `@modelcontextprotocol/sdk` ^1.12, `zod` ^3, Railway (nixpacks). This is the sibling of `crrem-mcp`/`cambium-mcp` — match their conventions exactly.

## Global Constraints

- Repo name: **`soapbox-costing`** under the `soapboxbuild` GitHub org. MCP server name (in `McpServer` + `.mcp.json` key): **`costing`**. Public URL: **`https://costing.mcp.soapbox.build/mcp`**; health at **`/health`**.
- MCP server code lives **in the plugin repo** (`src/`), same as `crrem-mcp`. Do NOT create a new Railway project — deploy a new **service** into the existing `soapbox-mcps` project.
- `"type": "module"` (ESM); build `tsc`; start `node dist/index.js`; `railway.toml` uses `builder = "nixpacks"`, `healthcheckPath = "/health"`.
- After `customDomainCreate`, **manually add the CNAME in Cloudflare immediately** — Railway does not auto-set DNS for custom domains.
- No cost data, no external-API calls, no `measure.cost` logic in this plan — skeleton only. The one tool shipped (`list_measures`) returns an explicit empty/"coming soon" taxonomy so tool-registry plumbing is proven end-to-end.
- The `measure.cost` contract stays canonical in `soapbox-agent`; this plan does not copy it.

---

### Task 1: Repo skeleton + build config

**Files:**
- Create: `soapbox-costing/package.json`
- Create: `soapbox-costing/tsconfig.json`
- Create: `soapbox-costing/railway.toml`
- Create: `soapbox-costing/.gitignore`

**Interfaces:**
- Produces: an npm project that builds with `npm run build` → `dist/index.js` and starts with `node dist/index.js`. Consumed by every later task/plan.

- [ ] **Step 1: Create `package.json`**

```json
{
  "name": "soapbox-costing-mcp",
  "version": "0.1.0",
  "description": "Soapbox Costing MCP — construction CapEx, OpEx, DER, and electrical service-capacity cost estimates for building decarbonization measures.",
  "type": "module",
  "main": "dist/index.js",
  "scripts": {
    "build": "tsc",
    "dev": "tsx src/index.ts",
    "start": "node dist/index.js",
    "test": "node --test"
  },
  "dependencies": {
    "@modelcontextprotocol/sdk": "^1.12.1",
    "zod": "^3.23.8"
  },
  "devDependencies": {
    "@types/node": "^22.0.0",
    "tsx": "^4.19.2",
    "typescript": "^5.7.3"
  }
}
```

- [ ] **Step 2: Create `tsconfig.json`** (mirror `crrem-mcp`)

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "outDir": "dist",
    "rootDir": "src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "declaration": false,
    "sourceMap": false
  },
  "include": ["src/**/*"]
}
```

- [ ] **Step 3: Create `railway.toml`**

```toml
[build]
builder = "nixpacks"
buildCommand = "npm run build"

[deploy]
startCommand = "node dist/index.js"
healthcheckPath = "/health"
healthcheckTimeout = 300
restartPolicyType = "on_failure"
```

- [ ] **Step 4: Create `.gitignore`**

```
node_modules/
dist/
*.log
.env
```

- [ ] **Step 5: Install + verify build tooling resolves**

Run: `cd soapbox-costing && npm install`
Expected: installs without error; `node_modules/@modelcontextprotocol/sdk` present.

- [ ] **Step 6: Commit**

```bash
cd soapbox-costing && git init && git add package.json tsconfig.json railway.toml .gitignore && git commit -m "chore: scaffold soapbox-costing MCP build config"
```

---

### Task 2: MCP server skeleton (health + tool registry + `list_measures` stub)

**Files:**
- Create: `soapbox-costing/src/index.ts`
- Test: `soapbox-costing/src/index.test.ts`

**Interfaces:**
- Produces: an HTTP server exposing `GET /health` → `200 {"status":"ok"}` and `POST /mcp` (Streamable HTTP MCP transport) with one registered tool `list_measures`. Later plans register additional tools on the same `McpServer` instance via an `registerTools(server)` extension point.

- [ ] **Step 1: Write the failing test** — `src/index.test.ts`

```ts
import { test } from "node:test";
import assert from "node:assert/strict";
import { buildServer } from "./index.js";

test("health endpoint returns ok", async () => {
  const { httpServer } = buildServer();
  await new Promise<void>((r) => httpServer.listen(0, r));
  const port = (httpServer.address() as any).port;
  const res = await fetch(`http://127.0.0.1:${port}/health`);
  assert.equal(res.status, 200);
  assert.deepEqual(await res.json(), { status: "ok" });
  httpServer.close();
});

test("list_measures tool is registered and returns an empty v0 taxonomy", async () => {
  const { mcpServer } = buildServer();
  // The tool exists on the server registry.
  assert.ok(mcpServer, "mcp server constructed");
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd soapbox-costing && npm run build && node --test dist/index.test.js`
Expected: FAIL — `buildServer` not exported / module not found.

- [ ] **Step 3: Write `src/index.ts`**

```ts
import { createServer, type Server } from "node:http";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import { z } from "zod";

const SERVER_NAME = "costing";
const SERVER_VERSION = "0.1.0";

// Extension point: Plans 2-6 add their tools here.
function registerTools(server: McpServer): void {
  server.tool(
    "list_measures",
    "List the decarbonization/retrofit measures this costing service can price. v0 returns an empty taxonomy; measures are added in later releases.",
    {},
    async () => ({
      content: [
        {
          type: "text",
          text: JSON.stringify({ measures: [], note: "taxonomy not yet loaded (v0 scaffold)" }),
        },
      ],
    }),
  );
}

export function buildServer(): { httpServer: Server; mcpServer: McpServer } {
  const mcpServer = new McpServer({ name: SERVER_NAME, version: SERVER_VERSION });
  registerTools(mcpServer);

  const httpServer = createServer(async (req, res) => {
    if (req.method === "GET" && req.url === "/health") {
      res.writeHead(200, { "content-type": "application/json" });
      res.end(JSON.stringify({ status: "ok" }));
      return;
    }
    if (req.url === "/mcp") {
      const transport = new StreamableHTTPServerTransport({ sessionIdGenerator: undefined });
      await mcpServer.connect(transport);
      await transport.handleRequest(req, res);
      return;
    }
    res.writeHead(404, { "content-type": "application/json" });
    res.end(JSON.stringify({ error: "not found" }));
  });

  return { httpServer, mcpServer };
}

// Entry point (skipped under the test runner, which imports buildServer directly).
const isMain = process.argv[1]?.endsWith("index.js");
if (isMain) {
  const port = Number(process.env.PORT ?? 8080);
  const { httpServer } = buildServer();
  httpServer.listen(port, () => console.log(`costing MCP listening on :${port}`));
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd soapbox-costing && npm run build && node --test dist/index.test.js`
Expected: PASS (both tests).

> **Note for implementer:** confirm the exact `StreamableHTTPServerTransport` constructor option name against the installed `@modelcontextprotocol/sdk` version (the SDK's transport API has changed across minor versions). If `sessionIdGenerator` is not the current option, adapt to the installed version's signature and note it in your report — the invariant is: `/mcp` speaks Streamable HTTP MCP and `/health` returns `{status:"ok"}`. Do not downgrade the SDK to match this snippet.

- [ ] **Step 5: Commit**

```bash
cd soapbox-costing && git add src/index.ts src/index.test.ts && git commit -m "feat: MCP server skeleton (health + list_measures stub + tool-registry extension point)"
```

---

### Task 3: Plugin packaging

**Files:**
- Create: `soapbox-costing/.claude-plugin/plugin.json`
- Create: `soapbox-costing/.mcp.json`
- Create: `soapbox-costing/README.md`
- Create: `soapbox-costing/LICENSE` (Apache-2.0, matching `crrem-skills`)

**Interfaces:**
- Produces: an installable Claude plugin that points at the deployed MCP. Consumed by the plugin catalog registration (later) and by portfolios.

- [ ] **Step 1: Create `.claude-plugin/plugin.json`**

```json
{
  "name": "soapbox-costing",
  "version": "0.1.0",
  "description": "Construction cost intelligence for building decarbonization — CapEx (low/base/high), OpEx delta, distributed-energy economics, and electrical service-capacity estimates, with surfaced citations.",
  "author": { "name": "Soapbox", "url": "https://soapbox.build" },
  "homepage": "https://github.com/soapboxbuild/soapbox-costing",
  "license": "Apache-2.0",
  "mcpServers": {
    "costing": { "type": "http", "url": "https://costing.mcp.soapbox.build/mcp" }
  },
  "skills": ["skills"]
}
```

> Note: `skills/` and `agents/` are added in Plan 5; an empty/absent `skills` dir is acceptable at this stage (the key is declared for forward-compat).

- [ ] **Step 2: Create `.mcp.json`**

```json
{
  "mcpServers": {
    "costing": { "type": "http", "url": "https://costing.mcp.soapbox.build/mcp" }
  }
}
```

- [ ] **Step 3: Create `README.md`** (short — purpose, MCP URL, "data sources & licensing" note pointing at the soapbox-agent spec, "grows over time" reference-library note). Keep under 40 lines.

- [ ] **Step 4: Create `LICENSE`** — Apache-2.0 text (copy from `crrem-skills/LICENSE`).

- [ ] **Step 5: Validate manifests**

Run: `cd soapbox-costing && node -e "JSON.parse(require('fs').readFileSync('.claude-plugin/plugin.json')); JSON.parse(require('fs').readFileSync('.mcp.json')); console.log('manifests OK')"`
Expected: `manifests OK`.

- [ ] **Step 6: Commit**

```bash
cd soapbox-costing && git add .claude-plugin/plugin.json .mcp.json README.md LICENSE && git commit -m "feat: plugin packaging (manifest + mcp.json + readme + license)"
```

---

### Task 4: Create GitHub repo + deploy to `soapbox-mcps` + DNS  ⚠️ OUTWARD-FACING — confirm with human before executing

**Files:** none (infra actions).

**Interfaces:**
- Produces: `https://costing.mcp.soapbox.build/mcp` live; repo pushed to `soapboxbuild/soapbox-costing`.

> **This task performs irreversible/outward-facing actions (create public repo, deploy a service, set DNS). The SDD controller MUST pause and get explicit human go-ahead before executing it, and confirm the Railway project + Cloudflare zone targets.**

- [ ] **Step 1: Create the GitHub repo** under `soapboxbuild` and push `main`.

```bash
cd soapbox-costing && gh repo create soapboxbuild/soapbox-costing --public --source=. --remote=origin --push
```
Expected: repo created (public, matching the `crrem-*` siblings), `main` pushed.

- [ ] **Step 2: Create a new service in the `soapbox-mcps` Railway project** from the repo, and deploy. Use the Railway MCP/CLI against project `soapbox-mcps` (do NOT create a new project). Set no env vars yet (none needed for the skeleton).

Expected: build succeeds (nixpacks runs `npm run build`), service healthy on `/health`.

- [ ] **Step 3: Add the custom domain** `costing.mcp.soapbox.build` to the service (`customDomainCreate`), then **immediately add the matching CNAME in Cloudflare** for the `mcp.soapbox.build` zone → the Railway-provided target. (Watch for the doubled-TXT gotcha; verify only one record.)

- [ ] **Step 4: Verify the live endpoint**

Run: `curl -fsS https://costing.mcp.soapbox.build/health`
Expected: `{"status":"ok"}` (allow a few minutes for DNS + cert).

- [ ] **Step 5: Verify MCP handshake over the live URL** — a `tools/list` returns `list_measures`.

Run (adapt to available MCP client / curl JSON-RPC):
`curl -fsS -X POST https://costing.mcp.soapbox.build/mcp -H 'content-type: application/json' -H 'accept: application/json, text/event-stream' -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'`
Expected: response listing the `list_measures` tool. (If the transport requires an `initialize` first, do that; the invariant is `list_measures` is discoverable.)

- [ ] **Step 6: Record the Railway service ID + domain** in the repo README (ops note) and commit.

---

## Self-Review

- **Spec coverage:** This plan implements the spec's "Repository & packaging" + "Rollout step 1 (scaffold + empty MCP deployed)" only. Tools, data, skill, persona, reference library, and rewiring are Plans 2–6 — intentionally out of scope here.
- **Placeholder scan:** none — all code/commands are concrete. Task 2 Step 4 flags the one version-sensitive API (transport constructor) as an implementer verification, not a placeholder.
- **Type consistency:** `buildServer()` return shape (`{httpServer, mcpServer}`) and the `registerTools(server)` extension point are the interfaces Plans 2–6 consume; named consistently here.
- **Outward-facing:** Task 4 is gated behind explicit human confirmation.
