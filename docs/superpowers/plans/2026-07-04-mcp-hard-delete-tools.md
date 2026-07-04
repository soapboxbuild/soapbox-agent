# Hard-Delete Tools (verifier + retrofit MCPs) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `retrofit__delete_measure` and `verifier__delete_finding` hard-delete tools, each cascading its Files-backed ledger cleanly, plus a shared re-index fix so re-rendering is idempotent.

**Architecture:** The delete cascade lives inside each MCP's storage module (`register.ts` / `ledger.ts`), mirroring the write cascade already there. Deleting one entry re-renders the client `.md` if others remain, or fully tears down the storage objects + `files` row (embeddings cascade off the `files` FK) if it was the last. A one-line fix in soapbox-api's `indexFile` deletes existing embeddings before inserting, making re-index idempotent and fixing a pre-existing duplicate-accumulation bug.

**Tech Stack:** TypeScript, `@modelcontextprotocol/sdk` (McpServer), Zod, Supabase JS (storage + Postgres), vitest 3. Three repos: `soapbox-platform` (apps/api), `retrofit-mcp`, `verifier-mcp`.

## Global Constraints

- **vitest on this VM:** run with `--pool=forks --poolOptions.forks.singleFork=true` (default worker pool hangs here).
- **`asset_id` = the Soapbox asset UUID**, never an Audette uid — enforced by the existing `resolveScope` guard; do not bypass it.
- **Storage bucket** is `asset-files`; uploads use `contentType: 'text/plain'` (the bucket's mime allowlist rejects markdown/ndjson).
- **Never fail silently:** every Supabase/storage/fetch error must propagate as a thrown Error so the MCP layer surfaces a structured tool error. Match the existing `throw new Error('<fn>: <what> failed: ...')` style.
- **Both MCPs deploy to the `soapbox-mcps` Railway project** (id `e5434a34-f54d-42cc-8f12-1f5cf9e9a9b5`, env `production`).
- **Hard delete is irreversible.** Tool descriptions must point callers to the soft alternatives (`update_measure_state` / `resolve_finding`) for a reversible hide.

---

### Task 1: Idempotent re-index (soapbox-api `indexFile`)

Delete existing embeddings for a file before inserting new ones, so re-rendering a ledger `.md` doesn't accumulate duplicate chunks. Independent of the MCP work and independently valuable, but a correctness dependency for the re-render path in Tasks 2 & 4.

**Files:**
- Modify: `soapbox-platform/apps/api/src/services/rag-indexer.ts` (the `indexFile` function, around line 58–69)
- Test: `soapbox-platform/apps/api/test/services/rag-indexer.test.ts`

**Interfaces:**
- Consumes: nothing new.
- Produces: no signature change — `indexFile({ fileId, assetId?, portfolioId?, content })` still returns `Promise<void>`; behavior now clears prior `embeddings` rows for `fileId` before insert.

- [ ] **Step 1: Write the failing test**

Add inside the existing `describe('indexFile', ...)` block in `test/services/rag-indexer.test.ts`:

```ts
  it('deletes existing embeddings for the file before inserting (idempotent re-index)', async () => {
    const deleteEq = vi.fn().mockResolvedValue({ error: null })
    const embeddingsChain: any = {
      insert: vi.fn().mockResolvedValue({ error: null }),
      delete: vi.fn(() => ({ eq: deleteEq })),
    }
    const updateChain: any = { update: vi.fn(), eq: vi.fn() }
    updateChain.update.mockReturnValue(updateChain)
    updateChain.eq.mockResolvedValue({ error: null })

    vi.mocked(supabase.from).mockImplementation((table) =>
      (table === 'embeddings' ? embeddingsChain : updateChain) as any
    )

    await indexFile({ fileId: 'f1', assetId: 'a1', content: 'Hello world. This is a test.' })

    expect(embeddingsChain.delete).toHaveBeenCalled()
    expect(deleteEq).toHaveBeenCalledWith('file_id', 'f1')
    // delete must precede insert
    const deleteOrder = embeddingsChain.delete.mock.invocationCallOrder[0]
    const insertOrder = embeddingsChain.insert.mock.invocationCallOrder[0]
    expect(deleteOrder).toBeLessThan(insertOrder)
  })
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd soapbox-platform/apps/api && npx vitest run test/services/rag-indexer.test.ts --pool=forks --poolOptions.forks.singleFork=true`
Expected: FAIL — `embeddingsChain.delete` not called (current code only inserts). The existing `embeddings.insert` mock also needs the `delete` method, so without the fix the new test fails on the assertion, not a mock crash.

- [ ] **Step 3: Add the delete-before-insert**

In `src/services/rag-indexer.ts`, in `indexFile`, insert immediately **before** the `const { error } = await supabase.from('embeddings').insert(rows)` line:

```ts
  // Re-index is idempotent: clear prior chunks for this file before inserting.
  // There is no unique constraint on (file_id, chunk_index), so without this
  // every re-render (any ledger/register update, not just delete) accumulates
  // duplicate embedding rows. Placed after chunking so a re-render with content
  // (our .md always has a header) always clears then repopulates.
  const { error: clearErr } = await supabase.from('embeddings').delete().eq('file_id', fileId)
  if (clearErr) throw new Error(`Embedding cleanup failed: ${clearErr.message}`)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd soapbox-platform/apps/api && npx vitest run test/services/rag-indexer.test.ts --pool=forks --poolOptions.forks.singleFork=true`
Expected: PASS (all tests in the file, including the existing `embeds chunks and inserts` — update its mock if it lacks `delete`; see note).

> Note: the existing `'embeds chunks and inserts into embeddings table'` test builds `insertChain = { insert: ... }` without a `delete`. Add `delete: vi.fn(() => ({ eq: vi.fn().mockResolvedValue({ error: null }) }))` to that `insertChain` so the new code path has a mock to call.

- [ ] **Step 5: Commit**

```bash
cd soapbox-platform && git add apps/api/src/services/rag-indexer.ts apps/api/test/services/rag-indexer.test.ts
git commit -m "fix(rag): clear prior embeddings before re-index (idempotent)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: `deleteMeasure` + teardown in retrofit `register.ts`

**Files:**
- Modify: `retrofit-mcp/src/register.ts` (add two functions after `getMeasures`)
- Test: `retrofit-mcp/test/register.test.ts` (add an `describe('deleteMeasure', ...)` block)

**Interfaces:**
- Consumes (already in `register.ts`): `type Scope = { portfolioId: string; assetId: string }`, `loadMeasures(scope)`, `saveMeasures(scope, measures)`, private `findExistingFilesRow(scope)`, private `jsonlPath(scope)` (= `${assetId}/retrofit/measures.jsonl`), `getClient()`, `BUCKET` (= `'asset-files'`).
- Produces: `deleteMeasure(scope: Scope, measureId: string): Promise<{ deleted: true; remaining: number }>` — used by Task 3.

- [ ] **Step 1: Write the failing tests**

Add to `retrofit-mcp/test/register.test.ts`. First extend the shared `makeFilesTable` mock to support `.delete().eq()`, and the storage mock to support `.remove()`. Replace the existing `makeFilesTable` and the storage block of `mockSupabaseModule` with these augmented versions:

```ts
function makeFilesTable(existingRow: { id: string } | null, calls: Record<string, unknown[]>) {
  return {
    select: () => ({
      eq: (col: string, val: unknown) => {
        const state = { filters: [[col, val]] as [string, unknown][] }
        const builder = {
          eq: (col2: string, val2: unknown) => { state.filters.push([col2, val2]); return builder },
          maybeSingle: () => { calls.selectFilters = state.filters; return Promise.resolve({ data: existingRow, error: null }) },
        }
        return builder
      },
    }),
    insert: (row: Record<string, unknown>) => { calls.insert = [row]; return Promise.resolve({ error: null }) },
    update: (patch: Record<string, unknown>) => ({ eq: (_c: string, id: unknown) => { calls.update = [patch, id]; return Promise.resolve({ error: null }) } }),
    delete: () => ({ eq: (_c: string, id: unknown) => { calls.filesDelete = [id]; return Promise.resolve({ error: null }) } }),
  }
}
```

And in `mockSupabaseModule`'s `storage.from`, add a `remove` alongside `download`/`upload`:

```ts
          remove: (paths: string[]) => { opts.calls.storageRemove = [paths]; return Promise.resolve({ error: null }) },
```

Then add the test block:

```ts
describe('deleteMeasure', () => {
  const originalFetch = global.fetch
  beforeEach(() => {
    vi.resetModules(); vi.doUnmock('@supabase/supabase-js')
    process.env.SUPABASE_URL = 'http://example.invalid'
    process.env.SUPABASE_SERVICE_ROLE_KEY = 'test-key'
    process.env.SOAPBOX_API_URL = 'https://api.example.invalid'
    process.env.MCP_SERVER_SECRET = 'shh-secret'
  })
  afterEach(() => { global.fetch = originalFetch; vi.restoreAllMocks() })

  it('removes one measure and re-saves the rest when others remain', async () => {
    const calls: Record<string, unknown[]> = {}
    const m1 = { ...base(), id: 'm1', status: 'recommended' as const }
    const m2 = { ...base(), id: 'm2', name: 'Second', status: 'proposed' as const }
    vi.doMock('@supabase/supabase-js', () => mockSupabaseModule({
      downloadResult: { data: { text: async () => [m1, m2].map((m) => JSON.stringify(m)).join('\n') + '\n' }, error: null },
      existingFilesRow: { id: 'file-1' }, calls,
    }))
    global.fetch = vi.fn(async () => ({ ok: true, status: 200 } as Response)) as unknown as typeof fetch

    const { deleteMeasure } = await import('../src/register.js')
    const res = await deleteMeasure({ portfolioId: 'p1', assetId: 'a1' }, 'm1')

    expect(res).toEqual({ deleted: true, remaining: 1 })
    // re-saved jsonl no longer contains m1
    const [, jsonlBody] = calls.uploadJsonl as [string, string, unknown]
    const rows = jsonlBody.trim().split('\n').map((l) => JSON.parse(l))
    expect(rows).toHaveLength(1)
    expect(rows[0].id).toBe('m2')
    // no teardown when others remain
    expect(calls.storageRemove).toBeFalsy()
    expect(calls.filesDelete).toBeFalsy()
  })

  it('tears down storage + files row when deleting the last measure', async () => {
    const calls: Record<string, unknown[]> = {}
    const only = { ...base(), id: 'm1', status: 'recommended' as const }
    vi.doMock('@supabase/supabase-js', () => mockSupabaseModule({
      downloadResult: { data: { text: async () => JSON.stringify(only) + '\n' }, error: null },
      existingFilesRow: { id: 'file-1' }, calls,
    }))
    const { deleteMeasure } = await import('../src/register.js')
    const res = await deleteMeasure({ portfolioId: 'p1', assetId: 'a1' }, 'm1')

    expect(res).toEqual({ deleted: true, remaining: 0 })
    // removed both storage objects
    const [paths] = calls.storageRemove as [string[]]
    expect(paths).toContain('a1/retrofit/measures.jsonl')
    expect(paths).toContain('a1/file-1/measures.md')
    // deleted the files row (embeddings cascade off the FK)
    expect(calls.filesDelete).toEqual(['file-1'])
    // did not re-save an empty jsonl
    expect(calls.uploadJsonl).toBeFalsy()
  })

  it('throws when the measure id is not in the register', async () => {
    const calls: Record<string, unknown[]> = {}
    vi.doMock('@supabase/supabase-js', () => mockSupabaseModule({
      downloadResult: { data: { text: async () => JSON.stringify({ ...base(), id: 'm1' }) + '\n' }, error: null },
      existingFilesRow: { id: 'file-1' }, calls,
    }))
    const { deleteMeasure } = await import('../src/register.js')
    await expect(deleteMeasure({ portfolioId: 'p1', assetId: 'a1' }, 'nope'))
      .rejects.toThrow(/not found/)
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd retrofit-mcp && npx vitest run test/register.test.ts --pool=forks --poolOptions.forks.singleFork=true`
Expected: FAIL — `deleteMeasure` is not exported from `../src/register.js`.

- [ ] **Step 3: Implement `deleteMeasure` + `teardownRegisterFile`**

In `retrofit-mcp/src/register.ts`, add after `getMeasures`:

```ts
async function teardownRegisterFile(scope: Scope): Promise<void> {
  const supabase = getClient()
  const existing = await findExistingFilesRow(scope)
  const paths = [jsonlPath(scope)]
  if (existing) paths.push(`${scope.assetId}/${existing.id}/measures.md`)
  const { error: rmErr } = await supabase.storage.from(BUCKET).remove(paths)
  if (rmErr) throw new Error(`teardownRegisterFile: storage remove failed: ${rmErr.message ?? rmErr}`)
  if (existing) {
    // embeddings.file_id has ON DELETE CASCADE on files(id), so deleting the
    // files row removes the RAG chunks automatically.
    const { error: delErr } = await supabase.from('files').delete().eq('id', existing.id)
    if (delErr) throw new Error(`teardownRegisterFile: files row delete failed: ${delErr.message ?? delErr}`)
  }
}

export async function deleteMeasure(scope: Scope, measureId: string): Promise<{ deleted: true; remaining: number }> {
  const measures = await loadMeasures(scope)
  if (!measures.some((m) => m.id === measureId)) {
    throw new Error(`measure_id ${measureId} not found in asset ${scope.assetId}'s measure register`)
  }
  const next = measures.filter((m) => m.id !== measureId)
  if (next.length > 0) {
    await saveMeasures(scope, next)
  } else {
    await teardownRegisterFile(scope)
  }
  return { deleted: true, remaining: next.length }
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd retrofit-mcp && npx vitest run test/register.test.ts --pool=forks --poolOptions.forks.singleFork=true`
Expected: PASS (all register tests).

- [ ] **Step 5: Commit**

```bash
cd retrofit-mcp && git add src/register.ts test/register.test.ts
git commit -m "feat: deleteMeasure — hard delete with re-render or teardown

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: `delete_measure` MCP tool (retrofit `index.ts`)

**Files:**
- Modify: `retrofit-mcp/src/index.ts` (add a `server.tool('delete_measure', ...)` next to `update_measure_state`; import `deleteMeasure`)
- Test: `retrofit-mcp/test/server.test.ts`

**Interfaces:**
- Consumes: `deleteMeasure` from Task 2; existing `resolveScope(scope, assetId)`, `requireAssetScope(resolved, assetId)`, `textResult(value)` helpers in `index.ts`.
- Produces: MCP tool `delete_measure({ asset_id, measure_id })`.

- [ ] **Step 1: Write the failing test**

In `retrofit-mcp/test/server.test.ts`, add `'delete_measure'` to the `TOOL_NAMES` array, and extend the `vi.mock('../src/register.js', ...)` factory to include `deleteMeasure`:

```ts
vi.mock('../src/register.js', () => ({
  saveMeasure: vi.fn(async () => ({ id: 'm1' })),
  getMeasures: vi.fn(async () => []),
  deleteMeasure: vi.fn(async () => ({ deleted: true, remaining: 0 })),
}))
```

Then add a test:

```ts
  it('delete_measure returns a deleted result', async () => {
    const raw = await rpc('tools/call', { name: 'delete_measure', arguments: { asset_id: 'a1', measure_id: 'm1' } })
    expect(raw).toMatch(/"deleted":true/)
  })
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd retrofit-mcp && npx vitest run test/server.test.ts --pool=forks --poolOptions.forks.singleFork=true`
Expected: FAIL — `tools/list` does not contain `delete_measure`; the call errors (unknown tool).

- [ ] **Step 3: Register the tool**

In `retrofit-mcp/src/index.ts`, add `deleteMeasure` to the existing `import { ... } from './register.js'`, then add this `server.tool(...)` immediately after the `update_measure_state` registration:

```ts
  server.tool(
    'delete_measure',
    "Hard-delete a measure from an asset's retrofit register by id. Irreversible: removes the entry, re-renders the client measures.md (or tears the file down if it was the last measure), and cleans the RAG index. To hide a measure while keeping the record, use update_measure_state instead.",
    {
      asset_id: z.string().describe('Asset (Soapbox asset id) whose register to delete from'),
      measure_id: z.string().describe('The measure id to hard-delete'),
    },
    async ({ asset_id, measure_id }) => {
      const resolved = await resolveScope(scope, asset_id)
      const registerScope = requireAssetScope(resolved, asset_id)
      const result = await deleteMeasure(registerScope, measure_id)
      return textResult(result)
    }
  )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd retrofit-mcp && npx vitest run --pool=forks --poolOptions.forks.singleFork=true`
Expected: PASS (whole suite). Also update the `'lists all eight tools'` test title/count to nine if it asserts a count — it iterates `TOOL_NAMES` so adding the name is sufficient; rename to `'lists all nine tools'` for accuracy.

- [ ] **Step 5: Commit**

```bash
cd retrofit-mcp && git add src/index.ts test/server.test.ts
git commit -m "feat: delete_measure MCP tool

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 4: `deleteFinding` + teardown in verifier `ledger.ts`

**Files:**
- Modify: `verifier-mcp/src/ledger.ts` (add two functions after `verificationStatus`)
- Test: `verifier-mcp/test/ledger.test.ts`

**Interfaces:**
- Consumes (already in `ledger.ts`): `type Scope = { portfolioId: string; assetId?: string }`, `loadFindings(scope)`, `saveFindings(scope, findings)`, private `findExistingFilesRow(scope)`, private `scopePrefix(scope)` (asset id, or `portfolio-<id>`), private `jsonlPath(scope)`, `getClient()`, `BUCKET`.
- Produces: `deleteFinding(scope: Scope, id: string): Promise<{ deleted: true; remaining: number }>` — used by Task 5.

- [ ] **Step 1: Write the failing tests**

Inspect `verifier-mcp/test/ledger.test.ts` for its supabase mock. It follows the same `vi.doMock('@supabase/supabase-js', ...)` shape as retrofit's `register.test.ts`. If the mock's files-table lacks `.delete()` and storage lacks `.remove()`, add them exactly as in Task 2 Step 1 (files table `delete: () => ({ eq: (_c, id) => { calls.filesDelete = [id]; return Promise.resolve({ error: null }) } })`; storage `remove: (paths) => { calls.storageRemove = [paths]; return Promise.resolve({ error: null }) }`). Then add:

```ts
describe('deleteFinding', () => {
  // reuse this file's existing beforeEach/afterEach env + module-reset setup
  const f = (id: string, over: Partial<any> = {}) => ({
    id, ts: '2026-07-04T00:00:00.000Z', claim: `claim ${id}`, verdict: 'conflict',
    severity: 'high', kind: 'data-quality', evidence: ['e'], sources: ['s'], status: 'open', ...over,
  })

  it('removes one finding and re-saves the rest when others remain', async () => {
    const calls: Record<string, unknown[]> = {}
    vi.doMock('@supabase/supabase-js', () => mockSupabaseModule({
      downloadResult: { data: { text: async () => [f('x1'), f('x2')].map((x) => JSON.stringify(x)).join('\n') + '\n' }, error: null },
      existingFilesRow: { id: 'file-9' }, calls,
    }))
    global.fetch = vi.fn(async () => ({ ok: true, status: 200 } as Response)) as unknown as typeof fetch
    const { deleteFinding } = await import('../src/ledger.js')
    const res = await deleteFinding({ portfolioId: 'p1', assetId: 'a1' }, 'x1')
    expect(res).toEqual({ deleted: true, remaining: 1 })
    const [, jsonlBody] = calls.uploadJsonl as [string, string, unknown]
    const rows = jsonlBody.trim().split('\n').map((l) => JSON.parse(l))
    expect(rows).toHaveLength(1)
    expect(rows[0].id).toBe('x2')
    expect(calls.storageRemove).toBeFalsy()
  })

  it('tears down storage + files row when deleting the last finding', async () => {
    const calls: Record<string, unknown[]> = {}
    vi.doMock('@supabase/supabase-js', () => mockSupabaseModule({
      downloadResult: { data: { text: async () => JSON.stringify(f('x1')) + '\n' }, error: null },
      existingFilesRow: { id: 'file-9' }, calls,
    }))
    const { deleteFinding } = await import('../src/ledger.js')
    const res = await deleteFinding({ portfolioId: 'p1', assetId: 'a1' }, 'x1')
    expect(res).toEqual({ deleted: true, remaining: 0 })
    const [paths] = calls.storageRemove as [string[]]
    expect(paths).toContain('a1/verification/findings.jsonl')
    expect(paths).toContain('a1/file-9/findings.md')
    expect(calls.filesDelete).toEqual(['file-9'])
  })

  it('tears down a portfolio-level ledger using the portfolio prefix', async () => {
    const calls: Record<string, unknown[]> = {}
    vi.doMock('@supabase/supabase-js', () => mockSupabaseModule({
      downloadResult: { data: { text: async () => JSON.stringify(f('x1')) + '\n' }, error: null },
      existingFilesRow: { id: 'file-9' }, calls,
    }))
    const { deleteFinding } = await import('../src/ledger.js')
    const res = await deleteFinding({ portfolioId: 'p1' }, 'x1')  // no assetId
    expect(res.remaining).toBe(0)
    const [paths] = calls.storageRemove as [string[]]
    expect(paths).toContain('portfolio-p1/verification/findings.jsonl')
    expect(paths).toContain('portfolio-p1/file-9/findings.md')
  })

  it('throws when the finding id is not in the ledger', async () => {
    const calls: Record<string, unknown[]> = {}
    vi.doMock('@supabase/supabase-js', () => mockSupabaseModule({
      downloadResult: { data: { text: async () => JSON.stringify(f('x1')) + '\n' }, error: null },
      existingFilesRow: { id: 'file-9' }, calls,
    }))
    const { deleteFinding } = await import('../src/ledger.js')
    await expect(deleteFinding({ portfolioId: 'p1', assetId: 'a1' }, 'nope')).rejects.toThrow(/not found/)
  })
})
```

> If `ledger.test.ts` does not already define a `mockSupabaseModule`/`makeFilesTable` (some verifier tests only cover pure functions), copy the two helpers verbatim from `retrofit-mcp/test/register.test.ts` (Task 2 Step 1 augmented versions), changing the `.jsonl`/`.md` filename branch in the storage `upload` mock to `findings` and the `download` path handling to match — the helper is filename-agnostic except the `uploadJsonl`/`uploadMd` key split, which keys off the `.jsonl` suffix and needs no change.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd verifier-mcp && npx vitest run test/ledger.test.ts --pool=forks --poolOptions.forks.singleFork=true`
Expected: FAIL — `deleteFinding` not exported from `../src/ledger.js`.

- [ ] **Step 3: Implement `deleteFinding` + `teardownLedgerFile`**

In `verifier-mcp/src/ledger.ts`, add after `verificationStatus`:

```ts
async function teardownLedgerFile(scope: Scope): Promise<void> {
  const supabase = getClient()
  const prefix = scopePrefix(scope)
  const existing = await findExistingFilesRow(scope)
  const paths = [jsonlPath(scope)]
  if (existing) paths.push(`${prefix}/${existing.id}/findings.md`)
  const { error: rmErr } = await supabase.storage.from(BUCKET).remove(paths)
  if (rmErr) throw new Error(`teardownLedgerFile: storage remove failed: ${rmErr.message ?? rmErr}`)
  if (existing) {
    // embeddings.file_id ON DELETE CASCADE removes RAG chunks with the row.
    const { error: delErr } = await supabase.from('files').delete().eq('id', existing.id)
    if (delErr) throw new Error(`teardownLedgerFile: files row delete failed: ${delErr.message ?? delErr}`)
  }
}

export async function deleteFinding(scope: Scope, id: string): Promise<{ deleted: true; remaining: number }> {
  const findings = await loadFindings(scope)
  if (!findings.some((x) => x.id === id)) {
    throw new Error(`finding ${id} not found in ${scopePrefix(scope)}'s findings ledger`)
  }
  const next = findings.filter((x) => x.id !== id)
  if (next.length > 0) {
    await saveFindings(scope, next)
  } else {
    await teardownLedgerFile(scope)
  }
  return { deleted: true, remaining: next.length }
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd verifier-mcp && npx vitest run test/ledger.test.ts --pool=forks --poolOptions.forks.singleFork=true`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd verifier-mcp && git add src/ledger.ts test/ledger.test.ts
git commit -m "feat: deleteFinding — hard delete with re-render or teardown

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 5: `delete_finding` MCP tool (verifier `index.ts`)

**Files:**
- Modify: `verifier-mcp/src/index.ts` (add a `server.tool('delete_finding', ...)` next to `resolve_finding`; import `deleteFinding`)
- Test: `verifier-mcp/test/server.test.ts`

**Interfaces:**
- Consumes: `deleteFinding` from Task 4; existing `resolveScope(scope, asset_id)` and `textResult` helpers in `index.ts`. Note verifier's `resolveScope` returns `{ portfolioId, assetId? }` which is exactly `deleteFinding`'s `Scope` — no `requireAssetScope` needed.
- Produces: MCP tool `delete_finding({ id, asset_id? })`.

- [ ] **Step 1: Write the failing test**

In `verifier-mcp/test/server.test.ts`, add `'delete_finding'` to the tool-name list it checks, and if it mocks `../src/ledger.js`, add `deleteFinding: vi.fn(async () => ({ deleted: true, remaining: 0 }))` to that factory. Add:

```ts
  it('delete_finding returns a deleted result', async () => {
    const raw = await rpc('tools/call', { name: 'delete_finding', arguments: { id: 'x1', asset_id: 'a1' } })
    expect(raw).toMatch(/"deleted":true/)
  })
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd verifier-mcp && npx vitest run test/server.test.ts --pool=forks --poolOptions.forks.singleFork=true`
Expected: FAIL — `delete_finding` not registered.

- [ ] **Step 3: Register the tool**

In `verifier-mcp/src/index.ts`, add `deleteFinding` to the `import { ... } from './ledger.js'`, then add after the `resolve_finding` registration:

```ts
  server.tool(
    'delete_finding',
    'Hard-delete a finding from the ledger by id. Irreversible: removes the entry, re-renders findings.md (or tears the file down if it was the last finding), and cleans the RAG index. To keep the record but mark it handled, use resolve_finding (confirmed/dismissed) instead.',
    {
      id: z.string().describe('Finding id to hard-delete'),
      asset_id: z.string().optional().describe('Asset the finding is scoped to; omit for a portfolio-level finding'),
    },
    async ({ id, asset_id }) => {
      const resolved = await resolveScope(scope, asset_id)
      const result = await deleteFinding(resolved, id)
      return textResult(result)
    }
  )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd verifier-mcp && npx vitest run --pool=forks --poolOptions.forks.singleFork=true`
Expected: PASS (whole suite).

- [ ] **Step 5: Commit**

```bash
cd verifier-mcp && git add src/index.ts test/server.test.ts
git commit -m "feat: delete_finding MCP tool

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 6: Deploy, bump TOOLS_VERSION, live smoke

**Files:**
- Modify: `soapbox-platform/apps/api/src/services/agent-config.ts` (`const TOOLS_VERSION = 'v6'` → `'v7'`, extend the trailing comment)

**Interfaces:**
- Consumes: deployed retrofit-mcp & verifier-mcp; the live smoke reuses `scratchpad/mcpcall.py` from the 2026-07-04 dry run (service bearer = `MCP_SERVER_SECRET` from the Railway service env; headers `x-soapbox-portfolio-id`/`x-soapbox-organization-id`).
- Produces: the new tools live on portfolio/asset agents.

- [ ] **Step 1: Deploy both MCPs**

Push each repo's branch and deploy via Railway (soapbox-mcps project). Both services auto-deploy from their connected repo/branch on push; confirm each redeploys:

```bash
cd retrofit-mcp && git push && cd ../verifier-mcp && git push
```

Watch the two services in the `soapbox-mcps` project redeploy to green (Railway dashboard or `railway logs`). Confirm health: `curl -s -o /dev/null -w '%{http_code}\n' https://retrofit-mcp-production.up.railway.app/health` and the verifier equivalent both return `200`.

- [ ] **Step 2: Bump TOOLS_VERSION**

In `soapbox-platform/apps/api/src/services/agent-config.ts`, change `const TOOLS_VERSION = 'v6'` to `'v7'` and append to its comment: `// v7: verifier__delete_finding + retrofit__delete_measure`. This busts the agent-config cache so asset/portfolio agents re-fetch the tool list and register the new tools (the two-runtime-tool-gates requirement). Commit and deploy soapbox-api:

```bash
cd soapbox-platform && git add apps/api/src/services/agent-config.ts
git commit -m "chore: TOOLS_VERSION v7 — delete_measure + delete_finding

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
git push
```

- [ ] **Step 3: Live smoke against Greystar / 212 Stuart**

Reuse `scratchpad/mcpcall.py` (re-fetch the 64-char `MCP_SERVER_SECRET` from the verifier-mcp Railway env if the scratchpad copy was scrubbed). Asset `5ec53668-b12f-4812-b003-e120883bb183`, portfolio `8ed1db55-327b-42af-916f-33907ed4cd7a`, org `bf7f0315-4fd4-4b8e-baab-d08cb7f6da13`.

Retrofit: create a labeled test measure, delete it, confirm no manual cleanup needed:
```bash
python3 mcpcall.py retrofit evaluate_measure '{"asset_id":"5ec53668-b12f-4812-b003-e120883bb183","measure":{"measure_family":"controls-rcx","name":"DRYRUN DELETE-ME","candidate_source":"originated","cost":{"value":1000,"unit":"USD","engine":"soapbox-dcf"},"owner_savings_annual":{"value":200,"unit":"USD/yr","engine":"cashflow-mcp"},"noi_delta_annual":{"value":200,"unit":"USD/yr","engine":"soapbox-dcf"},"cap_rate":{"value":0.05,"unit":"ratio","source":"dryrun"},"feasibility":{"score":3,"site_conditions":"x","disruption":"light","contractor_reality":"x","staging":"x","sources":["dryrun"]},"future_proofing":{"rationale":"x","citations":[]}}}'
# take the returned id, then:
python3 mcpcall.py retrofit delete_measure '{"asset_id":"5ec53668-b12f-4812-b003-e120883bb183","measure_id":"<id>"}'
python3 mcpcall.py retrofit get_measure_state '{"asset_id":"5ec53668-b12f-4812-b003-e120883bb183"}'   # expect []
```
Expected: `delete_measure` returns `{"deleted":true,"remaining":0}`; register reads `[]`.

Verify the files row and storage are gone (no manual surgery this time):
```sql
SELECT count(*) FROM files WHERE asset_id='5ec53668-b12f-4812-b003-e120883bb183' AND folder='Retrofit';  -- expect 0
```

Verifier: same shape — `record_finding` → `delete_finding` → `list_findings` (expect `[]`) → confirm `files` row (folder `Verification`) count is 0.

- [ ] **Step 4: Confirm the two-gate registration on a real thread**

Send a message in a Greystar portfolio thread (or asset thread) that would list tools, or ask the agent to "delete measure X from asset Y" on a throwaway test measure, and confirm the agent both *sees* `retrofit__delete_measure`/`verifier__delete_finding` and *executes* them (no "requires_action but no pending calls" reset). If the tools are absent, re-check the `getConnectorMcpTools` list and the `resolveCustomToolCall` prefix gate per the two-runtime-tool-gates lesson.

- [ ] **Step 5: Update memory**

Update `verifier-retrofit-in-portfolio-analysis.md` (or a new `mcp-delete-tools` memory): tools shipped, TOOLS_VERSION v7, the embeddings-idempotency fix, and that the manual-cleanup recipe is now obsolete for single items.

---

## Self-Review

**Spec coverage:**
- Goal `delete_measure` → Tasks 2–3. ✓
- Goal `delete_finding` (asset_id optional) → Tasks 4–5 (portfolio-prefix teardown test in Task 4). ✓
- Full cascade (jsonl + md re-render OR teardown; embeddings via FK) → Tasks 2 & 4 teardown fns + tests. ✓
- Shared indexFile fix → Task 1. ✓
- Tenancy guard reused → Tasks 3 & 5 (`resolveScope`/`requireAssetScope`). ✓
- Non-goals (no clear-scope, no soft-delete, no un-delete) → not implemented. ✓
- Rollout / TOOLS_VERSION bump → Task 6. ✓
- Testing (present→removed; last→teardown; missing→throws; wrong-asset→scope error; re-index idempotent) → Tasks 1,2,4; wrong-asset scope error is enforced at the tool layer by `resolveScope` (already proven live in the dry run) and covered by Task 6 Step 4 rather than a unit test, since `resolveScope` does a real Supabase lookup not present in the module mocks.

**Placeholder scan:** none — every code/step is concrete. The one conditional ("if ledger.test.ts lacks the mock helpers") gives the exact fallback (copy from register.test.ts).

**Type consistency:** `deleteMeasure(scope, measureId)` / `deleteFinding(scope, id)` both return `{ deleted: true; remaining: number }`, used identically in Tasks 3/5 and asserted the same way in tests. `Scope` types match each module's existing definition (retrofit assetId required; verifier assetId optional). Storage paths match the modules' `jsonlPath`/`scopePrefix`.
</content>
