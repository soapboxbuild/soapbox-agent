// soapbox-agent/demo-staging/build-fixture-from-run.mjs
// Build a demo-replay fixture from an ALREADY-VERIFIED clean run in the DB, instead of
// re-running the agent live. Uses the run's stored artifact.report_data as the render
// payload (guaranteed to reproduce the approved report) and its stored assistant
// narration as the event timeline. Demo-org data only.
//
// Usage:
//   SUPABASE_URL=https://<ref>.supabase.co SUPABASE_SERVICE_ROLE_KEY=<key> \
//   node build-fixture-from-run.mjs --artifact <artifactId> --conversation <convId> \
//        --workflow rsra --target-ms 75000 --out /tmp/rsra.json --scrub-out /tmp/rsra-scrub.txt
import { writeFileSync, mkdirSync } from 'node:fs'
import { dirname } from 'node:path'
import { createClient } from '@supabase/supabase-js'

const args = Object.fromEntries(process.argv.slice(2).reduce((a, v, i, arr) => {
  if (v.startsWith('--')) a.push([v.slice(2), arr[i + 1]]); return a
}, []))

const VALID = ['rsra', 'esg', 'decarb']
if (!VALID.includes(args.workflow)) { console.error(`--workflow must be one of ${VALID.join('|')}`); process.exit(1) }
if (!args.artifact || !args.conversation) { console.error('--artifact and --conversation are required'); process.exit(1) }

const url = process.env.SUPABASE_URL
if (!url) { console.error('SUPABASE_URL must be set'); process.exit(1) }

// Two auth modes:
//  (a) service role key (bypasses RLS) — SUPABASE_SERVICE_ROLE_KEY
//  (b) service-account sign-in (reads via RLS) — SUPABASE_ANON_KEY + SOAPBOX_AGENT_EMAIL/PASSWORD
let sb
const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY
if (serviceKey) {
  sb = createClient(url, serviceKey, { auth: { persistSession: false } })
} else if (process.env.SUPABASE_ANON_KEY) {
  sb = createClient(url, process.env.SUPABASE_ANON_KEY, { auth: { persistSession: false } })
  const { error } = await sb.auth.signInWithPassword({
    email: process.env.SOAPBOX_AGENT_EMAIL, password: process.env.SOAPBOX_AGENT_PASSWORD,
  })
  if (error) { console.error('service-account sign-in failed:', error.message); process.exit(1) }
} else {
  console.error('need SUPABASE_SERVICE_ROLE_KEY, or SUPABASE_ANON_KEY + SOAPBOX_AGENT_EMAIL/PASSWORD'); process.exit(1)
}

// 1. Render payload from the verified artifact.
const { data: art, error: aErr } = await sb.from('artifacts')
  .select('report_data, title').eq('id', args.artifact).single()
if (aErr || !art) { console.error('artifact fetch failed', aErr?.message); process.exit(2) }
const rd = { ...(art.report_data ?? {}) }
const template = rd._template ?? args.workflow
delete rd._template
delete rd._title
const render = { template, title: art.title ?? `${template.toUpperCase()} Report`, data: rd }

// 2. Narration from the run's assistant message(s), in order.
const { data: msgs, error: mErr } = await sb.from('messages')
  .select('role, content, created_at').eq('conversation_id', args.conversation)
  .eq('role', 'assistant').order('created_at', { ascending: true })
if (mErr) { console.error('messages fetch failed', mErr.message); process.exit(2) }
const narration = (msgs ?? [])
  .flatMap((m) => Array.isArray(m.content) ? m.content : [])
  .filter((b) => b?.type === 'text' && b.text)
  .map((b) => b.text).join('\n\n').trim()
if (!narration) { console.error('no assistant narration found for conversation'); process.exit(2) }

// 3. Build the event timeline: model_start, narration streamed in chunks, then the
//    fill_report tool_call marker (the render itself is re-run live by replayDemoFixture).
//    Timestamps are the RECORDED baseline; replayDemoFixture scales them to targetDurationMs.
const CHUNK = 90            // chars per text_delta (sentence-ish cadence)
const MS_PER_CHUNK = 550    // recorded pacing between deltas
const events = [{ t: 0, event: { type: 'model_start' } }]
let t = 300
for (let i = 0; i < narration.length; i += CHUNK) {
  events.push({ t, event: { type: 'text_delta', delta: narration.slice(i, i + CHUNK) } })
  t += MS_PER_CHUNK
}
// The verified run genuinely ended in a fill_report render — keep that marker for realism.
events.push({ t: t + 800, event: { type: 'tool_call', toolName: 'fill_report', input: { template } } })
const recordedTotalMs = events.at(-1).t

const fixture = {
  workflow: args.workflow,
  version: 1,
  targetDurationMs: Number(args['target-ms'] ?? 75000),
  recordedTotalMs,
  events,
  render,
}

const out = args.out ?? `fixtures/${args.workflow}.json`
mkdirSync(dirname(out), { recursive: true })
writeFileSync(out, JSON.stringify(fixture, null, 2))

// 4. Scrub input: all human-visible text (narration + serialized render data) for scrub-check.py.
if (args['scrub-out']) {
  const scrubText = narration + '\n\n' + JSON.stringify(render.data)
  mkdirSync(dirname(args['scrub-out']), { recursive: true })
  writeFileSync(args['scrub-out'], scrubText)
}

console.error(`wrote ${out}: ${events.length} events, recorded ${recordedTotalMs}ms, render template=${template}, data keys=${Object.keys(rd).length}`)
