import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import api from '../api/client';
import toast from 'react-hot-toast';

const STATUS_BADGE = { open: 'badge-blue', pending_approval: 'badge-yellow', resolved: 'badge-green', escalated: 'badge-red', closed: 'badge-gray' };
const PRIORITY_BADGE = { P0: 'badge-red', P1: 'badge-yellow', P2: 'badge-blue', P3: 'badge-gray' };

export default function AgentDashboard() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const [tickets, setTickets] = useState([]);
  const [selected, setSelected] = useState(null);
  const [ticketDetail, setTicketDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('escalated');
  const [resolving, setResolving] = useState(false);
  const [resolutionNote, setResolutionNote] = useState('');
  const [agentInput, setAgentInput] = useState('');
  const [sendingMessage, setSendingMessage] = useState(false);

  useEffect(() => {
    loadTickets();
  }, [filter]);

  const loadTickets = async () => {
    setLoading(true);
    try {
      const { data } = await api.get(`/tickets/?status=${filter}`);
      setTickets(data);
    } catch {
      toast.error('Failed to load tickets');
    } finally {
      setLoading(false);
    }
  };

  const loadDetail = async (id) => {
    setSelected(id);
    setResolutionNote('');
    try {
      const { data } = await api.get(`/tickets/${id}`);
      setTicketDetail(data);
    } catch {
      toast.error('Failed to load ticket');
    }
  };

  const handleResolve = async () => {
    if (!ticketDetail || resolving) return;
    setResolving(true);
    try {
      await api.post(`/tickets/${ticketDetail.ticket.id}/resolve`, {
        resolution_note: resolutionNote || null,
      });
      toast.success('Ticket resolved! Customer has been notified.');
      await loadDetail(ticketDetail.ticket.id);
      await loadTickets();
      setResolutionNote('');
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Failed to resolve ticket');
    } finally {
      setResolving(false);
    }
  };

  const handleSendAgentMessage = async () => {
    if (!agentInput.trim() || sendingMessage) return;
    setSendingMessage(true);
    try {
      await api.post('/chat/send', { ticket_id: ticketDetail.ticket.id, content: agentInput });
      await loadDetail(ticketDetail.ticket.id);
      setAgentInput('');
    } catch {
      toast.error('Failed to send message');
    } finally {
      setSendingMessage(false);
    }
  };

  const statuses = ['escalated', 'open', 'pending_approval', 'resolved'];

  return (
    <div className="app-shell">
      {/* Sidebar */}
      <div className="sidebar">
        <div className="sidebar-logo">
          <div className="sidebar-logo-icon">🛸</div>
          <div>
            <div style={{ fontWeight: 800 }}><span className="gradient-text">Orion</span></div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Agent Portal</div>
          </div>
        </div>
        <div className="sidebar-nav">
          <div className="nav-section-label">Filters</div>
          {statuses.map((s) => (
            <button key={s} className={`nav-item ${filter === s ? 'active' : ''}`} onClick={() => setFilter(s)}>
              <span>{s === 'escalated' ? '🚨' : s === 'open' ? '📂' : s === 'pending_approval' ? '⏳' : '✅'}</span>
              {s.replace('_', ' ')}
            </button>
          ))}
          <div className="divider" style={{ margin: '12px 0' }} />
          <button className="nav-item" onClick={() => { logout(); navigate('/login'); }}>
            <span>🚪</span> Sign Out
          </button>
        </div>
        <div style={{ padding: '16px', borderTop: '1px solid var(--border)' }}>
          <div className="flex items-center gap-2">
            <div style={{ width: 32, height: 32, borderRadius: '50%', background: 'var(--purple)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: 14 }}>{user?.name?.[0]}</div>
            <div>
              <div style={{ fontSize: '0.85rem', fontWeight: 600 }}>{user?.name}</div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Support Agent</div>
            </div>
          </div>
        </div>
      </div>

      {/* Main */}
      <div className="main-content">
        <div className="page-header">
          <div>
            <h2>Agent Dashboard</h2>
            <p style={{ fontSize: '0.85rem', marginTop: 2 }}>Handle escalated & complex tickets assigned to you</p>
          </div>
          <button className="btn btn-ghost btn-sm" onClick={loadTickets}>↻ Refresh</button>
        </div>

        <div className="page-body" style={{ display: 'flex', gap: '20px', height: 'calc(100vh - 90px)', overflow: 'hidden' }}>
          {/* Ticket list */}
          <div style={{ width: 340, flexShrink: 0 }}>
            <div className="table-wrapper" style={{ height: '100%', overflowY: 'auto' }}>
              {loading ? (
                <div className="flex items-center justify-center" style={{ padding: 40 }}>
                  <div className="spinner" />
                </div>
              ) : tickets.length === 0 ? (
                <div className="empty-state"><div className="empty-icon">✨</div><p>No {filter} tickets</p></div>
              ) : (
                tickets.map((t) => (
                  <div key={t.id} onClick={() => loadDetail(t.id)} style={{
                    padding: '14px 16px',
                    borderBottom: '1px solid var(--border)',
                    cursor: 'pointer',
                    background: selected === t.id ? 'var(--accent-dim)' : 'transparent',
                    transition: 'background 0.2s',
                    borderLeft: selected === t.id ? '3px solid var(--accent)' : '3px solid transparent',
                  }}>
                    <div style={{ fontWeight: 600, fontSize: '0.875rem', marginBottom: 6 }}>{t.subject}</div>
                    <div className="flex gap-2 flex-wrap">
                      <span className={`badge ${STATUS_BADGE[t.status] || 'badge-gray'}`}>{t.status}</span>
                      <span className={`badge ${PRIORITY_BADGE[t.priority] || 'badge-gray'}`}>{t.priority}</span>
                      {t.intent && <span className="badge badge-cyan">{t.intent}</span>}
                    </div>
                    <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', marginTop: 6 }}>#{t.id} · {new Date(t.created_at).toLocaleDateString()}</div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Ticket detail */}
          <div style={{ flex: 1, overflowY: 'auto' }}>
            {!ticketDetail ? (
              <div className="empty-state" style={{ height: '100%' }}>
                <div className="empty-icon">👈</div>
                <p>Select a ticket to view details</p>
              </div>
            ) : (
              <div className="fade-in" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                {/* Ticket summary card */}
                <div className="card">
                  <div className="flex justify-between items-center" style={{ marginBottom: 16 }}>
                    <h3>#{ticketDetail.ticket.id} — {ticketDetail.ticket.subject}</h3>
                    <div className="flex gap-2">
                      <span className={`badge ${STATUS_BADGE[ticketDetail.ticket.status] || 'badge-gray'}`}>{ticketDetail.ticket.status}</span>
                      <span className={`badge ${PRIORITY_BADGE[ticketDetail.ticket.priority] || 'badge-gray'}`}>{ticketDetail.ticket.priority}</span>
                    </div>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
                    {[
                      { label: 'Intent', value: ticketDetail.ticket.intent || '—' },
                      { label: 'Sentiment', value: ticketDetail.ticket.sentiment_score || '—' },
                      { label: 'Confidence', value: ticketDetail.ticket.confidence_score ? `${Math.round(parseFloat(ticketDetail.ticket.confidence_score) * 100)}%` : '—' },
                    ].map((item) => (
                      <div key={item.label} style={{ background: 'var(--bg-surface)', borderRadius: 'var(--radius)', padding: '12px 14px' }}>
                        <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 4 }}>{item.label}</div>
                        <div style={{ fontWeight: 700, fontSize: '1rem', color: 'var(--text-primary)' }}>{item.value}</div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Briefing doc */}
                {ticketDetail.ticket.summary && (
                  <div className="card" style={{ borderLeft: '3px solid var(--warning)' }}>
                    <div style={{ fontSize: '0.75rem', color: 'var(--warning)', fontWeight: 700, marginBottom: 8, textTransform: 'uppercase', letterSpacing: 1 }}>⚡ Orion Briefing</div>
                    <p style={{ fontSize: '0.875rem', lineHeight: 1.7 }}>{ticketDetail.ticket.summary}</p>
                  </div>
                )}

                {/* Conversation */}
                <div className="card">
                  <h3 style={{ marginBottom: 16 }}>Conversation Thread</h3>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                    {ticketDetail.messages.map((msg, i) => (
                      <div key={i} className={`message-bubble ${msg.is_ai ? 'ai' : 'user'}`} style={{ maxWidth: '90%', alignSelf: msg.is_ai ? 'flex-start' : 'flex-end' }}>
                        {msg.is_ai && (
                          <div style={{ fontSize: '0.72rem', color: msg.metadata?.is_agent_reply ? '#22c55e' : 'var(--accent-bright)', fontWeight: 700, marginBottom: 4 }}>
                            {msg.metadata?.is_agent_reply ? `👨‍💼 ${msg.metadata.sender_name || 'Agent'}` : '🛸 Orion'}
                          </div>
                        )}
                        <div style={{ fontSize: '0.875rem', lineHeight: 1.6 }}>{msg.content}</div>
                        <div className="message-meta">{new Date(msg.created_at).toLocaleString()}</div>
                      </div>
                    ))}
                    {ticketDetail.messages.length === 0 && <p style={{ fontSize: '0.85rem' }}>No messages yet.</p>}
                  </div>
                  
                  {/* Agent Reply Box */}
                  {ticketDetail.ticket.status !== 'resolved' && ticketDetail.ticket.status !== 'closed' && (
                    <div style={{ marginTop: 24, paddingTop: 16, borderTop: '1px solid var(--border)' }}>
                      <div style={{ display: 'flex', gap: 8 }}>
                        <textarea
                          className="input"
                          placeholder="Type a message manually to the customer..."
                          value={agentInput}
                          onChange={(e) => setAgentInput(e.target.value)}
                          onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSendAgentMessage(); } }}
                          rows={2}
                          style={{ flex: 1, resize: 'vertical' }}
                        />
                        <button 
                          className="btn btn-primary" 
                          onClick={handleSendAgentMessage}
                          disabled={!agentInput.trim() || sendingMessage}
                          style={{ alignSelf: 'flex-end' }}
                        >
                          {sendingMessage ? '...' : 'Send'}
                        </button>
                      </div>
                      <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: 6 }}>This message will be instantly sent to the customer without AI processing.</div>
                    </div>
                  )}
                </div>

                {/* Agent Action Panel */}
                {ticketDetail.ticket.status !== 'resolved' && ticketDetail.ticket.status !== 'closed' && (
                  <div className="card" style={{ borderLeft: '3px solid var(--success)', background: 'var(--bg-surface)' }}>
                    <div style={{ fontSize: '0.75rem', color: 'var(--success)', fontWeight: 700, marginBottom: 12, textTransform: 'uppercase', letterSpacing: 1 }}>
                      ✅ Agent Actions
                    </div>
                    <div style={{ marginBottom: 12 }}>
                      <label style={{ fontSize: '0.78rem', color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>
                        Resolution note <span style={{ color: 'var(--text-muted)' }}>(optional — shown to customer)</span>
                      </label>
                      <textarea
                        className="input"
                        placeholder="e.g. Your account has been unlocked. You can now log in normally."
                        value={resolutionNote}
                        onChange={(e) => setResolutionNote(e.target.value)}
                        rows={3}
                        style={{ resize: 'vertical', width: '100%' }}
                      />
                    </div>
                    <div className="flex gap-3">
                      <button
                        className="btn btn-primary"
                        onClick={handleResolve}
                        disabled={resolving}
                        style={{ flex: 1, justifyContent: 'center', background: 'var(--success)', borderColor: 'var(--success)' }}
                      >
                        {resolving ? <><div className="spinner" style={{ width: 14, height: 14, marginRight: 8 }} /> Resolving...</> : '✅ Resolve Ticket'}
                      </button>
                    </div>
                    <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: 8 }}>
                      The customer will receive a real-time notification in their chat when you resolve this ticket.
                    </div>
                  </div>
                )}

                {ticketDetail.ticket.status === 'resolved' && (
                  <div className="card" style={{ borderLeft: '3px solid var(--success)', textAlign: 'center', padding: '20px' }}>
                    <div style={{ fontSize: '1.5rem', marginBottom: 8 }}>✅</div>
                    <div style={{ fontWeight: 700, color: 'var(--success)' }}>Ticket Resolved</div>
                    <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginTop: 4 }}>The customer has been notified.</div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
