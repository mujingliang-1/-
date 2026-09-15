import { NavLink } from 'react-router-dom'
import type { ReactNode } from 'react'
import './AppLayout.css'

const navItems = [
  { path: '/inspect', icon: '▣', label: '拍照检查' },
  { path: '/history', icon: '▤', label: '检查记录' },
  { path: '/standards', icon: '☰', label: '检查标准' },
]

export default function AppLayout({ children }: { children?: ReactNode }) {
  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="logo">
            <span className="logo-mark">VM</span>
            <span className="logo-text">陈列巡检</span>
          </div>
          <p className="logo-sub">总部统一标准 · 视觉 Agent</p>
        </div>

        <nav className="sidebar-nav">
          <div className="nav-section">
            <span className="nav-section-title">智能巡检</span>
            {navItems.map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
              >
                <span className="nav-icon">{item.icon}</span>
                <span className="nav-label">{item.label}</span>
              </NavLink>
            ))}
          </div>
        </nav>

        <div className="sidebar-footer">
          <div className="sidebar-info">
            <span className="info-text">不确定即「无法判断」，不推测整店</span>
          </div>
        </div>
      </aside>

      <main className="main-content">
        <div className="content-wrapper">{children}</div>
      </main>
    </div>
  )
}
