export interface ParsedUserAgent {
  osName: string
  browserName: string
  browserVersion: string
  platform: string
}

export interface DeviceFingerprint {
  deviceId: string
  osName: string
  browserName: string
  browserVersion: string
  platform: string
  deviceLabel: string
  headers: Record<string, string>
}

interface DeviceFingerprintOptions {
  deviceIdKey?: string
  deviceIdPrefix?: string
}

const GENERIC_DEVICE_NAMES = new Set([
  '',
  'web',
  'desktop',
  'android',
  'ios',
  'unknown',
  'current-browser',
  'browser'
])

function extractVersion(userAgent: string, patterns: RegExp[]): string {
  for (const pattern of patterns) {
    const match = userAgent.match(pattern)
    if (match?.[1]) return match[1]
  }
  return ''
}

function detectOsName(userAgent: string): string {
  const ua = userAgent.toLowerCase()
  if (ua.includes('windows nt') || ua.includes('windows')) return 'Windows'
  if (ua.includes('iphone') || ua.includes('ipad') || ua.includes('ipod') || ua.includes('ios')) return 'iOS'
  if (ua.includes('android')) return 'Android'
  if (ua.includes('macintosh') || ua.includes('mac os x')) return 'macOS'
  if (ua.includes('cros')) return 'ChromeOS'
  if (ua.includes('linux')) return 'Linux'
  return 'Unknown OS'
}

function detectBrowserNameAndVersion(userAgent: string): { browserName: string; browserVersion: string } {
  const ua = userAgent.toLowerCase()

  if (ua.includes('edg/') || ua.includes('edge/') || ua.includes('edga/') || ua.includes('edgios/')) {
    return { browserName: 'Edge', browserVersion: extractVersion(userAgent, [/(?:Edg|Edge|EdgA|EdgiOS)\/([\d.]+)/i]) }
  }
  if (ua.includes('opr/') || ua.includes('opera')) {
    return { browserName: 'Opera', browserVersion: extractVersion(userAgent, [/(?:OPR|Opera)\/([\d.]+)/i]) }
  }
  if (ua.includes('samsungbrowser/')) {
    return { browserName: 'Samsung Internet', browserVersion: extractVersion(userAgent, [/SamsungBrowser\/([\d.]+)/i]) }
  }
  if (ua.includes('firefox/') || ua.includes('fxios/')) {
    return { browserName: 'Firefox', browserVersion: extractVersion(userAgent, [/(?:Firefox|FxiOS)\/([\d.]+)/i]) }
  }
  if (ua.includes('micromessenger/')) {
    return { browserName: 'WeChat', browserVersion: extractVersion(userAgent, [/MicroMessenger\/([\d.]+)/i]) }
  }
  if (ua.includes('ucbrowser/')) {
    return { browserName: 'UC Browser', browserVersion: extractVersion(userAgent, [/UCBrowser\/([\d.]+)/i]) }
  }
  if (ua.includes('qqbrowser/')) {
    return { browserName: 'QQ Browser', browserVersion: extractVersion(userAgent, [/QQBrowser\/([\d.]+)/i]) }
  }
  if (ua.includes('msie ') || ua.includes('trident/')) {
    return { browserName: 'Internet Explorer', browserVersion: extractVersion(userAgent, [/MSIE\s([\d.]+)/i, /rv:([\d.]+)/i]) }
  }
  if (ua.includes('safari/') && !ua.includes('chrome/') && !ua.includes('crios/')) {
    return { browserName: 'Safari', browserVersion: extractVersion(userAgent, [/Version\/([\d.]+)/i]) }
  }
  if (ua.includes('chrome/') || ua.includes('crios/')) {
    return { browserName: 'Chrome', browserVersion: extractVersion(userAgent, [/(?:Chrome|CriOS)\/([\d.]+)/i]) }
  }

  return { browserName: 'Unknown Browser', browserVersion: '' }
}

function inferPlatformFromOs(osName: string): string {
  if (osName === 'iOS') return 'ios'
  if (osName === 'Android') return 'android'
  if (['Windows', 'macOS', 'Linux', 'ChromeOS'].includes(osName)) return 'desktop'
  return 'web'
}

export function parseUserAgent(userAgent?: string): ParsedUserAgent {
  const ua = String(userAgent || '')
  const osName = detectOsName(ua)
  const { browserName, browserVersion } = detectBrowserNameAndVersion(ua)
  return {
    osName,
    browserName,
    browserVersion,
    platform: inferPlatformFromOs(osName)
  }
}

export function buildDeviceLabel(osName?: string, browserName?: string): string {
  const safeOs = String(osName || '').trim() || 'Unknown OS'
  const safeBrowser = String(browserName || '').trim() || 'Unknown Browser'
  return `${safeOs} · ${safeBrowser}`
}

export function isGenericDeviceName(value?: string): boolean {
  const raw = String(value || '').trim()
  const lowered = raw.toLowerCase()
  if (GENERIC_DEVICE_NAMES.has(lowered)) return true
  if (/^(desktop|web|android|ios|unknown)\s*[·-]\s*[a-z]{2}(?:-[a-z]{2})?$/.test(lowered)) return true
  return lowered.endsWith(' browser')
}

export function normalizeDeviceName(value: string | undefined, parsed: ParsedUserAgent): string {
  const raw = String(value || '').trim()
  if (raw && !isGenericDeviceName(raw)) return raw
  return buildDeviceLabel(parsed.osName, parsed.browserName)
}

function ensureDeviceId(key: string, prefix: string): string {
  if (!import.meta.client) return ''
  let value = localStorage.getItem(key) || ''
  if (!value) {
    const randomPart = Math.random().toString(36).slice(2, 10)
    value = typeof crypto !== 'undefined' && 'randomUUID' in crypto
      ? crypto.randomUUID()
      : `${prefix}-${Date.now()}-${randomPart}`
    localStorage.setItem(key, value)
  }
  return value
}

export function getClientDeviceFingerprint(options?: DeviceFingerprintOptions): DeviceFingerprint {
  const deviceIdKey = options?.deviceIdKey || 'tg_device_id'
  const deviceIdPrefix = options?.deviceIdPrefix || 'dev'
  const userAgent = import.meta.client ? (navigator.userAgent || '') : ''
  const parsed = parseUserAgent(userAgent)
  const deviceId = ensureDeviceId(deviceIdKey, deviceIdPrefix)
  const deviceLabel = buildDeviceLabel(parsed.osName, parsed.browserName)
  const headers: Record<string, string> = {}
  if (deviceId) headers['X-Device-Id'] = deviceId
  if (parsed.platform) headers['X-Platform'] = parsed.platform
  if (deviceLabel) headers['X-Device-Name'] = deviceLabel.slice(0, 120)

  return {
    deviceId,
    osName: parsed.osName,
    browserName: parsed.browserName,
    browserVersion: parsed.browserVersion,
    platform: parsed.platform,
    deviceLabel,
    headers
  }
}

export function parseUserAgentToLabel(userAgent?: string): string {
  const parsed = parseUserAgent(userAgent)
  return buildDeviceLabel(parsed.osName, parsed.browserName)
}
