// soapbox-agent/demo-staging/record-fixture.mjs
// Usage: node record-fixture.mjs --workflow rsra --asset 062cbda3-... --prompt "Run a rapid sustainability risk assessment." --target-ms 75000 --out fixtures/rsra.json
import { writeFileSync } from 'node:fs'
import { createClient } from '@supabase/supabase-js'

const args = Object.fromEntries(process.argv.slice(2).reduce((a, v, i, arr) => {
  if (v.startsWith('--')) a.push([v.slice(2), arr[i + 1]]); return a
}, []))

const DEMO_ORG_ID = '8ebc72a7-dca1-4cb1-be02-eed12f38340f'
const API = process.env.DEMO_API_HOST // e.g. stage app API host
const SB_URL = process.env.SUPABASE_URL
const SB_ANON = process.env.SUPABASE_ANON_KEY

const sb = createClient(SB_URL, SB_ANON)
const { data: auth, error } = await sb.auth.signInWithPassword({
  email: process.env.SOAPBOX_AGENT_EMAIL, password: process.env.SOAPBOX_AGENT_PASSWORD,
})
if (error) { console.error('auth failed', error.message); process.exit(1) }
const token = auth.session.access_token
const H = { Authorization: `Bearer ${token}`, 'x-organization-id': DEMO_ORG_ID, 'Content-Type': 'application/json' }

// 1. New conversation on the demo asset
const convRes = await fetch(`${API}/api/assets/${args.asset}/conversations`, {
  method: 'POST', headers: H, body: JSON.stringify({ title: `fixture-record-${args.workflow}` }),
})
const conv = await convRes.json()
console.error('conversation:', conv.id, '(clean up after)')

// 2. Send the prompt, read the SSE stream
const t0 = Date.now()
const events = []
let render = null
const res = await fetch(`${API}/api/conversations/${conv.id}/messages`, {
  method: 'POST', headers: H, body: JSON.stringify({ content: args.prompt }),
})
const reader = res.body.getReader()
const dec = new TextDecoder()
let buf = ''
for (;;) {
  const { done, value } = await reader.read()
  if (done) break
  buf += dec.decode(value, { stream: true })
  const lines = buf.split('\n'); buf = lines.pop() ?? ''
  for (const line of lines) {
    if (!line.startsWith('data: ')) continue
    let ev; try { ev = JSON.parse(line.slice(6)) } catch { continue }
    if (ev.type === 'ping') continue
    const t = Date.now() - t0
    if (ev.type === 'tool_call' && ev.toolName === 'fill_report') {
      render = { template: ev.input?.template ?? args.workflow, title: ev.input?.title, data: ev.input?.data ?? {} }
      events.push({ t, event: { type: 'tool_call', toolName: 'fill_report', input: { template: render.template } } })
    } else if (ev.type === 'artifact' || ev.type === 'done') {
      // artifact is re-produced by replay; stop capturing at first artifact/done
      break
    } else {
      events.push({ t, event: ev })
    }
  }
  if (render && events.at(-1)?.event?.toolName === 'fill_report') break
}

if (!render) { console.error('no fill_report captured — run did not render'); process.exit(2) }
const recordedTotalMs = events.at(-1).t
const fixture = {
  workflow: args.workflow, version: 1,
  targetDurationMs: Number(args['target-ms'] ?? 75000), recordedTotalMs,
  events, render,
}
const out = args.out ?? `fixtures/${args.workflow}.json`
writeFileSync(out, JSON.stringify(fixture, null, 2))
console.error(`wrote ${out} (${events.length} events, recorded ${recordedTotalMs}ms)`)
