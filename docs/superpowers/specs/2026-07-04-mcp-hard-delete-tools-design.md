# Hard-Delete Tools for the Verifier & Retrofit MCP Ledgers

_2026-07-04. Adds a hard-delete tool to each of the two Files-backed MCP ledgers
(`retrofit-mcp` measure register, `verifier-mcp` findings ledger), plus a shared
re-index correctness fix. Motivated by the Greystar dry run, where removing a single
test measure/finding required multi-step manual surgery (delete jsonl object, files row,
embeddings, md object) because no delete tool exists._

## Problem

Both MCPs are append/update-only. `retrofit__update_measure_state` and
`verifier__resolve_finding` change an item's *status* but never remove it. There is no way
to erase an entry created by mistake, during testing, or against the wrong asset — the row
persists in the client-visible `.md` render and the RAG index forever. Cleanup today means
hand-deleting across storage + `files` + `embeddings` with the service-role key.

## Goals / Non-Goals

**Goals**
- `retrofit-mcp`: `delete_measure(asset_id, measure_id)` — hard delete one measure. `asset_id`
  required (the register is always asset-scoped).
- `verifier-mcp`: `delete_finding(id, asset_id?)` — hard delete one finding. `asset_id` is
  **optional**, mirroring `record_finding` / `resolve_finding`: omit it to delete a
  portfolio-level finding (which lives at `<portfolioId>/verification/…`), pass it for an
  asset-scoped one. The teardown in step 5 keys off `scopePrefix(scope)` accordingly.
- Each fully cascades: jsonl entry removed, client `.md` re-rendered (or file torn down if it
  was the last entry), RAG embeddings cleaned, `files` row consistent.
- Same tenancy guard as every other tool (portfolio-scope caller may only delete within its own
  assets).

**Non-Goals (deferred)**
- No "clear whole register/ledger for an asset" command. The concrete need is per-item; a
  guarded clear-scope is a possible fast-follow, not this build.
- No soft-delete / withdraw status — already covered by existing statuses
  (`screened-out`, `dismissed`).
- No un-delete / trash. Hard delete is intentionally irreversible.

## Architecture

**Option A (chosen): the cascade lives in each MCP.** Each MCP already owns its full *write*
cascade — `register.ts` / `ledger.ts` write the `.jsonl`, re-render the `.md`, upsert the
`files` row, and call `soapbox-api /internal/index-file` on every save. Delete is the mirror of
that, in the same module, using the service-role client the module already holds. Rejected
alternative: a new `soapbox-api /internal/delete-file` endpoint — delete here is "remove one
line from a jsonl and re-render," which is register logic the API does not own; routing it
through the API adds a network hop and splits one cascade across two services.

### Delete flow (identical shape in both services)

Given `scope` (from trusted headers) and the item id:

1. Resolve scope with the existing guard. Retrofit: `requireAssetScope(await resolveScope(scope,
   asset_id), asset_id)` (asset_id required). Verifier: `await resolveScope(scope, asset_id)`
   where `asset_id` may be undefined (portfolio-level finding). `resolveScope` verifies any
   supplied asset belongs to the caller's portfolio (Supabase lookup) and throws otherwise;
   proven in the 2026-07-04 dry run to reject cross-portfolio access.
2. Load the current list. If no entry has the given id, **throw** a clear error
   (`measure_id <id> not found in asset <asset_id>'s register` / analogous for findings) —
   consistent with `update_measure_state`, which already throws on a missing id. Not a silent
   no-op.
3. `next = list.filter(item => item.id !== id)`.
4. **If `next.length > 0`:** call the existing `saveMeasures(scope, next)` /
   `saveFindings(scope, next)`. This re-uploads the jsonl, re-renders and re-uploads the `.md`,
   updates the `files` row size, and re-indexes.
5. **If `next.length === 0`** (deleted the last entry): full teardown — remove both storage
   objects (`<asset>/<kind>/<name>.jsonl` and `<asset>/<fileId>/<name>.md`) and delete the
   `files` row. `embeddings.file_id` has `ON DELETE CASCADE` on `files(id)`, so embeddings are
   removed automatically by the row delete — no explicit embeddings delete needed. (New helper,
   e.g. `teardownRegisterFile(scope)` in `register.ts` / the ledger analog, so the storage
   paths stay owned by the module that writes them.)
6. Return `{ deleted: true, remaining: next.length }`.

### Shared correctness fix (required dependency)

`rag-indexer.ts` `indexFile` currently `INSERT`s embedding rows without first removing prior
rows for the `file_id`, and `embeddings` has **no** unique constraint on
`(file_id, chunk_index)`. Every re-render — on *any* update, not just delete — therefore
accumulates duplicate chunks (stale RAG hits, unbounded growth). The delete re-render in step 4
would inherit this. Fix at the single choke point: in `indexFile`, delete existing embeddings
for the `file_id` before inserting.

```ts
// rag-indexer.ts, before the insert:
await supabase.from('embeddings').delete().eq('file_id', fileId)
```

This makes re-indexing idempotent and fixes the pre-existing update-path duplication for the
whole system, not only delete.

## Safety

- **Tenancy:** enforced by `resolveScope` + `requireAssetScope`, unchanged from every other tool.
  A portfolio-scoped agent can only delete within assets in its own portfolio.
- **No `confirm` flag:** deleting by an explicit id *is* the intent; there is no bulk/wildcard
  surface to guard. (A future clear-scope command WOULD require an explicit confirm.)
- **Irreversible by design.** Callers that want a reversible hide use the existing status tools.

## Testing

Per service, unit tests (vitest; this VM needs `--pool=forks --poolOptions.forks.singleFork=true`):
- item present → removed, `remaining` decremented, `.md` no longer contains it;
- deleting the last item → storage objects and `files` row gone, `get_measure_state` /
  `list_findings` returns `[]`;
- missing id → throws;
- id belonging to a different asset → scope error, nothing deleted;
- `indexFile` re-index → embeddings for the file_id equal the new chunk count (no duplicates).

Then a live smoke against Greystar / 212 Stuart mirroring the 2026-07-04 dry run: create a
labeled test entry, delete it via the new tool, confirm the register/ledger and `files` row are
clean with no manual surgery.

## Rollout

Both MCPs deploy to the `soapbox-mcps` Railway project. After merge + deploy, bump `TOOLS_VERSION`
in `agent-config.ts` so asset/portfolio agents pick up the new `verifier__*`/`retrofit__*` tool
in their registered tool set (the two-runtime-tool-gates lesson: the tool must be both listed via
`getConnectorMcpTools` and self-executed through the runtime gate).
</content>
