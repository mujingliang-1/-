import { useCallback, useEffect, useMemo, useRef, useState, type DragEvent } from 'react'
import {
  Finding,
  InspectionReport,
  getInspectStatus,
  runInspection,
} from '../api/inspect'
import './Inspect.css'

const STEPS = ['照片有效性预检', '视觉识别陈列', '对照总部标准', '生成整改建议']

function statusClass(value: string) {
  if (value === '合规') return 'ok'
  if (value === '不合规') return 'bad'
  return 'unsure'
}

function FindingCard({ item }: { item: Finding }) {
  return (
    <article className={`finding-card status-${statusClass(item.compliant)}`}>
      <header>
        <h3>{item.category}</h3>
        <div className="finding-tags">
          <span className={`pill ${statusClass(item.compliant)}`}>{item.compliant}</span>
          <span className={`pill sev-${item.severity}`}>{item.severity}</span>
        </div>
      </header>
      <dl>
        <div>
          <dt>具体问题</dt>
          <dd>{item.issue}</dd>
        </div>
        <div>
          <dt>对应检查标准</dt>
          <dd>{item.standard}</dd>
        </div>
        <div>
          <dt>问题所在区域</dt>
          <dd>{item.region}</dd>
        </div>
        <div>
          <dt>整改建议</dt>
          <dd>{item.suggestion}</dd>
        </div>
      </dl>
    </article>
  )
}

export function InspectPage() {
  const [files, setFiles] = useState<File[]>([])
  const [previews, setPreviews] = useState<string[]>([])
  const [storeId, setStoreId] = useState('')
  const [storeName, setStoreName] = useState('')
  const [note, setNote] = useState('')
  const [loading, setLoading] = useState(false)
  const [step, setStep] = useState(0)
  const [error, setError] = useState('')
  const [report, setReport] = useState<InspectionReport | null>(null)
  const [configured, setConfigured] = useState<boolean | null>(null)
  const [model, setModel] = useState('')
  const [dragOver, setDragOver] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    getInspectStatus()
      .then((s) => {
        setConfigured(s.llm_configured)
        setModel(s.model)
      })
      .catch(() => setConfigured(false))
  }, [])

  useEffect(() => {
    const urls = files.map((f) => URL.createObjectURL(f))
    setPreviews(urls)
    return () => urls.forEach((u) => URL.revokeObjectURL(u))
  }, [files])

  useEffect(() => {
    if (!loading) return
    setStep(0)
    const timer = window.setInterval(() => {
      setStep((s) => (s < STEPS.length - 1 ? s + 1 : s))
    }, 2200)
    return () => window.clearInterval(timer)
  }, [loading])

  const addFiles = useCallback((list: FileList | File[]) => {
    const incoming = Array.from(list).filter((f) => f.type.startsWith('image/'))
    setFiles((prev) => {
      const merged = [...prev]
      incoming.forEach((file) => {
        if (merged.length < 8 && !merged.some((p) => p.name === file.name && p.size === file.size)) {
          merged.push(file)
        }
      })
      return merged
    })
    setError('')
    setReport(null)
  }, [])

  const onDrop = (e: DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    if (e.dataTransfer.files?.length) addFiles(e.dataTransfer.files)
  }

  const overallClass = useMemo(
    () => (report ? statusClass(report.overall) : ''),
    [report],
  )

  async function onSubmit() {
    if (!files.length) {
      setError('请先上传门店陈列照片')
      return
    }
    setLoading(true)
    setError('')
    setReport(null)
    try {
      const result = await runInspection({ files, storeId, storeName, note })
      setReport(result)
      setStep(STEPS.length - 1)
    } catch (e) {
      setError(e instanceof Error ? e.message : '检查失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="inspect-page">
      <header className="page-hero">
        <div>
          <p className="eyebrow">Visual Merchandising Agent</p>
          <h1>上传门店照片，自动对照总部陈列标准</h1>
          <p className="lede">
            检查挂装、叠装、模特、鞋包配件、价签与清洁安全。照片模糊、过暗、遮挡或局部未入镜时，相关项明确输出「无法判断」。
          </p>
        </div>
        <div className={`config-chip ${configured ? 'on' : configured === false ? 'off' : ''}`}>
          {configured ? `模型已就绪 · ${model}` : configured === false ? '未检测到 DeepSeek 密钥' : '正在连接服务…'}
        </div>
      </header>

      <section className="inspect-grid">
        <div className="panel">
          <div
            className={`dropzone ${dragOver ? 'over' : ''}`}
            onDragOver={(e) => {
              e.preventDefault()
              setDragOver(true)
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={onDrop}
            onClick={() => inputRef.current?.click()}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') inputRef.current?.click()
            }}
          >
            <strong>拖拽照片到此处，或点击选择</strong>
            <span>支持 JPG / PNG / WebP，最多 8 张。建议正对货架、补光后拍摄。</span>
            <input
              ref={inputRef}
              type="file"
              accept="image/jpeg,image/png,image/webp,image/gif"
              multiple
              hidden
              onChange={(e) => e.target.files && addFiles(e.target.files)}
            />
          </div>

          {previews.length > 0 && (
            <ul className="preview-row">
              {previews.map((src, i) => (
                <li key={src}>
                  <img src={src} alt={files[i]?.name || `照片 ${i + 1}`} />
                  <button
                    type="button"
                    className="remove"
                    onClick={() => setFiles((prev) => prev.filter((_, idx) => idx !== i))}
                  >
                    移除
                  </button>
                </li>
              ))}
            </ul>
          )}

          <div className="meta-grid">
            <label>
              门店编号
              <input value={storeId} onChange={(e) => setStoreId(e.target.value)} placeholder="如 SH-012" />
            </label>
            <label>
              门店名称
              <input value={storeName} onChange={(e) => setStoreName(e.target.value)} placeholder="如 南京东路店" />
            </label>
            <label className="span-2">
              备注（选填）
              <input value={note} onChange={(e) => setNote(e.target.value)} placeholder="拍摄位置、楼层或督导说明" />
            </label>
          </div>

          <div className="actions">
            <button type="button" className="primary" disabled={loading || !files.length} onClick={onSubmit}>
              {loading ? '正在检查…' : '开始检查'}
            </button>
            <button
              type="button"
              className="ghost"
              disabled={loading}
              onClick={() => {
                setFiles([])
                setReport(null)
                setError('')
              }}
            >
              清空
            </button>
          </div>

          {error && <p className="error-banner">{error}</p>}
        </div>

        <aside className="panel side-hint">
          <h2>检查时会看什么</h2>
          <ol>
            <li>照片是否清晰、完整、可检</li>
            <li>挂装方向、间距、色序、空挂</li>
            <li>叠装对齐、件数 3–6、是否落地</li>
            <li>模特完整性、吊牌、底座</li>
            <li>鞋包成双、对齐、遮挡价签</li>
            <li>价签有无、朝向；文字看不清则「内容无法判断」</li>
            <li>杂物、消防疏散、货架是否松脱</li>
          </ol>
          <p className="muted">严重度：高=安全/落地；中=可售性与整洁；低=对齐与一致性。</p>
        </aside>
      </section>

      {loading && (
        <section className="panel progress-panel">
          <h2>Agent 正在巡检</h2>
          <ul className="steps">
            {STEPS.map((label, i) => (
              <li key={label} className={i <= step ? 'active' : ''}>
                <span>{i + 1}</span>
                {label}
              </li>
            ))}
          </ul>
        </section>
      )}

      {report && (
        <section className="result-block">
          <div className={`overall-banner ${overallClass}`}>
            <div>
              <p className="eyebrow">检查结论</p>
              <h2>
                {report.overall}
                {report.store_name ? ` · ${report.store_name}` : ''}
              </h2>
              <p>{report.summary}</p>
            </div>
            <ul className="overall-meta">
              <li>单号 {report.inspection_id}</li>
              <li>{report.created_at}</li>
              <li>{report.image_count} 张照片</li>
            </ul>
          </div>

          {report.uncertain && (
            <p className="unsure-callout">存在无法确定的项目，已按规则标记为「无法判断」，未对未入镜区域做整店推测。</p>
          )}

          <div className="finding-list">
            {report.findings.map((item) => (
              <FindingCard key={item.category} item={item} />
            ))}
          </div>
        </section>
      )}
    </div>
  )
}
