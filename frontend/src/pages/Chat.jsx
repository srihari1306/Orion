import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { io } from 'socket.io-client';
import { useAuthStore } from '../store/authStore';
import { useTicketStore } from '../store/ticketStore';
import toast from 'react-hot-toast';

const STATUS_BADGE = {
  open: 'badge-blue',
  pending_approval: 'badge-yellow',
  resolved: 'badge-green',
  closed: 'badge-gray',
  escalated: 'badge-red',
};

const PATH_BADGE = {
  auto_resolve: 'badge-green',
  approval: 'badge-yellow',
  handoff: 'badge-red',
  need_info: 'badge-cyan',
};

function formatTime(ts) {
  return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function formatDate(ts) {
  if (!ts) return '—';
  return new Date(ts).toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' });
}

export default function Chat() {
  const { user, logout } = useAuthStore();
  const { tickets, activeTicket, messages, orders, fetchTickets, fetchTicket, fetchOrders, createTicket, sendMessage, addMessage, updateTicketStatus } = useTicketStore();
  const navigate = useNavigate();
  const [input, setInput] = useState('');
  const [thinking, setThinking] = useState(null);
  const [sending, setSending] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [newSubject, setNewSubject] = useState('');
  const [selectedOrderId, setSelectedOrderId] = useState('');
  const messagesEndRef = useRef(null);
  const socketRef = useRef(null);

  useEffect(() => {
    fetchTickets();
    fetchOrders();

    socketRef.current = io('http://localhost:8000', { transports: ['websocket', 'polling'] });
    socketRef.current.on('agent_thinking', (data) => setThinking(data.message));
    socketRef.current.on('ticket_update', (data) => {
      setThinking(null);
      updateTicketStatus(data.ticket_id, data.status, data.resolution_path);
      if (data.reply) {
        addMessage({
          id: Date.now(),
          content: data.reply,
          is_ai: true,
          sender_id: null,
          created_at: new Date().toISOString(),
          metadata: { resolution_path: data.resolution_path, steps_taken: data.steps_taken },
        });
      }
      if (activeTicket?.id === data.ticket_id) {
        fetchTicket(data.ticket_id);
      }
    });

    return () => socketRef.current?.disconnect();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, thinking]);

  const handleSelectTicket = (id) => {
    fetchTicket(id);
    setThinking(null);
  };

  const handleSend = async () => {
    if (!input.trim() || !activeTicket || sending) return;
    const text = input.trim();
    setInput('');
    setSending(true);

    addMessage({ id: Date.now(), content: text, is_ai: false, sender_id: user.id, created_at: new Date().toISOString() });
    setThinking('🔍 Orion is analyzing your request...');

    try {
      await sendMessage(activeTicket.id, text);
    } catch {
      toast.error('Failed to send message');
      setThinking(null);
    } finally {
      setSending(false);
    }
  };

  const handleCreateTicket = async (e) => {
    e.preventDefault();
    if (!newSubject.trim()) return;
    try {
      const data = await createTicket(newSubject, selectedOrderId || null);
      toast.success('Ticket created! Describe your issue below.');
      setShowNew(false);
      setNewSubject('');
      setSelectedOrderId('');
      handleSelectTicket(data.ticket_id);
    } catch {
      toast.error('Failed to create ticket');
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  const handleOpenNewTicket = () => {
    fetchOrders();
    setShowNew(true);
  };

  return (
    <div className="app-shell">
      {/* Sidebar */}
      <div className="sidebar">
        <div className="sidebar-logo">
          <div className="sidebar-logo-icon">🛸</div>
          <div>
            <div style={{ fontWeight: 800, fontSize: '1.1rem' }}><span className="gradient-text">Orion</span></div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Support Engine</div>
          </div>
        </div>
        <div className="sidebar-nav">
          <div className="nav-section-label">Navigation</div>
          <button className="nav-item active">
            <span className="nav-icon">💬</span> My Tickets
            <span className="nav-count">{tickets.length}</span>
          </button>
          <button className="nav-item" onClick={() => { logout(); navigate('/login'); }}>
            <span className="nav-icon">🚪</span> Sign Out
          </button>
        </div>
        <div style={{ padding: '16px', borderTop: '1px solid var(--border)' }}>
          <div className="flex items-center gap-2">
            <div style={{ width: 32, height: 32, borderRadius: '50%', background: 'var(--accent)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: 14 }}>
              {user?.name?.[0]?.toUpperCase()}
            </div>
            <div>
              <div style={{ fontSize: '0.85rem', fontWeight: 600 }}>{user?.name}</div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{user?.role}</div>
            </div>
          </div>
        </div>
      </div>

      {/* Chat shell */}
      <div className="chat-shell" style={{ flex: 1 }}>
        {/* Ticket sidebar */}
        <div className="chat-sidebar">
          <div className="chat-sidebar-header">
            <div className="flex justify-between items-center" style={{ marginBottom: '12px' }}>
              <h3 style={{ fontSize: '0.9rem' }}>Your Tickets</h3>
              <button className="btn btn-primary btn-sm" onClick={handleOpenNewTicket}>+ New</button>
            </div>
          </div>
          <div className="ticket-list">
            {tickets.length === 0 && (
              <div className="empty-state" style={{ padding: '32px 16px' }}>
                <div className="empty-icon">🎫</div>
                <p style={{ fontSize: '0.82rem' }}>No tickets yet. Create your first one!</p>
              </div>
            )}
            {tickets.map((t) => (
              <div key={t.id} className={`ticket-list-item ${activeTicket?.id === t.id ? 'active' : ''}`} onClick={() => handleSelectTicket(t.id)}>
                <div className="ticket-subject">{t.subject}</div>
                <div className="ticket-meta">
                  <span className={`badge ${STATUS_BADGE[t.status] || 'badge-gray'}`} style={{ fontSize: '0.65rem' }}>{t.status}</span>
                  {t.intent && <span style={{ color: 'var(--accent-bright)' }}>{t.intent}</span>}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Chat main */}
        <div className="chat-main">
          {!activeTicket ? (
            <div className="empty-state" style={{ flex: 1 }}>
              <div style={{ fontSize: 64 }}>🛸</div>
              <h2 className="gradient-text">Orion Support</h2>
              <p>Select a ticket or create a new one to get started.</p>
              <button className="btn btn-primary" style={{ marginTop: 8 }} onClick={handleOpenNewTicket}>Create New Ticket</button>
            </div>
          ) : (
            <>
              {/* Chat header */}
              <div className="chat-header">
                <div className="flex justify-between items-center">
                  <div>
                    <div style={{ fontWeight: 700, fontSize: '0.95rem' }}>{activeTicket.subject}</div>
                    <div className="flex items-center gap-2" style={{ marginTop: 4 }}>
                      <span className={`badge ${STATUS_BADGE[activeTicket.status] || 'badge-gray'}`}>{activeTicket.status}</span>
                      <span className={`badge ${activeTicket.priority === 'P0' ? 'badge-red' : activeTicket.priority === 'P1' ? 'badge-yellow' : 'badge-gray'}`}>{activeTicket.priority}</span>
                      {activeTicket.intent && <span className="badge badge-cyan">{activeTicket.intent}</span>}
                      {activeTicket.resolution_type && <span className={`badge ${PATH_BADGE[activeTicket.resolution_type] || 'badge-gray'}`}>{activeTicket.resolution_type}</span>}
                    </div>
                  </div>
                  {activeTicket.confidence_score && (
                    <div style={{ textAlign: 'right' }}>
                      <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Confidence</div>
                      <div style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--success)' }}>
                        {Math.round(parseFloat(activeTicket.confidence_score) * 100)}%
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Messages */}
              <div className="messages-area">
                {messages.length === 0 && (
                  <div className="empty-state">
                    <div className="empty-icon">💬</div>
                    <p style={{ fontWeight: 600, marginBottom: 4 }}>Your ticket is ready!</p>
                    <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>Describe your issue below and Orion will start analyzing it immediately.</p>
                  </div>
                )}
                {messages.map((msg, i) => (
                  <div key={msg.id || i} className={`flex flex-col ${msg.is_ai ? '' : 'items-end'}`}>
                    <div className={`message-bubble ${msg.is_ai ? 'ai' : 'user'}`}>
                      {msg.is_ai && (
                        <div style={{ fontSize: '0.72rem', color: msg.metadata?.is_agent_reply ? '#22c55e' : 'var(--accent-bright)', fontWeight: 700, marginBottom: 6, display: 'flex', alignItems: 'center', gap: 4 }}>
                          {msg.metadata?.is_agent_reply ? `👨‍💼 ${msg.metadata.sender_name || 'Agent'}` : '🛸 Orion'}
                        </div>
                      )}
                      <div style={{ fontSize: '0.9rem', lineHeight: 1.6 }}>{msg.content}</div>
                      {msg.metadata?.steps_taken?.length > 0 && (
                        <div className="message-steps">
                          {msg.metadata.steps_taken.map((s, idx) => (
                            <span key={idx} className="step-pill">{s}</span>
                          ))}
                        </div>
                      )}
                      <div className="message-meta">{formatTime(msg.created_at)}</div>
                    </div>
                  </div>
                ))}

                {thinking && (
                  <div className="flex flex-col">
                    <div className="message-bubble ai" style={{ maxWidth: '60%' }}>
                      <div style={{ fontSize: '0.72rem', color: 'var(--accent-bright)', fontWeight: 700, marginBottom: 8 }}>🛸 Orion</div>
                      <div className="thinking-bar">
                        <div className="typing-dots"><span /><span /><span /></div>
                        <span style={{ fontSize: '0.82rem' }}>{thinking}</span>
                      </div>
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>

              {/* Input */}
              <div className="chat-input-area">
                <div className="chat-input-row">
                  <textarea
                    className="chat-input"
                    placeholder="Describe your issue... (Enter to send)"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={handleKeyDown}
                    rows={1}
                  />
                  <button className="btn btn-primary btn-icon" onClick={handleSend} disabled={!input.trim() || sending || !!thinking} style={{ width: 48, height: 48, borderRadius: '12px', justifyContent: 'center' }}>
                    {sending ? <div className="spinner" style={{ width: 16, height: 16 }} /> : '→'}
                  </button>
                </div>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: 8 }}>
                  Orion AI will autonomously resolve routine issues • Shift+Enter for new line
                </div>
              </div>
            </>
          )}
        </div>
      </div>

      {/* New Ticket Modal — with Order Selection */}
      {showNew && (
        <div className="modal-overlay" onClick={() => setShowNew(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 520 }}>
            <h3 style={{ marginBottom: 6 }}>Create New Ticket</h3>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginBottom: 20 }}>
              Give your issue a short subject and link an order if applicable.
            </p>
            <form onSubmit={handleCreateTicket} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <div>
                <label>Subject <span style={{ color: 'var(--error)' }}>*</span></label>
                <input
                  className="input"
                  placeholder="e.g. I didn't receive my refund"
                  value={newSubject}
                  onChange={(e) => setNewSubject(e.target.value)}
                  autoFocus
                  required
                />
              </div>

              {/* Order selection */}
              <div>
                <label>Related Order <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 400 }}>(recommended for order issues)</span></label>
                <select
                  className="input"
                  value={selectedOrderId}
                  onChange={(e) => setSelectedOrderId(e.target.value)}
                  style={{ cursor: 'pointer' }}
                >
                  <option value="">— No order linked —</option>
                  {orders.map((o) => (
                    <option key={o.order_id} value={o.order_id}>
                      {o.order_id} — ${o.total_amount.toFixed(2)} — {(o.items || []).map(i => i.name).join(', ')} ({o.status})
                    </option>
                  ))}
                </select>
              </div>

              {/* Selected order preview */}
              {selectedOrderId && (() => {
                const o = orders.find(x => x.order_id === selectedOrderId);
                if (!o) return null;
                return (
                  <div style={{
                    background: 'rgba(99, 102, 241, 0.08)',
                    border: '1px solid rgba(99, 102, 241, 0.2)',
                    borderRadius: 10,
                    padding: '12px 16px',
                    fontSize: '0.82rem',
                  }}>
                    <div className="flex justify-between items-center" style={{ marginBottom: 6 }}>
                      <span style={{ fontWeight: 700, color: 'var(--accent-bright)' }}>{o.order_id}</span>
                      <span className={`badge ${o.status === 'delivered' ? 'badge-green' : o.status === 'shipped' ? 'badge-blue' : 'badge-yellow'}`} style={{ fontSize: '0.65rem' }}>
                        {o.status}
                      </span>
                    </div>
                    <div style={{ color: 'var(--text-secondary)' }}>
                      {(o.items || []).map(i => `${i.name} ×${i.qty}`).join(', ')}
                    </div>
                    <div className="flex justify-between" style={{ marginTop: 6, color: 'var(--text-muted)', fontSize: '0.75rem' }}>
                      <span>Total: <strong style={{ color: 'var(--text-primary)' }}>${o.total_amount.toFixed(2)}</strong></span>
                      <span>Ordered: {formatDate(o.order_date)}</span>
                    </div>
                  </div>
                );
              })()}

              <div className="flex gap-3" style={{ marginTop: 4 }}>
                <button type="button" className="btn btn-ghost" style={{ flex: 1, justifyContent: 'center' }} onClick={() => { setShowNew(false); setSelectedOrderId(''); }}>Cancel</button>
                <button type="submit" className="btn btn-primary" style={{ flex: 1, justifyContent: 'center' }}>Create Ticket →</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
