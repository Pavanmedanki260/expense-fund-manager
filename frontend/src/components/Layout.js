import React, { useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useTheme } from '../contexts/ThemeContext';
import { LayoutDashboard, IndianRupee, ArrowDownUp, FileBarChart, Users, LogOut, Menu, X, Sun, Moon } from 'lucide-react';

export default function Layout({ children }) {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const location = useLocation();

  const navItems = [
    { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/funds', label: 'Fund Collection', icon: IndianRupee },
    { to: '/utilizations', label: 'Utilization', icon: ArrowDownUp },
    { to: '/reports', label: 'Reports', icon: FileBarChart },
  ];

  if (user?.role === 'admin') {
    navItems.push({ to: '/users', label: 'User Management', icon: Users });
  }

  const pageTitle = navItems.find(n => n.to === location.pathname)?.label || 'FundTrack';

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
        <nav className="sidebar-nav">
          {navItems.map(item => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => isActive ? 'active' : ''}
              onClick={() => setSidebarOpen(false)}
              data-testid={`nav-${item.to.substring(1)}`}
            >
              <item.icon size={18} />
              {item.label}
            </NavLink>
          ))}
          <button onClick={logout} data-testid="logout-btn" style={{ marginTop: 'auto' }}>
            <LogOut size={18} />
            Logout
          </button>
        </nav>
        {user && (
          <div className="sidebar-user">
            <img src={user.avatar_url || 'https://via.placeholder.com/32'} alt={user.name} />
            <div className="sidebar-user-info">
              <p>{user.name}</p>
              <span>{user.role}</span>
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
          {children}
        </div>
      </main>
    </div>
  );
}
