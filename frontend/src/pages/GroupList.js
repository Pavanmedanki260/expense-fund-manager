import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { Plus, Users, FolderOpen, LogOut, Sun, Moon, Shield } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useTheme } from '../contexts/ThemeContext';
import { api, formatDate } from '../utils';

export default function GroupList() {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const [groups, setGroups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ name: '', description: '' });

  useEffect(() => {
    api.get('/api/groups').then(setGroups).catch(() => toast.error('Failed to load groups')).finally(() => setLoading(false));
  }, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!form.name.trim()) { toast.error('Group name is required'); return; }
    try {
      const group = await api.post('/api/groups', form);
      toast.success('Group created');
      setShowCreate(false);
      setForm({ name: '', description: '' });
      navigate(`/groups/${group.group_id}/dashboard`);
    } catch { toast.error('Failed to create group'); }
  };

  const handleLogout = async () => { await logout(); navigate('/login'); };

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)' }} data-testid="group-list-page">
      {/* Header */}
      <header style={{ background: 'var(--surface)', borderBottom: '1px solid var(--border)', padding: '0 24px', height: 56, display: 'flex', alignItems: 'center', justifyContent: 'space-between', position: 'sticky', top: 0, zIndex: 30 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div className="logo-icon">FT</div>
          <h1 style={{ fontSize: 20, fontWeight: 600, color: 'var(--primary)', fontFamily: "'Outfit', sans-serif" }}>FundTrack</h1>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          {user?.is_super_admin && <span className="badge badge-role" style={{ display: 'flex', alignItems: 'center', gap: 4 }}><Shield size={12} /> Super Admin</span>}
          <img src={user?.avatar_url || 'https://via.placeholder.com/28'} alt="" style={{ width: 28, height: 28, borderRadius: '50%' }} />
          <span style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-primary)' }}>{user?.name}</span>
          <button className="theme-toggle" onClick={toggleTheme} data-testid="theme-toggle">
            {theme === 'light' ? <Moon size={18} /> : <Sun size={18} />}
          </button>
          <button className="btn btn-secondary btn-sm" onClick={handleLogout} data-testid="logout-btn">
            <LogOut size={14} /> Logout
          </button>
        </div>
      </header>

      <div style={{ maxWidth: 900, margin: '0 auto', padding: '32px 20px' }}>
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 style={{ fontSize: 24, fontFamily: "'Outfit', sans-serif" }}>Your Fund Groups</h2>
            <p style={{ fontSize: 14, color: 'var(--text-secondary)', marginTop: 4 }}>
              {user?.is_super_admin ? 'You can see all groups as Super Admin' : 'Groups you are a member of'}
            </p>
          </div>
          <button className="btn btn-primary" onClick={() => setShowCreate(true)} data-testid="create-group-btn">
            <Plus size={16} /> Create Group
          </button>
        </div>

        {loading ? (
          <div className="loading-page" style={{ minHeight: 200 }}><div className="spinner"></div></div>
        ) : groups.length === 0 ? (
          <div className="card" style={{ textAlign: 'center', padding: 48 }}>
            <FolderOpen size={48} style={{ color: 'var(--text-secondary)', opacity: 0.4, margin: '0 auto 12px' }} />
            <p style={{ color: 'var(--text-secondary)', fontSize: 15 }}>No groups yet. Create your first fund group to get started.</p>
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 16 }}>
            {groups.map(g => (
              <div
                key={g.group_id}
                className="card"
                style={{ cursor: 'pointer', transition: 'border-color 0.15s' }}
                onClick={() => navigate(`/groups/${g.group_id}/dashboard`)}
                data-testid={`group-card-${g.group_id}`}
                onMouseEnter={e => e.currentTarget.style.borderColor = 'var(--primary)'}
                onMouseLeave={e => e.currentTarget.style.borderColor = 'var(--border)'}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                  <h3 style={{ fontSize: 17, fontFamily: "'Outfit', sans-serif", color: 'var(--text-primary)' }}>{g.name}</h3>
                  <span className="badge badge-role" style={{ textTransform: 'capitalize' }}>
                    {g.user_role === 'super_admin' ? 'Super Admin' : g.user_role}
                  </span>
                </div>
                {g.description && <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 12, lineHeight: 1.4 }}>{g.description}</p>}
                <div style={{ display: 'flex', alignItems: 'center', gap: 12, fontSize: 13, color: 'var(--text-secondary)' }}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}><Users size={14} /> {g.member_count} member{g.member_count !== 1 ? 's' : ''}</span>
                  <span>Created {formatDate(g.created_at)}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {showCreate && (
        <div className="modal-overlay" data-testid="create-group-modal">
          <div className="modal-content">
            <div className="modal-header">
              <h3>Create Fund Group</h3>
              <button className="modal-close" onClick={() => setShowCreate(false)} data-testid="close-create-group">&times;</button>
            </div>
            <form onSubmit={handleCreate}>
              <div className="form-group">
                <label>Group Name *</label>
                <input type="text" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} placeholder="e.g., Education Fund 2025" required data-testid="group-name-input" />
              </div>
              <div className="form-group">
                <label>Description</label>
                <textarea value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} placeholder="What is this fund group for?" data-testid="group-desc-input"></textarea>
              </div>
              <div className="modal-actions">
                <button type="button" className="btn btn-secondary" onClick={() => setShowCreate(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary" data-testid="submit-create-group">Create Group</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
