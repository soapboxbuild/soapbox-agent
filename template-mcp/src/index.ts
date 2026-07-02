import express from 'express'
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js'
import { StreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/streamableHttp.js'
import { z } from 'zod'

const REPO = 'https://raw.githubusercontent.com/soapboxbuild/soapbox-agent/main'
const KNOWN_TYPES = ['rsra', 'crrem', 'sustainability-passport', 'portfolio-analysis', 'decarb', 'retrofit-advisor'] as const
type ReportType = typeof KNOWN_TYPES[number]

// In-memory cache with 5-minute TTL — re-fetches after template updates without requiring a redeploy
const CACHE_TTL_MS = 5 * 60 * 1000
const templateCache = new Map<ReportType, { html: string; fetchedAt: number }>()

async function fetchTemplate(report_type: ReportType): Promise<string | null> {
  const cached = templateCache.get(report_type)
  if (cached && Date.now() - cached.fetchedAt < CACHE_TTL_MS) return cached.html
  const url = `${REPO}/templates/${report_type}/layout-agent.html`
  const res = await fetch(url, { signal: AbortSignal.timeout(10_000) })
  if (!res.ok) return cached?.html ?? null  // fall back to stale on fetch error
  const html = await res.text()
  templateCache.set(report_type, { html, fetchedAt: Date.now() })
  return html
}

const app = express()
app.use(express.json())

app.get('/health', async (_req, res) => {
  const checks = await Promise.all(
    KNOWN_TYPES.map(async t => {
      const html = await fetchTemplate(t).catch(() => null)
      return { type: t, available: html !== null }
    })
  )
  res.json({ ok: true, service: 'template-mcp', version: '1.2.0', templates: checks })
})

app.post('/mcp', async (req, res) => {
  const server = new McpServer({ name: 'template-mcp', version: '1.2.0' })

  server.tool(
    'get_report_template',
    'Get the HTML report template for a Soapbox report type. Returns a complete HTML document with [[PLACEHOLDER]] markers — substitute each marker with your actual computed values. The template includes all CSS; do not add styles or change class names.',
    {
      report_type: z.enum(KNOWN_TYPES)
        .describe("Report type. Use 'rsra' for Rapid Sustainability Risk Assessment."),
    },
    async ({ report_type }) => {
      const html = await fetchTemplate(report_type)
      if (!html) {
        return {
          content: [{ type: 'text' as const, text: `Template not yet available for report type: ${report_type}` }],
          isError: true,
        }
      }
      return { content: [{ type: 'text' as const, text: html }] }
    }
  )

  const transport = new StreamableHTTPServerTransport({ sessionIdGenerator: undefined })
  res.on('close', () => transport.close())
  await server.connect(transport)
  await transport.handleRequest(req, res, req.body)
})

const PORT = parseInt(process.env.PORT ?? '3000', 10)
app.listen(PORT, () => console.log(`template-mcp v1.2.0 listening on port ${PORT}`))
