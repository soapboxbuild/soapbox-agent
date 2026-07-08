# Decarb Compliance Overlays (CRREM and/or BEPS) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the decarb report show, per the asset's jurisdiction, CRREM and/or the applicable BPS standard(s) — carbon standards on the existing trajectory chart (`bps_target`), EUI standards (WSCBA) in a new compact compliance panel — without a new abstraction or gate change.

**Architecture:** Approach B — extend the existing `targets` shape in the `decarb` template. The carbon chart already draws `bps_target` (stepped) + CRREM with per-line legend toggles; we add display-only label/source fields and one new EUI compliance panel, then update skill guidance so the report is actually populated for the jurisdiction.

**Tech Stack:** JSON Schema, vanilla client-side JS + inline SVG in `layout-agent.html`, Node (render harness), Playwright (render verification), Markdown (skill guidance).

## Global Constraints

- Work in repo `~/soapbox-agent`, branch `feat/decarb-compliance-overlays` (already created; spec committed there).
- **Do NOT modify** `soapbox-platform/apps/api/src/services/verification-gate.ts`. CRREM's `validateComplianceCurve` and `validateFineConsistency` stay exactly as-is.
- **Do NOT touch** `targets.crrem_pathway` / `crrem_meta` / `crrem_stranding_year` behavior — the CRREM path renders exactly as today.
- BPS values are display-only and MUST carry a human `source`/`bps_source` citation — never fabricated. No server re-verification exists for BPS.
- `template-mcp`'s `fill_report` fetches `layout-agent.html` from GitHub raw, so live effect requires merge; **verify locally via the render harness in Task 4**, not by the deployed MCP.
- All new schema objects use `additionalProperties: false`, matching the existing `targets` sub-objects.

---

### Task 1: Schema — add `bps_label`, `bps_source`, `eui_compliance[]`

**Files:**
- Modify: `templates/decarb/schema.json` (the `targets` object, ~lines 227–328)

**Interfaces:**
- Produces: `targets.bps_label: string`, `targets.bps_source: string`, and `targets.eui_compliance: Array<{standard, unit, building_eui, target_eui, compliance_year?, status, source}>` consumed by Tasks 2–4.

- [ ] **Step 1: Add the three properties to `targets.properties`** (alongside `crrem_pathway`, `trajectory`, etc.), keeping `additionalProperties: false`:

```jsonc
"bps_label": {
  "type": "string",
  "description": "Legend/footnote label for the carbon bps_target line, e.g. 'Seattle BEPS (GHGI target)'. Defaults to 'BPS compliance target' when omitted."
},
"bps_source": {
  "type": "string",
  "description": "Provenance citation for the bps_target values (jurisdiction + standard + table/rule + URL). Required whenever any trajectory point sets bps_target. Rendered as a chart footnote; NOT server-verified."
},
"eui_compliance": {
  "type": "array",
  "description": "Energy-based BPS standards (e.g. WA Clean Buildings Act / WSCBA) shown as a compact compliance panel. Omit or empty to hide the panel. Each entry is one standard applicable to the asset's jurisdiction.",
  "items": {
    "type": "object",
    "additionalProperties": false,
    "required": ["standard", "unit", "building_eui", "target_eui", "status", "source"],
    "properties": {
      "standard":        { "type": "string", "description": "Standard name, e.g. 'WA Clean Buildings Act (WSCBA)'." },
      "unit":            { "type": "string", "description": "EUI display unit, e.g. 'kBtu/sf/yr' or 'kWh/m2/yr'. building_eui and target_eui must be in this unit." },
      "building_eui":    { "type": "number", "description": "The building's current/whole-building EUI in `unit`." },
      "target_eui":      { "type": "number", "description": "The standard's EUI target (EUIt) for this property type in `unit`." },
      "compliance_year": { "type": "integer", "description": "First compliance deadline year. Optional." },
      "status":          { "type": "string", "enum": ["compliant", "non-compliant", "exempt"], "description": "Compliance status for this standard." },
      "source":          { "type": "string", "description": "Provenance citation (WAC/rule/table + URL). Required — never fabricate." }
    }
  }
}
```

- [ ] **Step 2: Validate the JSON parses and the keys exist**

Run: `cd ~/soapbox-agent && python3 -c "import json; t=json.load(open('templates/decarb/schema.json'))['properties']['targets']['properties']; assert {'bps_label','bps_source','eui_compliance'} <= set(t), set(t); print('ok', sorted(t))"`
Expected: prints `ok [...]` including the three new keys; no exception.

- [ ] **Step 3: Commit**

```bash
git add templates/decarb/schema.json
git commit -m "feat(decarb-schema): add bps_label, bps_source, eui_compliance[] to targets"
```

---

### Task 2: Carbon chart — label the BPS line + render its source footnote

**Files:**
- Modify: `templates/decarb/layout-agent.html` (series def ~line 966; footnotes block ~lines 1074–1085, inside `drawTrajectory`)

**Interfaces:**
- Consumes: `targets.bps_label`, `targets.bps_source` (Task 1). `tgt` is the `targets` object already in scope inside `drawTrajectory`.

- [ ] **Step 1: Use `bps_label` for the BPS series label.** Replace the `bps_target` series line (currently line ~966):

```js
{ key: 'bps_target',   label: (tgt.bps_label || 'BPS compliance target'), color: '#12253A', dash: '6,4', step: true }
```

- [ ] **Step 2: Render the BPS source as a footnote.** Immediately after the CRREM `crrem_meta` footnote block (the `if (crrem.length > 1 && (meta.country || …)) { … }` ending ~line 1085), add:

```js
if (tgt.bps_source && pts.some(function(p){ return p.bps_target != null; })) {
  notes += '<div class="chart-source">' + esc(tgt.bps_label || 'BPS target') + ' source: ' + esc(tgt.bps_source) + '</div>';
}
```

- [ ] **Step 3: Verify (deferred to Task 4 render harness).** No standalone test — this renders only in a filled report. Marked complete once Task 4's screenshot shows the BPS line labeled with `bps_label` and the source footnote present.

- [ ] **Step 4: Commit**

```bash
git add templates/decarb/layout-agent.html
git commit -m "feat(decarb): label the bps_target line via bps_label + render bps_source footnote"
```

---

### Task 3: EUI compliance panel (new render unit)

**Files:**
- Modify: `templates/decarb/layout-agent.html` — add section markup after `#trajectory-section` (~line 1605), a populate call near the trajectory show-block (~line 939), the `renderEuiCompliance` function, and panel CSS (near the existing `.chart-legend` styles ~lines 361–372).

**Interfaces:**
- Consumes: `targets.eui_compliance` (Task 1). Uses existing helpers `setHtml(id, html)` and `esc(str)` already defined in the file.

- [ ] **Step 1: Add the section markup** after the `#trajectory-section` closing `</div>` (after line 1605):

```html
  <!-- ══════════════════════════════════
       6b. EUI COMPLIANCE (energy-based BPS, e.g. WSCBA)
  ════════════════════════════════════ -->
  <div id="eui-compliance-section" class="section" style="display:none">
    <div class="section-label">Energy Compliance</div>
    <h2 class="section-title">Building Performance Standard — Energy (EUI)</h2>
    <div class="chart-block" id="eui-compliance-block"><!-- JS-rendered --></div>
  </div>
```

- [ ] **Step 2: Add the populate call.** After the trajectory show-block (after line 939, `}` that closes `if (trajSection && traj.length > 1)`), add:

```js
    var euiSection = document.getElementById('eui-compliance-section');
    var euiList = targets.eui_compliance || [];
    if (euiSection && euiList.length) {
      renderEuiCompliance(euiList);
      euiSection.style.display = '';
    }
```

- [ ] **Step 3: Add the `renderEuiCompliance` function** (place it just after `drawTrajectory` ends, inside `populateReport`):

```js
    function renderEuiCompliance(list) {
      var pill = { compliant: ['#065F46','#D1FAE5','Compliant'],
                   exempt:    ['#3730A3','#E0E7FF','Exempt'],
                   'non-compliant': ['#991B1B','#FEE2E2','Non-compliant'] };
      var rows = list.map(function(e){
        var st = pill[e.status] || pill.compliant;
        /* Bar scaled so the target sits at 100%; building marker is building/target. */
        var tgtV = Number(e.target_eui) || 1;
        var pct = Math.max(0, Math.min(100, (Number(e.building_eui) / tgtV) * 100));
        var deadline = e.compliance_year ? ' · by ' + esc(String(e.compliance_year)) : '';
        return ''
          + '<div class="eui-row">'
          +   '<div class="eui-head"><span class="eui-std">' + esc(e.standard) + '</span>'
          +     '<span class="eui-pill" style="color:'+st[0]+';background:'+st[1]+'">' + esc(st[2]) + deadline + '</span></div>'
          +   '<div class="eui-bar"><div class="eui-fill" style="width:'+pct.toFixed(0)+'%"></div>'
          +     '<div class="eui-target" title="Target"></div></div>'
          +   '<div class="eui-nums"><strong>' + esc(String(e.building_eui)) + '</strong> vs target ' + esc(String(e.target_eui)) + ' ' + esc(e.unit) + '</div>'
          +   '<div class="chart-source">' + esc(e.standard) + ' target source: ' + esc(e.source) + '</div>'
          + '</div>';
      }).join('');
      setHtml('eui-compliance-block', '<div class="chart-title">Energy Use Intensity vs. compliance target</div>' + rows);
    }
```

- [ ] **Step 4: Add panel CSS** near the `.chart-legend` block (~line 372):

```css
    .eui-row { margin: 12px 0; }
    .eui-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
    .eui-std { font-weight: 600; font-size: 13px; }
    .eui-pill { font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 9999px; }
    .eui-bar { position: relative; height: 10px; background: #F1F5F9; border-radius: 6px; margin: 6px 0 4px; }
    .eui-fill { position: absolute; left: 0; top: 0; height: 100%; background: #0E7490; border-radius: 6px; }
    .eui-target { position: absolute; left: 100%; top: -3px; width: 2px; height: 16px; background: #12253A; transform: translateX(-1px); }
    .eui-nums { font-size: 12px; color: #334155; }
```

- [ ] **Step 5: Verify (Task 4 harness).** Complete once Task 4's screenshot shows one panel row per `eui_compliance` entry, the marker left of the target line when compliant, the status pill, and the source footnote — and the section is absent when `eui_compliance` is empty.

- [ ] **Step 6: Commit**

```bash
git add templates/decarb/layout-agent.html
git commit -m "feat(decarb): add EUI compliance panel for energy-based BPS (WSCBA)"
```

---

### Task 4: Example data + local render harness + screenshot verification

**Files:**
- Modify: `templates/decarb/example-data.json` (add `bps_target` points, `bps_label`, `bps_source`, `eui_compliance`)
- Create: `scripts/render-decarb-example.mjs`

**Interfaces:**
- Consumes: everything from Tasks 1–3. Mimics `template-mcp` `fill_report`: replaces the `<script id="report-data">…</script>` body with the example JSON.

- [ ] **Step 1: Populate the example.** In `templates/decarb/example-data.json`, under `targets`: add `bps_label`, `bps_source`, an `eui_compliance` entry, and set `bps_target` on the existing `trajectory` points (a stepped line). Example values:

```jsonc
"bps_label": "Seattle BEPS (GHGI target)",
"bps_source": "Seattle OSE Director's Rule — office GHGI targets (verify at seattle.gov/ose)",
"eui_compliance": [
  { "standard": "WA Clean Buildings Act (WSCBA)", "unit": "kBtu/sf/yr",
    "building_eui": 33.5, "target_eui": 60.9, "compliance_year": 2027,
    "status": "compliant", "source": "WAC 194-50-150 — office EUIt" }
]
// and on each trajectory point add a stepped "bps_target": e.g. 15 for years <2031, 8 for 2031-2035, 4 thereafter
```

- [ ] **Step 2: Write the render harness** `scripts/render-decarb-example.mjs`:

```js
import { readFileSync, writeFileSync } from 'node:fs';
const tpl = readFileSync('templates/decarb/layout-agent.html', 'utf8');
const data = readFileSync('templates/decarb/example-data.json', 'utf8');
const out = tpl.replace(
  /(<script id="report-data"[^>]*>)([\s\S]*?)(<\/script>)/,
  (_m, open, _body, close) => open + '\n' + data + '\n' + close
);
if (out === tpl) { console.error('report-data script block not found'); process.exit(1); }
const dest = process.argv[2] || '/tmp/claude-1001/-home-claude/9272867d-cfd6-49ae-9623-363ea156bd7f/scratchpad/decarb-preview.html';
writeFileSync(dest, out);
console.log('wrote', dest);
```

- [ ] **Step 3: Render and verify parses/injects**

Run: `cd ~/soapbox-agent && node scripts/render-decarb-example.mjs`
Expected: `wrote /…/decarb-preview.html` (non-zero exit only on the "not found" error).

- [ ] **Step 4: Screenshot with Playwright and eyeball.** Open the file with the Playwright MCP (`browser_navigate` to `file:///…/decarb-preview.html`, then `browser_take_screenshot`). Confirm: (a) carbon chart shows the BPS line labeled "Seattle BEPS (GHGI target)" + its source footnote; (b) the EUI panel shows WSCBA 33.5 vs 60.9, "Compliant · by 2027", marker left of the target line, source footnote.

- [ ] **Step 5: Verify the panel hides when empty.** Temporarily render with `eui_compliance` removed (e.g. a scratch copy of the JSON) and confirm no EUI section appears. Discard the scratch copy.

- [ ] **Step 6: Commit**

```bash
git add templates/decarb/example-data.json scripts/render-decarb-example.mjs
git commit -m "test(decarb): example fixture + local render harness for BPS line & EUI panel"
```

---

### Task 5: Skill guidance — jurisdiction-auto-include + population rules

**Files:**
- Modify: `skills/decarb-plan/SKILL.md` (and, if it emits the decarb report, the CRREM/RSRA path guidance)

**Interfaces:**
- Consumes: schema fields (Task 1). Documents how the agent fills them from the `bps-compliance` skill.

- [ ] **Step 1: Add a "Compliance overlays (CRREM + BPS)" subsection** to `skills/decarb-plan/SKILL.md` stating:
  - Determine the asset's jurisdiction, then **auto-include** the standards that apply (e.g. Seattle → Seattle BEPS + WSCBA) **plus** CRREM; the user may override ("show only WSCBA", "drop CRREM").
  - **Carbon** standards (Seattle BEPS, Boston BERDO, NYC LL97): populate per-year `targets.trajectory[].bps_target` (stepped) + `targets.bps_label` + `targets.bps_source`. CRREM stays via `targets.crrem_pathway` exactly as today.
  - **Energy** standards (WSCBA): populate `targets.eui_compliance[]` (never `bps_target`).
  - **Values come from the `bps-compliance` skill** reference tables (BERDO/DC BEPS/WSCBA/LL97) + official-portal verification; every entry carries a `source`/`bps_source` citation. **Never fabricate** target values.
  - A standard the asset is exempt from is still included, annotated `status:"exempt"` (that is the useful signal).

- [ ] **Step 2: Verify guidance is self-consistent with the schema.** Re-read the subsection against Task 1 field names; confirm every field it names exists in `schema.json`.

- [ ] **Step 3: Commit**

```bash
git add skills/decarb-plan/SKILL.md
git commit -m "docs(decarb-plan): jurisdiction-auto-include of CRREM + BPS overlays; source-cited BPS values"
```

---

### Task 6: End-to-end verification (acceptance) + branch finish

**Files:** none (verification only)

- [ ] **Step 1: Push the branch** and open a PR draft:

```bash
cd ~/soapbox-agent && git push -u origin feat/decarb-compliance-overlays
```

- [ ] **Step 2: Re-render the real report.** Re-run the decarb report for asset `4th and Madison` (b577e453-8356-4746-8d75-76b7bf93f072) through the normal gated platform path with the updated skill guidance, choosing CRREM + Seattle BEPS + WSCBA. Confirm: carbon chart shows CRREM + Seattle BEPS (annotated exempt) with toggles; EUI panel shows WSCBA 33.5 vs 60.9 compliant. Confirm CRREM gate still passes (unchanged).

- [ ] **Step 3: Confirm no regression** to existing decarb reports: render a CRREM-only example (no `bps_target`, no `eui_compliance`) via the Task 4 harness → chart identical to today, no EUI panel.

- [ ] **Step 4: Summarize** the verified result to the user and hand off the PR for merge.

---

## Self-Review

**Spec coverage:**
- §1 carbon chart (no code) → Tasks 2 (label/source) + 5 (populate). ✓
- §2 EUI panel → Task 3 + fixture Task 4. ✓
- §3 gate unchanged → Global Constraints + Task 6 Step 2 confirms CRREM gate still passes. ✓
- §4 skill wiring / jurisdiction-auto-include / source citations → Task 5. ✓
- §5 testing (no gate tests; render/preview) → Task 4 harness + Task 6 e2e. ✓
- Files-touched list matches Tasks 1–5; `verification-gate.ts` explicitly untouched. ✓

**Placeholder scan:** every code step shows real code; no TBD/TODO. Verification steps that depend on the render harness are explicitly cross-referenced to Task 4 (not vague "add tests"). ✓

**Type/name consistency:** `bps_label`, `bps_source`, `eui_compliance[]` field names identical across Tasks 1–5; `renderEuiCompliance`, `setHtml`, `esc`, `#eui-compliance-section`/`#eui-compliance-block` consistent across Task 3 and 4. Series key `bps_target` matches the existing schema/layout. ✓
