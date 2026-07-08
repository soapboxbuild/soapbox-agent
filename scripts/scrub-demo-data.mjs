import { readFileSync } from 'node:fs'
import { inflateRawSync } from 'node:zlib'

const BANNED = ['Azora','azora','Nestar','Lazora','Esternova','Kepa','Bernaola','Vanessa','López','Lopez','@azora.com','Madrid','Valenciana','Barcelona','León','Leon','Sevilla']
const dir = new URL('../skills/esg-profile/demo/static/', import.meta.url).pathname

// Minimal pure-Node zip reader (no `unzip` binary dependency — not guaranteed present
// in every sandbox/CI image). Reads the central directory, then concatenates the raw
// text of every entry matching *.xml, mirroring `unzip -p <file> '*.xml'`.
function readZipXmlText(path) {
  const buf = readFileSync(path)
  const EOCD_SIG = 0x06054b50
  let eocdOffset = -1
  for (let i = buf.length - 22; i >= 0 && i >= buf.length - 22 - 65535; i--) {
    if (buf.readUInt32LE(i) === EOCD_SIG) { eocdOffset = i; break }
  }
  if (eocdOffset === -1) throw new Error(`${path}: not a valid zip (no EOCD)`)

  const cdEntries = buf.readUInt16LE(eocdOffset + 10)
  const cdOffset = buf.readUInt32LE(eocdOffset + 16)

  let out = ''
  let pos = cdOffset
  const CD_SIG = 0x02014b50
  const LFH_SIG = 0x04034b50
  for (let n = 0; n < cdEntries; n++) {
    if (buf.readUInt32LE(pos) !== CD_SIG) throw new Error(`${path}: malformed central directory`)
    const compressionMethod = buf.readUInt16LE(pos + 10)
    const compressedSize = buf.readUInt32LE(pos + 20)
    const fileNameLength = buf.readUInt16LE(pos + 28)
    const extraFieldLength = buf.readUInt16LE(pos + 30)
    const fileCommentLength = buf.readUInt16LE(pos + 32)
    const localHeaderOffset = buf.readUInt32LE(pos + 42)
    const fileName = buf.toString('utf8', pos + 46, pos + 46 + fileNameLength)

    if (fileName.endsWith('.xml')) {
      if (buf.readUInt32LE(localHeaderOffset) !== LFH_SIG) throw new Error(`${path}: malformed local header for ${fileName}`)
      const lfnLen = buf.readUInt16LE(localHeaderOffset + 26)
      const lefLen = buf.readUInt16LE(localHeaderOffset + 28)
      const dataStart = localHeaderOffset + 30 + lfnLen + lefLen
      const raw = buf.subarray(dataStart, dataStart + compressedSize)
      const data = compressionMethod === 0 ? raw : inflateRawSync(raw)
      out += data.toString('utf8')
    }

    pos += 46 + fileNameLength + extraFieldLength + fileCommentLength
  }
  return out
}

for (const f of ['extract.xlsx', 'notes_scrubbed.docx']) {
  const dump = readZipXmlText(`${dir}${f}`)
  const hit = BANNED.filter(b => dump.includes(b))
  if (hit.length) throw new Error(`${f} still leaks: ${hit.join(', ')}`)
}
console.log('scrub OK — no banned tokens')
