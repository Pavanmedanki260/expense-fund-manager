import React, { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend, PieChart, Pie, Cell } from 'recharts';
import { Download, FileBarChart } from 'lucide-react';
import toast from 'react-hot-toast';
import { useTheme } from '../contexts/ThemeContext';
import { api, formatINR } from '../utils';

const CATEGORY_COLORS = ['#1D9E75', '#147A5A', '#5DCAA5', '#F59E0B'];

export default function Reports() {
  const { theme } = useTheme();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [filters, setFilters] = useState({ date_from: '', date_to: '', category: '' });

  const textColor = theme === 'dark' ? '#F5F5F5' : '#374151';

  useEffect(() => {
    api.get('/api/dashboard').then(setData).catch(console.error).finally(() => setLoading(false));
  }, []);

  const handleExport = async () => {
    setExporting(true);
    try {
      const params = new URLSearchParams();
      if (filters.date_from) params.set('date_from', filters.date_from);
      if (filters.date_to) params.set('date_to', filters.date_to);
      if (filters.category) params.set('category', filters.category);
      const blob = await api.download(`/api/export/excel?${params}`);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `fundtrack_report_${new Date().toISOString().split('T')[0]}.xlsx`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      toast.success('Report downloaded');
    } catch (err) {
      toast.error('Export failed');
    } finally {
      setExporting(false);
    }
  };

  if (loading) return <div className="loading-page"><div className="spinner"></div></div>;
  if (!data) return <div className="empty-state"><p>Failed to load report data</p></div>;

  return (
    <div data-testid="reports-page">
      <div className="filters-bar mb-6">
        <div className="form-group">
          <label>From</label>
          <input type="date" value={filters.date_from} onChange={e => setFilters(f => ({ ...f, date_from: e.target.value }))} data-testid="report-date-from" />
        </div>
        <div className="form-group">
          <label>To</label>
          <input type="date" value={filters.date_to} onChange={e => setFilters(f => ({ ...f, date_to: e.target.value }))} data-testid="report-date-to" />
        </div>
        <div className="form-group">
          <label>Category</label>
          <select value={filters.category} onChange={e => setFilters(f => ({ ...f, category: e.target.value }))} data-testid="report-category-filter">
            <option value="">All Categories</option>
            <option value="Donation">Donation</option>
            <option value="Grant">Grant</option>
            <option value="Revenue">Revenue</option>
            <option value="Other">Other</option>
          </select>
        </div>
        <div className="form-group" style={{ display: 'flex', alignItems: 'flex-end' }}>
          <button className="btn btn-primary" onClick={handleExport} disabled={exporting} data-testid="export-excel-btn">
            <Download size={16} /> {exporting ? 'Exporting...' : 'Download Excel'}
          </button>
        </div>
      </div>

      <div className="kpi-grid mb-6">
        <div className="kpi-card" data-testid="report-total-collected">
          <div className="kpi-label">Total Collected</div>
          <div className="kpi-value">{formatINR(data.total_collected)}</div>
        </div>
        <div className="kpi-card" data-testid="report-total-utilized">
          <div className="kpi-label">Total Utilized</div>
          <div className="kpi-value">{formatINR(data.total_utilized)}</div>
        </div>
        <div className="kpi-card" data-testid="report-balance">
          <div className="kpi-label">Balance</div>
          <div className="kpi-value">{formatINR(data.balance)}</div>
        </div>
        <div className="kpi-card" data-testid="report-pct-utilized">
          <div className="kpi-label">% Utilized</div>
          <div className="kpi-value">{data.pct_utilized}%</div>
        </div>
      </div>

      <div className="charts-grid">
        <div className="card" data-testid="report-category-chart">
          <h3 style={{ marginBottom: 16 }}>Category Breakdown</h3>
          {data.category_breakdown.length > 0 ? (
            <ResponsiveContainer width="100%" height={280}>
              <PieChart>
                <Pie data={data.category_breakdown} dataKey="amount" nameKey="category" cx="50%" cy="50%" outerRadius={100} label={({ category, percent }) => `${category} ${(percent * 100).toFixed(0)}%`}>
                  {data.category_breakdown.map((_, i) => (
                    <Cell key={i} fill={CATEGORY_COLORS[i % CATEGORY_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(val) => formatINR(val)} contentStyle={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8, color: textColor }} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="empty-state"><p>No data</p></div>
          )}
        </div>

        <div className="card" data-testid="report-monthly-chart">
          <h3 style={{ marginBottom: 16 }}>Monthly Comparison</h3>
          {data.monthly_data.length > 0 ? (
            <ResponsiveContainer width="100%" height={280}>
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
            <div className="empty-state"><p>No monthly data</p></div>
          )}
        </div>
      </div>
    </div>
  );
}
