export interface PhotoQuality {
  filename: string
  width: number
  height: number
  mean_brightness: number
  edge_strength: number
  too_dark: boolean
  too_bright: boolean
  blurry: boolean
  issues: string[]
  notes: string
}

export interface Finding {
  category: string
  compliant: '合规' | '不合规' | '无法判断'
  issue: string
  standard: string
  region: string
  severity: '高' | '中' | '低' | '无法判断'
  suggestion: string
  visible_in_photo: boolean
}

export interface InspectionReport {
  inspection_id: string
  store_id: string
  store_name: string
  created_at: string
  overall: '合规' | '不合规' | '无法判断'
  summary: string
  photo_quality: PhotoQuality[]
  findings: Finding[]
  image_count: number
  model: string
  uncertain: boolean
}

export interface InspectStatus {
  llm_configured: boolean
  model: string
  max_images: number
}

export interface RuleItem {
  id: string
  category: string
  title: string
  standard: string
  severity_hint: string
  checks: string[]
}

export interface RulesPayload {
  categories: string[]
  severity: Record<string, string>
  rules: RuleItem[]
}

export interface HistoryItem {
  id: string
  store_id: string
  store_name: string
  created_at: string
  overall: string
  summary: string
  image_count: number
}

const API = ''

async function readError(res: Response): Promise<string> {
  try {
    const data = await res.json()
    if (typeof data?.detail === 'string') return data.detail
    if (Array.isArray(data?.detail)) {
      return data.detail.map((d: { msg?: string }) => d.msg || JSON.stringify(d)).join('；')
    }
    return JSON.stringify(data)
  } catch {
    return res.statusText || '请求失败'
  }
}

export async function getInspectStatus(): Promise<InspectStatus> {
  const res = await fetch(`${API}/api/inspect/status`)
  if (!res.ok) throw new Error(await readError(res))
  return res.json()
}

export async function getInspectRules(): Promise<RulesPayload> {
  const res = await fetch(`${API}/api/inspect/rules`)
  if (!res.ok) throw new Error(await readError(res))
  return res.json()
}

export async function runInspection(params: {
  files: File[]
  storeId?: string
  storeName?: string
  note?: string
}): Promise<InspectionReport> {
  const form = new FormData()
  params.files.forEach((file) => form.append('files', file))
  form.append('store_id', params.storeId || '')
  form.append('store_name', params.storeName || '')
  form.append('note', params.note || '')
  const res = await fetch(`${API}/api/inspect`, { method: 'POST', body: form })
  if (!res.ok) throw new Error(await readError(res))
  return res.json()
}

export async function getInspectHistory(): Promise<HistoryItem[]> {
  const res = await fetch(`${API}/api/inspect/history`)
  if (!res.ok) throw new Error(await readError(res))
  const data = await res.json()
  return data.items || []
}

export async function getInspection(id: string): Promise<InspectionReport> {
  const res = await fetch(`${API}/api/inspect/${id}`)
  if (!res.ok) throw new Error(await readError(res))
  return res.json()
}

export function inspectionImageUrl(id: string, index: number) {
  return `${API}/api/inspect/${id}/image/${index}`
}
