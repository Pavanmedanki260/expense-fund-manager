import React, { useState, useEffect } from 'react';
import { NavLink, useLocation, useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useTheme } from '../contexts/ThemeContext';
import { LayoutDashboard, IndianRupee, ArrowDownUp, FileBarChart, Users, LogOut, Menu, X, Sun, Moon, ArrowLeft } from 'lucide-react';
import { api } from '../utils';

export default function GroupLayout({ children }) {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const { groupId } = useParams();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [group, setGroup] = useState(null);
  const [userRole, setUserRole] = useState(null);
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    if (groupId) {
      api.get(`/api/groups/${groupId}`).then(g => {
        setGroup(g);
        setUserRole(g.user_role);
      }).catch(() => navigate('/groups'));
    }
  }, [groupId, navigate]);

  const canManageMembers = userRole === 'admin' || user?.is_super_admin;

  const navItems = [
    { to: `/groups/${groupId}/dashboard`, label: 'Dashboard', icon: LayoutDashboard },
    { to: `/groups/${groupId}/funds`, label: 'Fund Collection', icon: IndianRupee },
    { to: `/groups/${groupId}/utilizations`, label: 'Utilization', icon: ArrowDownUp },
    { to: `/groups/${groupId}/reports`, label: 'Reports', icon: FileBarChart },
  ];
  if (canManageMembers) {
    navItems.push({ to: `/groups/${groupId}/members`, label: 'Members', icon: Users });
  }

  const pageTitle = navItems.find(n => n.to === location.pathname)?.label || group?.name || 'FundTrack';

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <div className="app-layout" data-testid="app-layout">
      {sidebarOpen && <div className="sidebar-overlay" onClick={() => setSidebarOpen(false)} />}
      <aside className={`sidebar ${sidebarOpen ? 'open' : ''}`} data-testid="sidebar">
        <div className="sidebar-logo">
          <div className="logo-icon">FT</div>
          <h1>FundTrack</h1>
          <button className="menu-btn" onClick={() => setSidebarOpen(false)} style={{ marginLeft: 'auto' }}>
            <X size={20} />
          </button>
        </div>
        <div style={{ padding: '12px 12px 0', borderBottom: '1px solid var(--border)', paddingBottom: 12 }}>
          <button
            onClick={() => { navigate('/groups'); setSidebarOpen(false); }}
            style={{ display: 'flex', alignItems: 'center', gap: 6, background: 'none', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', fontSize: 13, padding: 0 }}
            data-testid="back-to-groups"
          >
            <ArrowLeft size={14} /> All Groups
          </button>
          {group && <p style={{ fontSize: 14, fontWeight: 600, color: 'var(--primary)', marginTop: 6, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{group.name}</p>}
          {userRole && <span style={{ fontSize: 11, color: 'var(--text-secondary)', textTransform: 'capitalize' }}>{userRole === 'super_admin' ? 'Super Admin' : userRole}</span>}
        </div>
        <nav className="sidebar-nav">
          {navItems.map(item => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => isActive ? 'active' : ''}
              onClick={() => setSidebarOpen(false)}
              data-testid={`nav-${item.label.toLowerCase().replace(/\s+/g, '-')}`}
            >
              <item.icon size={18} />
              {item.label}
            </NavLink>
          ))}
          <button onClick={handleLogout} data-testid="logout-btn" style={{ marginTop: 'auto' }}>
            <LogOut size={18} />
            Logout
          </button>
        </nav>
        {user && (
          <div className="sidebar-user">
            <img src={user.avatar_url || 'https://via.placeholder.com/32'} alt={user.name} />
            <div className="sidebar-user-info">
              <p>{user.name}</p>
              <span>{user.is_super_admin ? 'Super Admin' : 'Member'}</span>
            </div>
          </div>
        )}
      </aside>
      <main className="main-content">
        <header className="topbar" data-testid="topbar">
          <div className="topbar-left">
            <button className="menu-btn" onClick={() => setSidebarOpen(true)} data-testid="menu-toggle">
              <Menu size={22} />
            </button>
            <h2>{pageTitle}</h2>
          </div>
          <div className="topbar-right">
            <button className="theme-toggle" onClick={toggleTheme} data-testid="theme-toggle">
              {theme === 'light' ? <Moon size={18} /> : <Sun size={18} />}
            </button>
          </div>
        </header>
        <div className="page-content">
          {React.Children.map(children, child =>
            React.cloneElement(child, { groupId, userRole, group })
          )}
        </div>
      </main>
    </div>
  );
}
