import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import api from '../api/client';
import toast from 'react-hot-toast';

export default function Login() {
  const [mode, setMode] = useState('login');
  const [form, setForm] = useState({ name: '', email: '', password: '', role: 'customer' });
  const [loading, setLoading] = useState(false);
  const { login } = useAuthStore();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const endpoint = mode === 'login' ? '/auth/login' : '/auth/register';
      const payload = mode === 'login'
        ? { email: form.email, password: form.password }
        : form;
      const { data } = await api.post(endpoint, payload);
      login(data.user, data.access_token);
      toast.success(`Welcome back, ${data.user.name}!`);
      const roleRoutes = { customer: '/chat', agent: '/agent', manager: '/manager', admin: '/admin' };
      navigate(roleRoutes[data.user.role] || '/chat');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Something went wrong');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page" style={{ background: 'var(--bg-primary)', alignItems: 'center', justifyContent: 'center', position: 'relative', overflow: 'hidden' }}>
      {/* Background orbs */}
      <div style={{ position: 'absolute', top: '-20%', left: '-10%', width: '600px', height: '600px', background: 'radial-gradient(circle, rgba(59,130,246,0.08) 0%, transparent 70%)', borderRadius: '50%', pointerEvents: 'none' }} />
      <div style={{ position: 'absolute', bottom: '-20%', right: '-10%', width: '500px', height: '500px', background: 'radial-gradient(circle, rgba(139,92,246,0.08) 0%, transparent 70%)', borderRadius: '50%', pointerEvents: 'none' }} />

      <div className="card scale-in" style={{ width: '100%', maxWidth: '440px', margin: '24px', position: 'relative' }}>
        {/* Logo */}
        <div className="flex items-center gap-3" style={{ marginBottom: '32px' }}>
          <div className="sidebar-logo-icon">🛸</div>
          <div>
            <div style={{ fontSize: '1.4rem', fontWeight: 800, letterSpacing: '-0.5px' }}>
              <span className="gradient-text">Orion</span>
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Autonomous Support Engine</div>
          </div>
        </div>

        {/* Tab toggle */}
        <div className="flex" style={{ background: 'var(--bg-surface)', borderRadius: 'var(--radius)', padding: '4px', marginBottom: '28px' }}>
          {['login', 'register'].map((m) => (
            <button
              key={m}
              className="btn"
              onClick={() => setMode(m)}
              style={{
                flex: 1,
                background: mode === m ? 'var(--bg-card)' : 'transparent',
                color: mode === m ? 'var(--text-primary)' : 'var(--text-muted)',
                border: mode === m ? '1px solid var(--border)' : 'none',
                boxShadow: mode === m ? 'var(--shadow-sm)' : 'none',
                justifyContent: 'center',
              }}
            >
              {m === 'login' ? 'Sign In' : 'Register'}
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {mode === 'register' && (
            <div className="fade-in">
              <label>Full Name</label>
              <input className="input" placeholder="Alice Johnson" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
            </div>
          )}

          <div>
            <label>Email Address</label>
            <input className="input" type="email" placeholder="alice@example.com" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required />
          </div>

          <div>
            <label>Password</label>
            <input className="input" type="password" placeholder="••••••••" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required />
          </div>

          {mode === 'register' && (
            <div className="fade-in">
              <label>Role</label>
              <select className="input" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
                <option value="customer">Customer</option>
                <option value="agent">Support Agent</option>
                <option value="manager">Manager</option>
                <option value="admin">Admin</option>
              </select>
            </div>
          )}

          <button className="btn btn-primary w-full" type="submit" disabled={loading} style={{ justifyContent: 'center', marginTop: '8px', height: '46px' }}>
            {loading ? <div className="spinner" /> : mode === 'login' ? 'Sign In to Orion' : 'Create Account'}
          </button>
        </form>

        {/* Demo accounts */}
        <div style={{ marginTop: '24px', padding: '16px', background: 'var(--bg-surface)', borderRadius: 'var(--radius)', border: '1px solid var(--border)' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '8px', fontWeight: 600 }}>DEMO ACCOUNTS</div>
          {[
            { role: 'Customer', email: 'customer@demo.com', pass: 'demo1234' },
            { role: 'Agent', email: 'agent@demo.com', pass: 'demo1234' },
            { role: 'Manager', email: 'manager@demo.com', pass: 'demo1234' },
            { role: 'Admin', email: 'admin@demo.com', pass: 'demo1234' },
          ].map((d) => (
            <div key={d.role} className="flex justify-between" style={{ fontSize: '0.78rem', padding: '3px 0', color: 'var(--text-secondary)' }}>
              <span style={{ color: 'var(--accent-bright)' }}>{d.role}</span>
              <span>{d.email} / {d.pass}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
