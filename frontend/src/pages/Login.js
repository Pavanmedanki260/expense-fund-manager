import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useTheme } from '../contexts/ThemeContext';
import toast from 'react-hot-toast';
import { Eye, EyeOff } from 'lucide-react';
import { setToken } from '../utils';

const API = process.env.REACT_APP_BACKEND_URL || '';

export default function Login() {
  const { theme } = useTheme();
  const { setUser } = useAuth();
  const navigate = useNavigate();
  const [isRegister, setIsRegister] = useState(false);
  const [form, setForm] = useState({ name: '', email: '', password: '' });
  const [showPw, setShowPw] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (isRegister && !form.name.trim()) { setError('Name is required'); return; }
    if (!form.email.trim()) { setError('Email is required'); return; }
    if (form.password.length < 6) { setError('Password must be at least 6 characters'); return; }
    setLoading(true);
    try {
      const endpoint = isRegister ? '/api/auth/register' : '/api/auth/login';
      const body = isRegister ? form : { email: form.email, password: form.password };
      const res = await fetch(`${API}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (!res.ok) {
        const detail = data.detail;
        if (typeof detail === 'string') setError(detail);
        else if (Array.isArray(detail)) setError(detail.map(e => e.msg || JSON.stringify(e)).join(' '));
        else setError('Something went wrong');
        return;
      }
      if (data.access_token) setToken(data.access_token);
      setUser(data.user || data);
      toast.success(isRegister ? 'Account created!' : 'Welcome back!');
      navigate('/groups', { replace: true });
    } catch (err) {
      setError('Network error. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page" data-testid="login-page">
      <div className="login-left">
        <div className="login-content">
          <div className="login-logo">
            <div className="logo-icon">FT</div>
            <h1>FundTrack</h1>
          </div>
          <p className="login-tagline">
            {isRegister
              ? 'Create your account to start tracking funds across multiple groups.'
              : 'Track fund collections and utilizations across multiple groups with real-time analytics.'}
          </p>

          <form onSubmit={handleSubmit} style={{ marginTop: 8 }}>
            {isRegister && (
              <div className="form-group">
                <label>Full Name</label>
                <input
                  type="text"
                  value={form.name}
                  onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                  placeholder="Enter your name"
                  data-testid="register-name-input"
                />
              </div>
            )}
            <div className="form-group">
              <label>Email</label>
              <input
                type="email"
                value={form.email}
                onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
                placeholder="you@example.com"
                data-testid="login-email-input"
              />
            </div>
            <div className="form-group">
              <label>Password</label>
              <div style={{ position: 'relative' }}>
                <input
                  type={showPw ? 'text' : 'password'}
                  value={form.password}
                  onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
                  placeholder={isRegister ? 'Min 6 characters' : 'Enter password'}
                  style={{ paddingRight: 40 }}
                  data-testid="login-password-input"
                />
                <button
                  type="button"
                  onClick={() => setShowPw(!showPw)}
                  style={{ position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-secondary)', padding: 0 }}
                  data-testid="toggle-password-visibility"
                >
                  {showPw ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>

            {error && (
              <div style={{ background: 'var(--status-danger-bg)', color: 'var(--status-danger-text)', padding: '8px 12px', borderRadius: 8, fontSize: 13, marginBottom: 12 }} data-testid="auth-error">
                {error}
              </div>
            )}

            <button
              type="submit"
              className="btn btn-primary"
              style={{ width: '100%', marginTop: 4 }}
              disabled={loading}
              data-testid="auth-submit-btn"
            >
              {loading ? 'Please wait...' : (isRegister ? 'Create Account' : 'Sign In')}
            </button>
          </form>

          <div style={{ textAlign: 'center', marginTop: 20, fontSize: 14, color: 'var(--text-secondary)' }}>
            {isRegister ? 'Already have an account?' : "Don't have an account?"}
            <button
              onClick={() => { setIsRegister(!isRegister); setError(''); }}
              style={{ background: 'none', border: 'none', color: 'var(--primary)', cursor: 'pointer', fontWeight: 500, marginLeft: 4, fontSize: 14 }}
              data-testid="toggle-auth-mode"
            >
              {isRegister ? 'Sign In' : 'Create Account'}
            </button>
          </div>
        </div>
      </div>
      <div className="login-right">
        <img
          src="https://images.pexels.com/photos/36077712/pexels-photo-36077712.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940"
          alt="Modern architecture"
        />
        <div className="login-right-overlay"></div>
      </div>
    </div>
  );
}
