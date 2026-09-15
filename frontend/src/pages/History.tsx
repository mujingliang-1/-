import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import {
  HistoryItem,
  InspectionReport,
  getInspectHistory,
  getInspection,
  inspectionImageUrl,
} from '../api/inspect'
import './History.css'

function badgeClass(overall: string) {
  if (overall === '合规') return 'ok'
  if (overall === '不合规') return 'bad'
  return 'unsure'
}

export function HistoryPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [items, setItems] = useState<HistoryItem[]>([])
  const [detail, setDetail] = useState<InspectionReport | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    getInspectHistory()
      .then(setItems)
      .catch((e) => setError(e instanceof Error ? e.message : '加载失败'))
  }, [])

  useEffect(() => {
    if (!id) {
      setDetail(null)
      return
    }
    getInspection(id)
      .then(setDetail)
      .catch((e) => setError(e instanceof Error ? e.message : '记录不存在'))
  }, [id])

  return (
    <div className="history-page">
      <header className="page-hero">
        <div>
          <p className="eyebrow">Inspection Log</p>
          <h1>历史检查记录</h1>
          <p className="lede">可回看每次上传的照片与 Agent 结论，便于督导复核。</p>
        </div>
      </header>

      {error && <p className="error-banner">{error}</p>}

      {detail && (
        <section className="panel detail-panel">
          <div className={`overall-mini ${badgeClass(detail.overall)}`}>
            <strong>{detail.overall}</strong>
            <span>{detail.store_name || detail.store_id || '未填写门店'} · {detail.created_at}</span>
          </div>
          <p>{detail.summary}</p>
          <div className="history-thumbs">
            {Array.from({ length: detail.image_count }).map((_, i) => (
              <img key={i} src={inspectionImageUrl(detail.inspection_id, i)} alt={`照片 ${i + 1}`} />
            ))}
          </div>
          <table className="findings-table">
            <thead>
              <tr>
                <th>类别</th>
                <th>是否合规</th>
                <th>具体问题</th>
                <th>标准</th>
                <th>区域</th>
                <th>严重度</th>
                <th>整改建议</th>
              </tr>
            </thead>
            <tbody>
              {detail.findings.map((f) => (
                <tr key={f.category}>
                  <td>{f.category}</td>
                  <td>{f.compliant}</td>
                  <td>{f.issue}</td>
                  <td>{f.standard}</td>
                  <td>{f.region}</td>
                  <td>{f.severity}</td>
                  <td>{f.suggestion}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      <ul className="history-list">
        {items.length === 0 && <li className="empty">暂无记录。请先在「拍照检查」上传照片。</li>}
        {items.map((item) => (
          <li key={item.id}>
            <button type="button" className={item.id === id ? 'active' : ''} onClick={() => navigate(`/history/${item.id}`)}>
              <img src={inspectionImageUrl(item.id, 0)} alt="" />
              <div>
                <strong>
                  {item.store_name || item.store_id || '未填写门店'}
                  <span className={`pill ${badgeClass(item.overall)}`}>{item.overall}</span>
                </strong>
                <p>{item.summary}</p>
                <small>
                  {item.created_at} · {item.image_count} 张 · {item.id}
                </small>
              </div>
            </button>
          </li>
        ))}
      </ul>

      <p className="muted">
        <Link to="/inspect">返回拍照检查</Link>
      </p>
    </div>
  )
}
