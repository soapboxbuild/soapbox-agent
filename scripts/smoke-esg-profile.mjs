import { readFileSync, writeFileSync } from 'node:fs'

const html = readFileSync(new URL('../templates/esg-profile/layout-agent.html', import.meta.url), 'utf8')

const DATA_SCRIPT_RE = /<script id="report-data"[^>]*>[\s\S]*?<\/script>/
const inject = (data) => html.replace(DATA_SCRIPT_RE,
  `<script id="report-data" type="application/json">${JSON.stringify(data).replace(/</g, '\\u003c')}</script>`)

const sponsor = JSON.parse(readFileSync(new URL('../skills/esg-profile/demo/example-sponsor.json', import.meta.url)))
const fund = JSON.parse(readFileSync(new URL('../skills/esg-profile/demo/example-fund.json', import.meta.url)))

const a = inject(sponsor)
const b = inject(fund)
writeFileSync('/tmp/esg-sponsor.html', a)
writeFileSync('/tmp/esg-fund.html', b)

function assert(cond, msg) {
  if (!cond) throw new Error('ASSERTION FAILED: ' + msg)
}

function countMatches(str, re) {
  const m = str.match(new RegExp(re, 'g'))
  return m ? m.length : 0
}

// --- Basic injection sanity ---
assert(a !== html, 'sponsor injection did not change the template')
assert(b !== html, 'fund injection did not change the template')
assert(countMatches(a, '<script id="report-data"[^>]*>') === 1, 'sponsor output must have exactly one report-data script block')
assert(countMatches(b, '<script id="report-data"[^>]*>') === 1, 'fund output must have exactly one report-data script block')

// --- Sponsor fixture: sponsor-only content present, fund-only content absent ---
assert(a.includes('"name":"Sponsor Sierra"'), 'sponsor output missing sponsor name from fixture')
assert(a.includes('"investment_overview"'), 'sponsor output missing sponsor-only field investment_overview')
assert(!a.includes('"fund_overview"'), 'sponsor output must not contain fund_overview data (fund pages should be absent)')
assert(!a.includes('"ranking"'), 'sponsor output must not contain fund ranking content')

// --- Fund fixture: fund ranking content present, sponsor-only content absent ---
assert(b.includes('"ranking":['), 'fund output missing fund ranking content from fixture')
assert(b.includes('Sponsor Sierra'), 'fund output missing sponsor names from ranking table')
assert(!b.includes('"investment_overview"'), 'fund output must not contain sponsor-only investment_overview field')
assert(!b.includes('"scorecard"'), 'fund output must not contain sponsor-only scorecard field (sponsor pages should be absent)')

console.log('smoke OK — /tmp/esg-sponsor.html /tmp/esg-fund.html')
