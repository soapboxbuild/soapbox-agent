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
  res.json({ ok: true, service: 'template-mcp', version: '1.3.0', templates: checks })
})

app.post('/mcp', async (req, res) => {
  const server = new McpServer({ name: 'template-mcp', version: '1.3.0' })

  server.tool(
    'fill_report',
    'Render a Soapbox report by injecting your computed JSON data into the official template. Returns complete HTML ready to display as an artifact. Do NOT write your own HTML — always use this tool.',
    {
      report_type: z.enum(KNOWN_TYPES)
        .describe("Report type. Use 'rsra' for Rapid Sustainability Risk Assessment."),
      data: z.record(z.unknown())
        .describe('Computed report data object. Injected into the template <script id="report-data"> block.'),
    },
    async ({ report_type, data }) => {
      const html = await fetchTemplate(report_type)
      if (!html) {
        return {
          content: [{ type: 'text' as const, text: `Template not yet available for report type: ${report_type}` }],
          isError: true,
        }
      }
      const json = JSON.stringify(data)
      const rendered = html.replace(
        /<script id="report-data"[^>]*>[\s\S]*?<\/script>/,
        `<script id="report-data" type="application/json">${json}</script>`
      )
      return { content: [{ type: 'text' as const, text: rendered }] }
    }
  )

  server.tool(
    'get_report_template',
    'Get the raw HTML report template with the <script id="report-data"> placeholder. Prefer fill_report instead — use this only if you need to inspect the template structure.',
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
