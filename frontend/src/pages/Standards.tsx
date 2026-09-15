import { useEffect, useState } from 'react'
import { RulesPayload, getInspectRules } from '../api/inspect'
import './Standards.css'

export function StandardsPage() {
  const [data, setData] = useState<RulesPayload | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    getInspectRules()
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : '加载失败'))
  }, [])

  return (
    <div className="standards-page">
      <header className="page-hero">
        <div>
          <p className="eyebrow">Brand Standard</p>
          <h1>总部统一陈列检查标准</h1>
          <p className="lede">Agent 只对照下列规则判断。证据不足时输出「无法判断」，不推测整店。</p>
        </div>
      </header>

      {error && <p className="error-banner">{error}</p>}

      {data && (
        <>
          <section className="severity-row">
            {Object.entries(data.severity).map(([level, desc]) => (
              <article key={level} className={`sev-card sev-${level}`}>
                <h3>严重度 · {level}</h3>
                <p>{desc}</p>
              </article>
            ))}
          </section>

          <section className="rule-grid">
            {data.rules.map((rule) => (
              <article key={rule.id} className="panel rule-card">
                <p className="eyebrow">{rule.category}</p>
                <h2>{rule.title}</h2>
                <p>{rule.standard}</p>
                <ul>
                  {rule.checks.map((c) => (
                    <li key={c}>{c}</li>
                  ))}
                </ul>
              </article>
            ))}
          </section>
        </>
      )}
    </div>
  )
}
