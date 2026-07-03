# Decarbonization Analysis — Agent Architecture Decision Record

**Date:** 2026-07-03
**Status:** Decided (Christopher). Near-term actions approved; plugin extraction deferred.
**Context:** first two live decarb engagements (Cortland Westminster pilot + the
Cortland Westminster app-thread run) surfaced the question: should the decarb
workflow become its own standalone agent plugin, like the Verifier and Retrofit
Specialist plugins?

---

## Decision

**No wholesale skill→plugin conversion, and not now.** Decarb stays an
orchestration **skill + persona**. The deterministic, must-be-guaranteed pieces
will later be extracted into a small **engagement/validation worker plugin** —
but only after the workflow stabilizes over several more real engagements.

The eventual target is *additive*, not a conversion:

```
decarb-plan  (SKILL + named analyst PERSONA)   ← orchestration, phase choreography, doctrine
      │ conducts
      ├── engagement plugin (NEW, later)        ← deterministic core: phase state, gates,
      │                                            building-model reconciliation, provenance
      ├── retrofit plugin (worker, exists)      ← measure evaluation
      ├── verifier plugin (worker, exists)      ← findings, verification gate
      ├── Audette (physics), ESPM (energy), BPD (benchmark), template (render)
      └── memory plugin (exists)
```

## Rationale

**Decarb is the general contractor, not a worker.** The Verifier and Retrofit
Specialist earn plugin status because each owns a domain with its own tools and
data. Decarb owns no unique tools — it *conducts* the workers plus Audette/ESPM/
BPD/template. Wrapping pure orchestration in an MCP server adds a server with no
unique tools. So "make the skill a plugin" is the wrong framing.

**What a plugin genuinely buys — guaranteed discipline (the Verifier/Retrofit
lesson).** Every failure in the live runs was the agent doing prose-managed work
unreliably. These pieces should be deterministic, server-enforced tools rather
than prompt discipline:
- **Engagement + phase state** — today a JSON file the agent hand-edits via
  `save_file`. As tools (`start_engagement`, `get_state`, `advance_phase`,
  `record_adjudication`) it becomes durable, queryable, resumable without the
  agent reconstructing it.
- **Gate enforcement** — render gate lives in the platform runtime; the two human
  gates live in prompt discipline. Server-owned gate state can't be prompted around.
- **Building-model reconciliation** — the ALTA-vs-Audette check that failed
  (17 modeled buildings vs 15 real structures, unreconciled GFA) is deterministic
  math; belongs in a tool, not agent arithmetic.
- **Provenance / source-of-truth ledger** — "which number came from where,"
  enforced structurally, with each displayed figure carrying its tier.

**Why defer.** The workflow changed ~10 times in a single session (gate
sequencing, allocation rule, building validation gate, calibration doctrine,
split estimation, units/benchmarking, IRR methodology). Freezing a state schema
and tool API into an MCP now locks in a shape still being discovered. Doctrine
and skill text are cheap to keep changing; a plugin schema is not.

## Extraction triggers (when to build the engagement plugin)

Build it once ALL of these hold:
1. Two to three more real engagements completed end-to-end (through render/export).
2. The phase sequence and the set of gate/state operations stop changing between runs.
3. A clear, recurring set of state operations and validation checks has emerged
   (the concrete tool surface is obvious, not speculative).
4. Prompt-only enforcement has demonstrably failed at least once more in a way a
   server-side tool would have prevented (evidence, not anticipation).

## Near-term actions (approved, no plugin, no schema lock-in)

1. **Consolidated doctrine file** — single canonical "decarb engagement doctrine"
   that the skill and the platform prompt both point at, replacing the ~10 rules
   currently duplicated across the platform system prompt, `decarb-plan/SKILL.md`,
   the `utility-split-estimation` skill, and memory. Kills drift. (Also add an
   `AGENTS.md` in soapbox-agent for future skill editors.)
2. **Gate-1 sequencing fix** — no baseline reaches the user until building-model
   provenance is validated (P1.5) and calibration is done. Gate 1 sits *after*
   validation + calibration, never straddling an unvalidated model.
3. **Source-of-truth table at P1** — establish authoritative source per input
   (building count/GFA → ALTA; energy → ESPM; equipment → survey/PCA; factors →
   CRREM) and tag every displayed figure with its provenance tier; enforce the
   existing reconciliation hierarchy (measured > audit > modeled > estimate).
4. **Checkpointed phases** — break the mega-turn (evidence + upload + calibration
   in one ~30-min autonomous turn) into smaller units that each persist state and
   yield, so a dropped connection / deploy restart costs one phase, not the run.
5. **Gate expensive/irreversible actions** — Audette utility upload and write-back
   behind validation + explicit confirmation, never fired mid-turn.
6. **Artifacts only at gates** — stop using rendered HTML as a running scratchpad;
   a polished artifact reads as trustworthy even when provisional/wrong.
7. **Named analyst persona** — give decarb an identity/voice (like Aris for RSRA,
   the retrofit specialist persona). Zero lock-in: a persona is an injected prompt,
   not a server.

## Operational note

Do not push prompt/doctrine changes to the auto-deploying `soapbox-platform` main
branch while a live engagement is running — each deploy restarts the api container
and kills the in-flight turn (observed this session). Batch platform changes; land
them between engagements.

## Related

Verifier + Memory plugins ([[verifier-memory-plugins]]), Retrofit Specialist
([[retrofit-specialist-plugin]]), decarb-plan workflow ([[decarb-plan-workflow]]),
analytics standards ([[feedback-analytics-standards]]), plugin strategy
([[feedback-plugin-strategy]]).
