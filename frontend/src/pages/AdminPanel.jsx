import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import api from '../api/client';
import toast from 'react-hot-toast';

const ROLE_BADGE = { customer: 'badge-blue', agent: 'badge-purple', manager: 'badge-yellow', admin: 'badge-red' };

export default function AdminPanel() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('stats');
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState([]);
  const [auditLog, setAuditLog] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateUser, setShowCreateUser] = useState(false);
  const [newUser, setNewUser] = useState({ name: '', email: '', password: '', role: 'agent' });

  useEffect(() => { loadData(); }, [activeTab]);

  const loadData = async () => {
    setLoading(true);
    try {
      if (activeTab === 'stats') {
        const { data } = await api.get('/admin/stats');
        setStats(data);
      } else if (activeTab === 'users') {
        const { data } = await api.get('/admin/users');
        setUsers(data);
      } else if (activeTab === 'audit') {
        const { data } = await api.get('/admin/audit-log?limit=100');
        setAuditLog(data);
      }
    } catch {
      toast.error('Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateUser = async (e) => {
    e.preventDefault();
    try {
      await api.post('/admin/users', newUser);
      toast.success('User created');
      setShowCreateUser(false);
      setNewUser({ name: '', email: '', password: '', role: 'agent' });
      loadData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to create user');
    }
  };

  const handleDeactivate = async (userId) => {
    if (!window.confirm('Deactivate this user?')) return;
    try {
      await api.patch(`/admin/users/${userId}/deactivate`);
      toast.success('User deactivated');
      loadData();
    } catch {
      toast.error('Failed to deactivate');
    }
  };

  const tabs = [
    { id: 'stats', label: 'System Stats', icon: '📊' },
    { id: 'users', label: 'User Management', icon: '👥' },
    { id: 'audit', label: 'Audit Log', icon: '📋' },
  ];

  return (
    <div className="app-shell">
      {/* Sidebar */}
      <div className="sidebar">
        <div className="sidebar-logo">
          <div className="sidebar-logo-icon">🛸</div>
          <div>
            <div style={{ fontWeight: 800 }}><span className="gradient-text">Orion</span></div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Admin Panel</div>
          </div>
        </div>
        <div className="sidebar-nav">
          <div className="nav-section-label">Admin</div>
          {tabs.map((t) => (
            <button key={t.id} className={`nav-item ${activeTab === t.id ? 'active' : ''}`} onClick={() => setActiveTab(t.id)}>
              <span>{t.icon}</span> {t.label}
            </button>
          ))}
          <div className="divider" style={{ margin: '12px 0' }} />
          <button className="nav-item" onClick={() => { logout(); navigate('/login'); }}>
            <span>🚪</span> Sign Out
          </button>
        </div>
        <div style={{ padding: '16px', borderTop: '1px solid var(--border)' }}>
          <div className="flex items-center gap-2">
            <div style={{ width: 32, height: 32, borderRadius: '50%', background: 'var(--danger)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: 14 }}>{user?.name?.[0]}</div>
            <div>
              <div style={{ fontSize: '0.85rem', fontWeight: 600 }}>{user?.name}</div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Administrator</div>
            </div>
          </div>
        </div>
      </div>

      {/* Main */}
      <div className="main-content">
        <div className="page-header">
          <div>
            <h2>{tabs.find((t) => t.id === activeTab)?.icon} {tabs.find((t) => t.id === activeTab)?.label}</h2>
            <p style={{ fontSize: '0.85rem', marginTop: 2 }}>Orion system administration</p>
          </div>
          <div className="flex gap-2">
            {activeTab === 'users' && (
              <button className="btn btn-primary btn-sm" onClick={() => setShowCreateUser(true)}>+ Create User</button>
            )}
            <button className="btn btn-ghost btn-sm" onClick={loadData}>↻ Refresh</button>
          </div>
        </div>

        <div className="page-body">
          {loading ? (
            <div className="flex items-center justify-center" style={{ padding: 80 }}>
              <div className="spinner" style={{ width: 32, height: 32 }} />
            </div>
          ) : activeTab === 'stats' && stats ? (
            <>
              <div className="stat-grid">
                {[
                  { label: 'Total Tickets', value: stats.total_tickets, icon: '🎫', color: 'var(--accent)' },
                  { label: 'Open', value: stats.open, icon: '📂', color: 'var(--info)' },
                  { label: 'Resolved', value: stats.resolved, icon: '✅', color: 'var(--success)' },
                  { label: 'Pending Approval', value: stats.pending_approval, icon: '⏳', color: 'var(--warning)' },
                  { label: 'Escalated', value: stats.escalated, icon: '🚨', color: 'var(--danger)' },
                  { label: 'Resolution Rate', value: `${stats.resolution_rate}%`, icon: '📈', color: 'var(--purple)' },
                  { label: 'Actions Executed', value: stats.total_actions_executed, icon: '⚡', color: 'var(--accent-bright)' },
                ].map((s) => (
                  <div key={s.label} className="stat-card" style={{ '--accent-color': s.color }}>
                    <div className="stat-icon" style={{ background: `${s.color}20` }}><span style={{ fontSize: 20 }}>{s.icon}</span></div>
                    <div className="stat-value">{s.value}</div>
                    <div className="stat-label">{s.label}</div>
                  </div>
                ))}
              </div>

              {stats.intent_distribution && Object.keys(stats.intent_distribution).length > 0 && (
                <div className="card" style={{ marginTop: 4 }}>
                  <h3 style={{ marginBottom: 16 }}>Intent Distribution</h3>
                  {Object.entries(stats.intent_distribution).map(([intent, count]) => {
                    const pct = Math.round((count / (stats.total_tickets || 1)) * 100);
                    return (
                      <div key={intent} style={{ marginBottom: 12 }}>
                        <div className="flex justify-between" style={{ marginBottom: 5 }}>
                          <span style={{ fontSize: '0.85rem' }}>{intent.replace(/_/g, ' ')}</span>
                          <span className="badge badge-blue">{count}</span>
                        </div>
                        <div style={{ background: 'var(--bg-surface)', borderRadius: 99, height: 6 }}>
                          <div style={{ width: `${pct}%`, height: '100%', background: 'linear-gradient(90deg, var(--accent), var(--purple))', borderRadius: 99 }} />
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </>
          ) : activeTab === 'users' ? (
            <div className="table-wrapper">
              <table className="table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Name</th>
                    <th>Email</th>
                    <th>Role</th>
                    <th>Status</th>
                    <th>Created</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => (
                    <tr key={u.id}>
                      <td style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>#{u.id}</td>
                      <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{u.name}</td>
                      <td>{u.email}</td>
                      <td><span className={`badge ${ROLE_BADGE[u.role] || 'badge-gray'}`}>{u.role}</span></td>
                      <td>
                        <div className="flex items-center gap-2">
                          <div className={`status-dot ${u.is_active ? 'dot-green' : 'dot-gray'}`} />
                          <span style={{ fontSize: '0.8rem' }}>{u.is_active ? 'Active' : 'Inactive'}</span>
                        </div>
                      </td>
                      <td style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{new Date(u.created_at).toLocaleDateString()}</td>
                      <td>
                        {u.is_active && u.id !== user?.id && (
                          <button className="btn btn-danger btn-sm" onClick={() => handleDeactivate(u.id)}>Deactivate</button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : activeTab === 'audit' ? (
            <div className="table-wrapper">
              <table className="table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Ticket</th>
                    <th>Action</th>
                    <th>Executed By</th>
                    <th>Status</th>
                    <th>Result</th>
                    <th>Time</th>
                  </tr>
                </thead>
                <tbody>
                  {auditLog.map((log) => (
                    <tr key={log.id}>
                      <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', fontSize: '0.8rem' }}>#{log.id}</td>
                      <td><span className="badge badge-blue">#{log.ticket_id}</span></td>
                      <td><span className="badge badge-purple">{log.action_type}</span></td>
                      <td style={{ fontSize: '0.8rem', color: 'var(--accent-bright)', fontFamily: 'var(--font-mono)' }}>{log.executed_by}</td>
                      <td><span className={`badge ${log.status === 'executed' ? 'badge-green' : log.status === 'failed' ? 'badge-red' : 'badge-yellow'}`}>{log.status}</span></td>
                      <td style={{ fontSize: '0.78rem', color: 'var(--text-muted)', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{log.result || '—'}</td>
                      <td style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>{new Date(log.created_at).toLocaleString()}</td>
                    </tr>
                  ))}
                  {auditLog.length === 0 && (
                    <tr><td colSpan={7} style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>No audit logs yet</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          ) : null}
        </div>
      </div>

      {/* Create User Modal */}
      {showCreateUser && (
        <div className="modal-overlay" onClick={() => setShowCreateUser(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3 style={{ marginBottom: 20 }}>Create New User</h3>
            <form onSubmit={handleCreateUser} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <div><label>Full Name</label><input className="input" value={newUser.name} onChange={(e) => setNewUser({ ...newUser, name: e.target.value })} required /></div>
              <div><label>Email</label><input className="input" type="email" value={newUser.email} onChange={(e) => setNewUser({ ...newUser, email: e.target.value })} required /></div>
              <div><label>Password</label><input className="input" type="password" value={newUser.password} onChange={(e) => setNewUser({ ...newUser, password: e.target.value })} required /></div>
              <div>
                <label>Role</label>
                <select className="input" value={newUser.role} onChange={(e) => setNewUser({ ...newUser, role: e.target.value })}>
                  <option value="agent">Agent</option>
                  <option value="manager">Manager</option>
                  <option value="customer">Customer</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
              <div className="flex gap-3" style={{ marginTop: 4 }}>
                <button type="button" className="btn btn-ghost" style={{ flex: 1, justifyContent: 'center' }} onClick={() => setShowCreateUser(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary" style={{ flex: 1, justifyContent: 'center' }}>Create User</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
