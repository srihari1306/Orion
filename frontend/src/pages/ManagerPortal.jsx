import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import api from '../api/client';
import toast from 'react-hot-toast';

function DonutChart({ data, size = 180 }) {
  const total = data.reduce((s, d) => s + d.value, 0);
  if (total === 0) return null;
  const cx = size / 2, cy = size / 2, r = size * 0.35;
  const circumference = 2 * Math.PI * r;
  let offset = 0;

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      {data.map((d, i) => {
        const pct = d.value / total;
        const dashLength = pct * circumference;
        const o = offset;
        offset += dashLength;
        return (
          <circle
            key={i}
            cx={cx} cy={cy} r={r}
            fill="none"
            stroke={d.color}
            strokeWidth={size * 0.1}
            strokeDasharray={`${dashLength} ${circumference - dashLength}`}
            strokeDashoffset={-o}
            strokeLinecap="round"
            style={{ transition: 'stroke-dasharray 1s ease, stroke-dashoffset 1s ease' }}
          />
        );
      })}
      <text x={cx} y={cy - 6} textAnchor="middle" fill="var(--text-primary)" fontSize={size * 0.16} fontWeight="800">{total}</text>
      <text x={cx} y={cy + 14} textAnchor="middle" fill="var(--text-muted)" fontSize={size * 0.065} fontWeight="500">TICKETS</text>
    </svg>
  );
}

function DistributionBar({ label, count, total, color, delay = 0 }) {
  const pct = total > 0 ? Math.round((count / total) * 100) : 0;
  return (
    <div style={{ animationDelay: `${delay}ms` }} className="fade-in">
      <div className="flex justify-between" style={{ marginBottom: 6 }}>
        <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', textTransform: 'capitalize' }}>
          {label.replace(/_/g, ' ')}
        </span>
        <span style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>
          {count} <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>({pct}%)</span>
        </span>
      </div>
      <div style={{ background: 'var(--bg-surface)', borderRadius: 99, height: 8, overflow: 'hidden' }}>
        <div
          style={{
            width: `${pct}%`,
            height: '100%',
            background: color || 'linear-gradient(90deg, var(--accent), var(--purple))',
            borderRadius: 99,
            transition: 'width 1.2s cubic-bezier(0.16, 1, 0.3, 1)',
            boxShadow: `0 0 8px ${color || 'var(--accent)'}40`,
          }}
        />
      </div>
    </div>
  );
}

export default function ManagerPortal() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const [approvals, setApprovals] = useState([]);
  const [stats, setStats] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [agentHealth, setAgentHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [reviewing, setReviewing] = useState(null);
  const [reviewNote, setReviewNote] = useState('');
  const [activeTab, setActiveTab] = useState('approvals');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [appRes, statsRes, metricsRes, healthRes] = await Promise.allSettled([
        api.get('/approve/'),
        api.get('/admin/stats'),
        api.get('/metrics/summary'),
        api.get('/metrics/health'),
      ]);
      if (appRes.status === 'fulfilled') setApprovals(appRes.value.data);
      if (statsRes.status === 'fulfilled') setStats(statsRes.value.data);
      if (metricsRes.status === 'fulfilled') setMetrics(metricsRes.value.data);
      if (healthRes.status === 'fulfilled') setAgentHealth(healthRes.value.data);
    } catch {
      toast.error('Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const handleReview = async (id, status) => {
    try {
      await api.post(`/approve/${id}/review`, { status, review_note: reviewNote });
      toast.success(`Request ${status}`);
      setReviewing(null);
      setReviewNote('');
      loadData();
    } catch {
      toast.error('Review failed');
    }
  };

  const statItems = stats ? [
    { label: 'Total Tickets', value: stats.total_tickets, icon: '🎫', color: 'var(--accent)' },
    { label: 'Resolved', value: stats.resolved, icon: '✅', color: 'var(--success)' },
    { label: 'Pending Approval', value: stats.pending_approval, icon: '⏳', color: 'var(--warning)' },
    { label: 'Escalated', value: stats.escalated, icon: '🚨', color: 'var(--danger)' },
    { label: 'Resolution Rate', value: `${stats.resolution_rate}%`, icon: '📈', color: 'var(--purple)' },
    { label: 'Actions Executed', value: stats.total_actions_executed, icon: '⚡', color: 'var(--info)' },
  ] : [];

  const metricsCards = metrics ? [
    { label: 'Auto-Resolved', value: `${metrics.auto_resolution_rate}%`, icon: '🤖', color: 'var(--success)', sub: `${metrics.resolved_count} resolved` },
    { label: 'Escalated', value: `${metrics.escalation_rate}%`, icon: '🔀', color: 'var(--warning)', sub: 'to human agents' },
    { label: 'Pending Approval', value: `${metrics.approval_rate}%`, icon: '🔑', color: 'var(--purple)', sub: 'manager review' },
    { label: 'Avg Resolution', value: `${metrics.avg_resolution_time_minutes}m`, icon: '⏱️', color: 'var(--info)', sub: 'average time' },
    { label: 'Avg Confidence', value: metrics.avg_confidence_score, icon: '🎯', color: 'var(--accent)', sub: 'LLM confidence' },
    { label: 'Fallbacks Used', value: metrics.fallback_triggered_count, icon: '🛡️', color: 'var(--danger)', sub: `${metrics.pipeline_failure_count} failures` },
  ] : [];

  const donutData = metrics?.resolution_path_distribution ? Object.entries(metrics.resolution_path_distribution).map(([k, v]) => ({
    label: k,
    value: v,
    color: {
      auto_resolve: 'var(--success)',
      handoff: 'var(--warning)',
      approval: 'var(--purple)',
      need_info: 'var(--info)',
      unknown: 'var(--text-muted)',
    }[k] || 'var(--accent)',
  })) : [];

  const intentColors = {
    refund_request: '#ef4444',
    wismo: '#3b82f6',
    replacement_request: '#8b5cf6',
    account_issue: '#f59e0b',
    bug_report: '#06b6d4',
    abuse: '#dc2626',
    general_inquiry: '#10b981',
  };

  const pageTitles = {
    approvals: { icon: '⏳', title: 'Approval Queue', sub: 'Review pending actions before execution' },
    stats: { icon: '📊', title: 'KPI Overview', sub: 'Real-time resolution metrics' },
    metrics: { icon: '📈', title: 'Evaluation Dashboard', sub: 'Agent performance analytics & system health' },
  };

  const current = pageTitles[activeTab];

  return (
    <div className="app-shell">
      {/* Sidebar */}
      <div className="sidebar">
        <div className="sidebar-logo">
          <div className="sidebar-logo-icon">🛸</div>
          <div>
            <div style={{ fontWeight: 800 }}><span className="gradient-text">Orion</span></div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Manager Portal</div>
          </div>
        </div>
        <div className="sidebar-nav">
          <div className="nav-section-label">Sections</div>
          {[
            { id: 'approvals', label: 'Approval Queue', icon: '⏳' },
            { id: 'stats', label: 'KPI Overview', icon: '📊' },
            { id: 'metrics', label: 'Evaluation', icon: '📈' },
          ].map((tab) => (
            <button key={tab.id} className={`nav-item ${activeTab === tab.id ? 'active' : ''}`} onClick={() => setActiveTab(tab.id)}>
              <span>{tab.icon}</span> {tab.label}
              {tab.id === 'approvals' && approvals.length > 0 && <span className="nav-count">{approvals.length}</span>}
            </button>
          ))}
          <div className="divider" style={{ margin: '12px 0' }} />
          <button className="nav-item" onClick={() => { logout(); navigate('/login'); }}>
            <span>🚪</span> Sign Out
          </button>
        </div>
        <div style={{ padding: '16px', borderTop: '1px solid var(--border)' }}>
          <div className="flex items-center gap-2">
            <div style={{ width: 32, height: 32, borderRadius: '50%', background: 'var(--warning)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: 14 }}>{user?.name?.[0]}</div>
            <div>
              <div style={{ fontSize: '0.85rem', fontWeight: 600 }}>{user?.name}</div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Manager</div>
            </div>
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className="main-content">
        <div className="page-header">
          <div>
            <h2>{current.icon} {current.title}</h2>
            <p style={{ fontSize: '0.85rem', marginTop: 2 }}>{current.sub}</p>
          </div>
          <div className="flex gap-3 items-center">
            {/* Circuit breaker health indicator */}
            {activeTab === 'metrics' && agentHealth && (
              <div className="flex items-center gap-2" style={{
                padding: '6px 14px',
                borderRadius: 'var(--radius)',
                background: agentHealth.is_open ? 'var(--danger-dim)' : 'var(--success-dim)',
                border: `1px solid ${agentHealth.is_open ? 'rgba(239,68,68,0.3)' : 'rgba(16,185,129,0.3)'}`,
                fontSize: '0.78rem',
                fontWeight: 600,
              }}>
                <span className={`status-dot ${agentHealth.is_open ? 'dot-red' : 'dot-green'}`} />
                <span style={{ color: agentHealth.is_open ? 'var(--danger)' : 'var(--success)' }}>
                  LLM: {agentHealth.circuit_state.toUpperCase()}
                </span>
              </div>
            )}
            <button className="btn btn-ghost btn-sm" onClick={loadData}>↻ Refresh</button>
          </div>
        </div>

        <div className="page-body">
          {loading ? (
            <div className="flex items-center justify-center" style={{ padding: 80 }}>
              <div className="spinner" style={{ width: 32, height: 32 }} />
            </div>

          ) : activeTab === 'approvals' ? (
            <>
              {approvals.length === 0 ? (
                <div className="empty-state">
                  <div className="empty-icon">✅</div>
                  <h3>All clear!</h3>
                  <p>No pending approvals at the moment.</p>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                  {approvals.map((a) => (
                    <div key={a.id} className="card card-glow fade-in">
                      <div className="flex justify-between items-center" style={{ marginBottom: 14 }}>
                        <div>
                          <div style={{ fontWeight: 700, fontSize: '1rem' }}>
                            Ticket #{a.ticket_id} — <span style={{ color: 'var(--warning)', textTransform: 'capitalize' }}>{a.action_type}</span>
                          </div>
                          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 2 }}>
                            Requested {new Date(a.created_at).toLocaleString()}
                          </div>
                        </div>
                        <span className="badge badge-yellow">Pending Review</span>
                      </div>

                      {/* Payload */}
                      {a.payload && (
                        <div style={{ background: 'var(--bg-surface)', borderRadius: 'var(--radius)', padding: '12px 14px', marginBottom: 12, fontFamily: 'var(--font-mono)', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                          {a.payload.amount && <div><span style={{ color: 'var(--success)' }}>amount:</span> ${a.payload.amount}</div>}
                          {a.payload.order_id && <div><span style={{ color: 'var(--accent-bright)' }}>order_id:</span> {a.payload.order_id}</div>}
                          {a.payload.reason && <div><span style={{ color: 'var(--text-muted)' }}>reason:</span> {a.payload.reason}</div>}
                        </div>
                      )}

                      {/* Briefing */}
                      {a.briefing && (
                        <div style={{ background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.2)', borderRadius: 'var(--radius)', padding: '12px 14px', marginBottom: 14 }}>
                          <div style={{ fontSize: '0.7rem', color: 'var(--warning)', fontWeight: 700, marginBottom: 6 }}>📋 ORION BRIEFING</div>
                          <p style={{ fontSize: '0.85rem', lineHeight: 1.7 }}>{a.briefing}</p>
                        </div>
                      )}

                      {reviewing === a.id ? (
                        <div>
                          <label>Review Note (optional)</label>
                          <input className="input" placeholder="Add a note..." value={reviewNote} onChange={(e) => setReviewNote(e.target.value)} style={{ marginBottom: 10 }} />
                          <div className="flex gap-3">
                            <button className="btn btn-danger btn-sm" onClick={() => handleReview(a.id, 'rejected')}>✕ Reject</button>
                            <button className="btn btn-success btn-sm" onClick={() => handleReview(a.id, 'approved')}>✓ Approve & Execute</button>
                            <button className="btn btn-ghost btn-sm" onClick={() => setReviewing(null)}>Cancel</button>
                          </div>
                        </div>
                      ) : (
                        <button className="btn btn-primary btn-sm" onClick={() => setReviewing(a.id)}>Review Action</button>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </>

          ) : activeTab === 'stats' ? (
            <>
              <div className="stat-grid">
                {statItems.map((s) => (
                  <div key={s.label} className="stat-card" style={{ '--accent-color': s.color }}>
                    <div className="stat-icon" style={{ background: `${s.color}20` }}>
                      <span style={{ fontSize: 20 }}>{s.icon}</span>
                    </div>
                    <div className="stat-value">{s.value}</div>
                    <div className="stat-label">{s.label}</div>
                  </div>
                ))}
              </div>

              {stats?.intent_distribution && Object.keys(stats.intent_distribution).length > 0 && (
                <div className="card">
                  <h3 style={{ marginBottom: 16 }}>Intent Distribution</h3>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                    {Object.entries(stats.intent_distribution).map(([intent, count]) => {
                      const pct = Math.round((count / stats.total_tickets) * 100);
                      return (
                        <div key={intent}>
                          <div className="flex justify-between" style={{ marginBottom: 6 }}>
                            <span style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>{intent.replace(/_/g, ' ')}</span>
                            <span style={{ fontSize: '0.875rem', fontWeight: 700, color: 'var(--text-primary)' }}>{count}</span>
                          </div>
                          <div style={{ background: 'var(--bg-surface)', borderRadius: 99, height: 6 }}>
                            <div style={{ width: `${pct}%`, height: '100%', background: 'linear-gradient(90deg, var(--accent), var(--purple))', borderRadius: 99, transition: 'width 1s ease' }} />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </>

          ) : activeTab === 'metrics' ? (
            metrics ? (
              <div className="fade-in">
                {/* KPI Cards */}
                <div className="stat-grid" style={{ marginBottom: 24 }}>
                  {metricsCards.map((m, i) => (
                    <div key={m.label} className="stat-card fade-in" style={{ '--accent-color': m.color, animationDelay: `${i * 60}ms` }}>
                      <div className="stat-icon" style={{ background: `${m.color}20` }}>
                        <span style={{ fontSize: 20 }}>{m.icon}</span>
                      </div>
                      <div className="stat-value">{m.value}</div>
                      <div className="stat-label">{m.label}</div>
                      <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: 4 }}>{m.sub}</div>
                    </div>
                  ))}
                </div>

                {/* Two-column layout: Resolution Paths + Intent Distribution */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 24 }}>

                  {/* Resolution Path Breakdown — Donut */}
                  <div className="card card-glow fade-in" style={{ animationDelay: '200ms' }}>
                    <h3 style={{ marginBottom: 20 }}>
                      <span style={{ marginRight: 8 }}>🔀</span>Resolution Paths
                    </h3>
                    <div className="flex items-center justify-center" style={{ gap: 28 }}>
                      <DonutChart data={donutData} size={180} />
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                        {donutData.map((d) => (
                          <div key={d.label} className="flex items-center gap-2" style={{ fontSize: '0.82rem' }}>
                            <div style={{
                              width: 10, height: 10, borderRadius: 3,
                              background: d.color,
                              boxShadow: `0 0 6px ${d.color}`,
                            }} />
                            <span style={{ color: 'var(--text-secondary)', textTransform: 'capitalize', minWidth: 85 }}>
                              {d.label.replace(/_/g, ' ')}
                            </span>
                            <span style={{ fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' }}>
                              {d.value}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Intent Distribution — Bars */}
                  <div className="card card-glow fade-in" style={{ animationDelay: '300ms' }}>
                    <h3 style={{ marginBottom: 20 }}>
                      <span style={{ marginRight: 8 }}>🏷️</span>Intent Distribution
                    </h3>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                      {metrics.intent_distribution && Object.entries(metrics.intent_distribution)
                        .sort(([, a], [, b]) => b - a)
                        .map(([intent, count], i) => (
                          <DistributionBar
                            key={intent}
                            label={intent}
                            count={count}
                            total={metrics.total_tickets}
                            color={intentColors[intent] || 'var(--accent)'}
                            delay={i * 80}
                          />
                        ))}
                      {(!metrics.intent_distribution || Object.keys(metrics.intent_distribution).length === 0) && (
                        <p style={{ textAlign: 'center', padding: 20, color: 'var(--text-muted)' }}>No intent data yet</p>
                      )}
                    </div>
                  </div>
                </div>

                {/* Priority Distribution + System Health */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>

                  {/* Priority Distribution */}
                  <div className="card card-glow fade-in" style={{ animationDelay: '400ms' }}>
                    <h3 style={{ marginBottom: 20 }}>
                      <span style={{ marginRight: 8 }}>🚦</span>Priority Distribution
                    </h3>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                      {metrics.priority_distribution && ['P0', 'P1', 'P2', 'P3'].map((p, i) => {
                        const count = metrics.priority_distribution[p] || 0;
                        if (count === 0 && !metrics.priority_distribution[p]) return null;
                        const colors = { P0: '#ef4444', P1: '#f59e0b', P2: '#3b82f6', P3: '#10b981' };
                        const labels = { P0: 'Critical', P1: 'High', P2: 'Medium', P3: 'Low' };
                        return (
                          <DistributionBar
                            key={p}
                            label={`${p} — ${labels[p]}`}
                            count={count}
                            total={metrics.total_tickets}
                            color={colors[p]}
                            delay={i * 80}
                          />
                        );
                      })}
                    </div>
                  </div>

                  {/* System Health Panel */}
                  <div className="card card-glow fade-in" style={{ animationDelay: '500ms' }}>
                    <h3 style={{ marginBottom: 20 }}>
                      <span style={{ marginRight: 8 }}>🛡️</span>System Health
                    </h3>

                    {/* Circuit Breaker Status */}
                    {agentHealth && (
                      <div style={{
                        background: agentHealth.is_open ? 'rgba(239,68,68,0.06)' : 'rgba(16,185,129,0.06)',
                        border: `1px solid ${agentHealth.is_open ? 'rgba(239,68,68,0.2)' : 'rgba(16,185,129,0.2)'}`,
                        borderRadius: 'var(--radius)',
                        padding: '16px 18px',
                        marginBottom: 16,
                      }}>
                        <div className="flex justify-between items-center" style={{ marginBottom: 10 }}>
                          <span style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-secondary)' }}>Groq LLM Circuit Breaker</span>
                          <span className={`badge ${agentHealth.is_open ? 'badge-red' : 'badge-green'}`}>
                            {agentHealth.circuit_state}
                          </span>
                        </div>
                        <div className="flex gap-4">
                          <div>
                            <div style={{ fontSize: '1.5rem', fontWeight: 800, color: agentHealth.is_open ? 'var(--danger)' : 'var(--success)' }}>
                              {agentHealth.failure_count}
                            </div>
                            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>failures</div>
                          </div>
                          <div>
                            <div style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--text-primary)' }}>
                              {agentHealth.failure_threshold}
                            </div>
                            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>threshold</div>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Resilience Stats */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                      <div className="flex justify-between items-center" style={{
                        background: 'var(--bg-surface)', borderRadius: 'var(--radius)', padding: '12px 14px',
                      }}>
                        <div className="flex items-center gap-2">
                          <span style={{ fontSize: 16 }}>🛡️</span>
                          <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Fallback Classifiers Used</span>
                        </div>
                        <span style={{ fontWeight: 700, fontFamily: 'var(--font-mono)', color: metrics.fallback_triggered_count > 0 ? 'var(--warning)' : 'var(--success)' }}>
                          {metrics.fallback_triggered_count}
                        </span>
                      </div>
                      <div className="flex justify-between items-center" style={{
                        background: 'var(--bg-surface)', borderRadius: 'var(--radius)', padding: '12px 14px',
                      }}>
                        <div className="flex items-center gap-2">
                          <span style={{ fontSize: 16 }}>💥</span>
                          <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Pipeline Failures</span>
                        </div>
                        <span style={{ fontWeight: 700, fontFamily: 'var(--font-mono)', color: metrics.pipeline_failure_count > 0 ? 'var(--danger)' : 'var(--success)' }}>
                          {metrics.pipeline_failure_count}
                        </span>
                      </div>
                      <div className="flex justify-between items-center" style={{
                        background: 'var(--bg-surface)', borderRadius: 'var(--radius)', padding: '12px 14px',
                      }}>
                        <div className="flex items-center gap-2">
                          <span style={{ fontSize: 16 }}>🎯</span>
                          <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Avg LLM Confidence</span>
                        </div>
                        <span style={{
                          fontWeight: 700,
                          fontFamily: 'var(--font-mono)',
                          color: metrics.avg_confidence_score >= 0.7 ? 'var(--success)' : metrics.avg_confidence_score >= 0.4 ? 'var(--warning)' : 'var(--danger)',
                        }}>
                          {metrics.avg_confidence_score}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="empty-state">
                <div className="empty-icon">📈</div>
                <h3>No metrics available</h3>
                <p>Process some tickets to start generating evaluation data.</p>
              </div>
            )
          ) : null}
        </div>
      </div>
    </div>
  );
}
