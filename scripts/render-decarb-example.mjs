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
