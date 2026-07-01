import express from 'express'
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js'
import { StreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/streamableHttp.js'
import { z } from 'zod'
import { readFileSync, existsSync } from 'fs'
import { join, dirname } from 'path'
import { fileURLToPath } from 'url'

const __dirname = dirname(fileURLToPath(import.meta.url))
// dist/index.js → ../../templates at runtime; src/index.ts → ../../templates in dev
const TEMPLATES_DIR = join(__dirname, '..', '..', 'templates')

const KNOWN_TYPES = ['rsra', 'crrem', 'sustainability-passport', 'retrofit-advisor']

const app = express()
app.use(express.json())

app.get('/health', (_req, res) => {
  const available = KNOWN_TYPES.filter(t =>
    existsSync(join(TEMPLATES_DIR, t, 'layout-agent.html'))
  )
  res.json({ ok: true, service: 'template-mcp', version: '1.0.0', available })
})

app.post('/mcp', async (req, res) => {
  const server = new McpServer({ name: 'template-mcp', version: '1.0.0' })

  server.tool(
    'get_report_template',
    'Get the HTML report template for a Soapbox report type. Returns a complete HTML document with [[PLACEHOLDER]] markers — substitute each marker with your actual computed values. The template includes all CSS; do not add styles or change class names.',
    {
      report_type: z.enum(['rsra', 'crrem', 'sustainability-passport', 'retrofit-advisor'])
        .describe("Report type. Use 'rsra' for Rapid Sustainability Risk Assessment."),
    },
    async ({ report_type }) => {
      const filePath = join(TEMPLATES_DIR, report_type, 'layout-agent.html')
      if (!existsSync(filePath)) {
        return {
          content: [{ type: 'text' as const, text: `Template not yet available for report type: ${report_type}` }],
          isError: true,
        }
      }
      const html = readFileSync(filePath, 'utf-8')
      return { content: [{ type: 'text' as const, text: html }] }
    }
  )

  const transport = new StreamableHTTPServerTransport({ sessionIdGenerator: undefined })
  res.on('close', () => transport.close())
  await server.connect(transport)
  await transport.handleRequest(req, res, req.body)
})

const PORT = parseInt(process.env.PORT ?? '3000', 10)
app.listen(PORT, () => console.log(`template-mcp listening on port ${PORT}`))
