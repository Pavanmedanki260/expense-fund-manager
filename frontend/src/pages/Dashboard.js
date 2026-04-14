import React, { useState, useEffect } from 'react';
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { TrendingUp, TrendingDown, Wallet, Percent } from 'lucide-react';
import { useTheme } from '../contexts/ThemeContext';
import { api, formatINR, formatDate } from '../utils';

const CATEGORY_COLORS = ['#1D9E75', '#147A5A', '#5DCAA5', '#F59E0B'];

export default function Dashboard() {
  const { theme } = useTheme();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get('/api/dashboard').then(setData).catch(console.error).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="loading-page"><div className="spinner"></div></div>;
  if (!data) return <div className="empty-state"><p>Failed to load dashboard</p></div>;

  const textColor = theme === 'dark' ? '#F5F5F5' : '#374151';
  const gridColor = theme === 'dark' ? '#404040' : '#E4E4E7';

  const kpis = [
    { label: 'Total Collected', value: formatINR(data.total_collected), icon: TrendingUp, color: '#1D9E75', bg: 'var(--status-healthy-bg)' },
    { label: 'Total Utilized', value: formatINR(data.total_utilized), icon: TrendingDown, color: '#F59E0B', bg: 'var(--status-warning-bg)' },
    { label: 'Balance', value: formatINR(data.balance), icon: Wallet, color: data.balance >= 0 ? '#1D9E75' : '#EF4444', bg: data.balance >= 0 ? 'var(--status-healthy-bg)' : 'var(--status-danger-bg)' },
    { label: '% Utilized', value: `${data.pct_utilized}%`, icon: Percent, color: data.pct_utilized > 80 ? '#F59E0B' : '#1D9E75', bg: data.pct_utilized > 80 ? 'var(--status-warning-bg)' : 'var(--status-healthy-bg)' },
  ];

  return (
    <div data-testid="dashboard-page">
      <div className="kpi-grid" data-testid="kpi-grid">
        {kpis.map((kpi, i) => (
          <div className="kpi-card" key={i} data-testid={`kpi-${kpi.label.toLowerCase().replace(/\s+/g, '-')}`}>
            <div className="kpi-icon" style={{ background: kpi.bg, color: kpi.color }}>
              <kpi.icon size={18} />
            </div>
            <div className="kpi-label">{kpi.label}</div>
            <div className="kpi-value">{kpi.value}</div>
          </div>
        ))}
      </div>

      <div className="charts-grid">
        <div className="card" data-testid="category-chart">
          <h3 style={{ marginBottom: 16 }}>Fund Breakdown by Category</h3>
          {data.category_breakdown.length > 0 ? (
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie data={data.category_breakdown} dataKey="amount" nameKey="category" cx="50%" cy="50%" outerRadius={90} label={({ category, percent }) => `${category} ${(percent * 100).toFixed(0)}%`}>
                  {data.category_breakdown.map((_, i) => (
                    <Cell key={i} fill={CATEGORY_COLORS[i % CATEGORY_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(val) => formatINR(val)} contentStyle={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8, color: textColor }} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="empty-state"><p>No fund data yet</p></div>
          )}
        </div>

        <div className="card" data-testid="monthly-chart">
          <h3 style={{ marginBottom: 16 }}>Monthly Collected vs Utilized</h3>
          {data.monthly_data.length > 0 ? (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={data.monthly_data}>
                <XAxis dataKey="month" tick={{ fill: textColor, fontSize: 12 }} />
                <YAxis tick={{ fill: textColor, fontSize: 12 }} tickFormatter={(v) => `${(v / 1000).toFixed(0)}K`} />
                <Tooltip formatter={(val) => formatINR(val)} contentStyle={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8, color: textColor }} />
                <Legend />
                <Bar dataKey="collected" name="Collected" fill="#1D9E75" radius={[4, 4, 0, 0]} />
                <Bar dataKey="utilized" name="Utilized" fill="#F59E0B" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="empty-state"><p>No monthly data yet</p></div>
          )}
        </div>
      </div>

      <div className="card" data-testid="recent-activity">
        <h3 style={{ marginBottom: 16 }}>Recent Activity</h3>
        {data.recent_activity.length > 0 ? (
          data.recent_activity.map((item, i) => (
            <div className="activity-item" key={i}>
              <div className={`activity-dot ${item.type}`}></div>
              <div className="activity-text">
                <p>{item.description}</p>
                <span>{formatINR(item.amount)} - {item.user} - {formatDate(item.date)}</span>
              </div>
            </div>
          ))
        ) : (
          <div className="empty-state"><p>No recent activity</p></div>
        )}
      </div>
    </div>
  );
}
