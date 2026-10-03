// NOTICE: This file is protected under RCF-PL

/**
 * Tests for WrtEngineClient's error contract.
 *
 * The regression these guard against is specific: the client used to swallow
 * every failure and hand back a plausible-looking empty result. The editor then
 * treated that as a real answer — `fromEditableHtml` returning "" on every
 * keystroke blanked the open document, and `validate` returning
 * `{ valid: true }` showed "✓ Valid (Native C)" with the backend dead.
 *
 * So the assertions here are as much about what the client must NOT return as
 * about what it must.
 */

import { WrtEngineClient, WrtEngineError } from '@/lib/wrt-engine-client'
import { authedFetch, API_URL } from '@/lib/api'

jest.mock('@/lib/api', () => ({
  API_URL: 'http://engine.test',
  authedFetch: jest.fn(),
}))

const mockFetch = authedFetch as jest.MockedFunction<typeof authedFetch>

/** Build a Response-like object without dragging in a real fetch polyfill. */
const jsonResponse = (body: unknown, init: { status?: number; statusText?: string } = {}) => {
  const { status = 200, statusText = 'OK' } = init
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText,
    json: jest.fn().mockResolvedValue(body),
    headers: new Headers(),
  } as unknown as Response
}

const textResponse = (raw: string, init: { status?: number; statusText?: string } = {}) => {
  const { status = 200, statusText = 'OK' } = init
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText,
    // A body that is not JSON — the client used to mask this as an empty result.
    json: jest.fn().mockRejectedValue(new SyntaxError('Unexpected token < in JSON at position 0')),
    headers: new Headers(),
  } as unknown as Response
}

const client = new WrtEngineClient()

beforeEach(() => {
  mockFetch.mockReset()
})

describe('WrtEngineClient — success paths', () => {
  it('returns the engine validation report', async () => {
    const report = {
      valid: true,
      word_count: 3,
      char_count: 10,
      line_count: 1,
      tag_count: 2,
      issues: [],
    }
    mockFetch.mockResolvedValue(jsonResponse(report))

    await expect(client.validate('[b]привет[/b]')).resolves.toEqual(report)
    expect(mockFetch).toHaveBeenCalledWith(
      `${API_URL}/wrt/validate`,
      expect.objectContaining({ method: 'POST' })
    )
  })

  it('defaults a missing issues array to empty rather than undefined', async () => {
    mockFetch.mockResolvedValue(
      jsonResponse({ valid: true, word_count: 1, char_count: 3, line_count: 1, tag_count: 0 })
    )

    await expect(client.validate('abc')).resolves.toHaveProperty('issues', [])
  })

  it('returns fixed content from fix()', async () => {
    mockFetch.mockResolvedValue(jsonResponse({ content: '[b]fixed[/b]' }))
    await expect(client.fix('[b]fixed')).resolves.toBe('[b]fixed[/b]')
  })

  it('returns HTML from toHtml() and toEditableHtml()', async () => {
    mockFetch.mockResolvedValue(jsonResponse({ html: '<p>hi</p>' }))

    await expect(client.toHtml('[b]hi[/b]')).resolves.toBe('<p>hi</p>')
    mockFetch.mockResolvedValue(jsonResponse({ html: '<p>hi</p>' }))
    await expect(client.toEditableHtml('[b]hi[/b]')).resolves.toBe('<p>hi</p>')
  })

  it('returns serialized WRT from fromEditableHtml()', async () => {
    mockFetch.mockResolvedValue(jsonResponse({ content: '[b]hi[/b]' }))
    await expect(client.fromEditableHtml('<b>hi</b>')).resolves.toBe('[b]hi[/b]')
  })

  it('returns stats from stats()', async () => {
    const stats = { lines: 3, words: 5, chars: 20, tags: 2, valid: true }
    mockFetch.mockResolvedValue(jsonResponse(stats))
    await expect(client.stats('abc')).resolves.toEqual(stats)
  })

  it('returns a file listing from listFiles()', async () => {
    mockFetch.mockResolvedValue(
      jsonResponse({ path: '/workspace', files: [{ name: 'a.wrt', path: '/workspace/a.wrt', is_dir: false, size: 12, mtime: 0, ext: '.wrt' }] })
    )

    await expect(client.listFiles('/workspace')).resolves.toEqual({
      path: '/workspace',
      files: [expect.objectContaining({ name: 'a.wrt' })],
    })
  })

  it('returns an empty array when the engine reports no recent files', async () => {
    mockFetch.mockResolvedValue(jsonResponse({ files: [] }))
    await expect(client.getRecentFiles()).resolves.toEqual([])
  })
})

describe('WrtEngineClient — failure paths never masquerade as results', () => {
  it('throws WrtEngineError when the engine answers !res.ok', async () => {
    mockFetch.mockResolvedValue(jsonResponse({}, { status: 503, statusText: 'Service Unavailable' }))

    await expect(client.validate('anything')).rejects.toBeInstanceOf(WrtEngineError)
    await expect(client.validate('anything')).rejects.toThrow(/503/)
  })

  it('throws when the network is down, preserving the cause', async () => {
    const cause = new TypeError('Failed to fetch')
    mockFetch.mockRejectedValue(cause)

    const err = await client.fromEditableHtml('<p>x</p>').catch((e: unknown) => e)

    expect(err).toBeInstanceOf(WrtEngineError)
    expect((err as WrtEngineError).status).toBeUndefined()
    expect((err as { cause?: unknown }).cause).toBe(cause)
  })

  it('throws on a malformed JSON body instead of treating it as empty', async () => {
    mockFetch.mockResolvedValue(textResponse('<html>502 Bad Gateway</html>'))

    await expect(client.toEditableHtml('[b]x[/b]')).rejects.toBeInstanceOf(WrtEngineError)
    await expect(client.toEditableHtml('[b]x[/b]')).rejects.toThrow(/malformed JSON/i)
  })

  it('throws when a payload is missing the field the caller needs', async () => {
    // 200 OK, but no `content` key. The old code did `data.content ?? ""`.
    mockFetch.mockResolvedValue(jsonResponse({ unexpected: true }))
    await expect(client.fromEditableHtml('<p>x</p>')).rejects.toThrow(/without a 'content' field/)
  })

  it('throws when the engine reports success:false in an HTTP 200 body', async () => {
    mockFetch.mockResolvedValue(jsonResponse({ success: false, error: 'file not found' }))
    await expect(client.fromEditableHtml('<p>x</p>')).rejects.toThrow(/file not found/)
  })

  it('throws when a validation report has no valid field', async () => {
    mockFetch.mockResolvedValue(jsonResponse({ word_count: 1 }))
    await expect(client.validate('a')).rejects.toThrow(/without a 'valid' field/)
  })

  it('throws when listFiles returns no files array', async () => {
    mockFetch.mockResolvedValue(jsonResponse({ path: '/workspace' }))
    await expect(client.listFiles()).rejects.toThrow(/without a 'files' array/)
  })
})

describe('WrtEngineClient — the data-loss regression, stated explicitly', () => {
  it('fromEditableHtml() never resolves to "" when the engine fails', async () => {
    // This is the exact shape that blanked the user's document: every keystroke in
    // Visual Mode triggered a serialization, the engine was unreachable, and ""
    // was written straight into state.
    mockFetch.mockRejectedValue(new TypeError('Failed to fetch'))

    const outcome = await client
      .fromEditableHtml('<p>typed text</p>')
      .then((value) => ({ resolved: true as const, value }))
      .catch(() => ({ resolved: false as const }))

    expect(outcome.resolved).toBe(false)
  })

  it('toEditableHtml() does not fall back to a blank paragraph', async () => {
    // "<p><br></p>" looks like an empty document to the user and invites them to
    // type into something that is about to be overwritten.
    mockFetch.mockRejectedValue(new TypeError('Failed to fetch'))

    const value = await client.toEditableHtml('[b]x[/b]').catch(() => 'THREW')
    expect(value).toBe('THREW')
  })

  it('validate() does not report success when the engine is unreachable', async () => {
    mockFetch.mockRejectedValue(new TypeError('Failed to fetch'))

    const report = await client.validate('[b]x[/b]').catch(() => 'THREW')
    expect(report).toBe('THREW')
  })

  it('fix() does not echo the input back as if it had been fixed', async () => {
    mockFetch.mockRejectedValue(new TypeError('Failed to fetch'))

    const fixed = await client.fix('[b]broken').catch(() => 'THREW')
    expect(fixed).toBe('THREW')
  })

  it('listFiles() does not report an empty workspace when the engine is down', async () => {
    mockFetch.mockRejectedValue(new TypeError('Failed to fetch'))

    const listing = await client.listFiles().catch(() => 'THREW')
    expect(listing).toBe('THREW')
  })
})
describe('WrtEngineClient — importDocument', () => {
  const makeFile = (name: string, bytes = 'PK\u0003\u0004fake') => {
    const blob = new Blob([bytes], { type: 'application/octet-stream' })
    // jsdom's File does not always carry .name off a constructed object.
    Object.defineProperty(blob, 'name', { value: name })
    return blob as File
  }

  it('sends the raw File as the body, not a base64 JSON envelope', async () => {
    const file = makeFile('report.docx')
    mockFetch.mockResolvedValue(
      jsonResponse({ content: '[h1]Отчёт[/h1]', filename: 'report.wrt' })
    )

    await client.importDocument(file)

    const [url, init] = mockFetch.mock.calls[0]
    // A .pptx is tens of megabytes; base64 would inflate it by a third before
    // it even left the browser.
    expect(init?.body).toBe(file)
    expect(String(url)).toContain('filename=report.docx')
    // No JSON content-type: the body is bytes, and declaring JSON would make
    // the backend try to parse the archive.
    expect(init?.headers).toBeUndefined()
  })

  it('url-encodes a filename with spaces and non-ASCII characters', async () => {
    mockFetch.mockResolvedValue(jsonResponse({ content: 'x', filename: 'x.wrt' }))

    await client.importDocument(makeFile('Отчёт за 2026 год.docx'))

    const [url] = mockFetch.mock.calls[0]
    expect(String(url)).toContain('filename=%D0%9E%D1%82%D1%87%D1%91%D1%82')
    expect(String(url)).not.toContain(' ')
  })

  it('returns the converted WRT and the suggested filename', async () => {
    mockFetch.mockResolvedValue(
      jsonResponse({ content: '[h1]Отчёт за год[/h1]', filename: 'report.wrt' })
    )

    const result = await client.importDocument(makeFile('report.docx'))

    expect(result.content).toContain('[h1]Отчёт за год[/h1]')
    expect(result.filename).toBe('report.wrt')
  })

  it('surfaces the backend detail for a corrupt file', async () => {
    // The message is written for the user who dropped the file, so the reason
    // has to survive the trip -- "this file is corrupt" and "this format is
    // unsupported" call for different reactions.
    mockFetch.mockResolvedValue(
      jsonResponse({ detail: 'Could not read broken.docx — the file may be corrupt.' }, { status: 422 })
    )

    await expect(client.importDocument(makeFile('broken.docx'))).rejects.toThrow(/corrupt/)
  })

  it('reports an unsupported format rather than a bare status code', async () => {
    mockFetch.mockResolvedValue(
      jsonResponse({ detail: 'Cannot import .pdf — supported: docx, odt, pptx, md.' }, { status: 415 })
    )

    await expect(client.importDocument(makeFile('scan.pdf'))).rejects.toThrow(/supported/)
  })

  it('throws when the engine is unreachable instead of returning empty content', async () => {
    // Returning "" would replace the open document with nothing.
    mockFetch.mockRejectedValue(new TypeError('Failed to fetch'))

    const result = await client.importDocument(makeFile('report.docx')).catch(() => 'THREW')
    expect(result).toBe('THREW')
  })

  it('throws when a 200 response carries no content field', async () => {
    // A malformed reply must not read as an empty document.
    mockFetch.mockResolvedValue(jsonResponse({ filename: 'report.wrt' }))

    await expect(client.importDocument(makeFile('report.docx'))).rejects.toThrow(/content/)
  })

  it('falls back to a derived filename when the backend omits one', async () => {
    mockFetch.mockResolvedValue(jsonResponse({ content: '[h1]x[/h1]' }))

    const result = await client.importDocument(makeFile('report.docx'))

    expect(result.filename).toBe('report.docx.wrt')
  })
})
