import React, { useState, useEffect } from 'react';
import toast from 'react-hot-toast';
import { Plus, Pencil, Trash2, Search } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { api, formatINR, formatDate, getStatusBadge } from '../utils';

export default function FundList() {
  const { user } = useAuth();
  const [funds, setFunds] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingFund, setEditingFund] = useState(null);
  const [deleteConfirm, setDeleteConfirm] = useState(null);
  const [filters, setFilters] = useState({ category: '', date_from: '', date_to: '', search: '' });

  const [form, setForm] = useState({ source_name: '', amount_inr: '', category: 'Donation', date_received: '', notes: '' });

  const canEdit = user?.role === 'admin' || user?.role === 'contributor';

  const fetchFunds = async () => {
    try {
      const params = new URLSearchParams();
      if (filters.category) params.set('category', filters.category);
      if (filters.date_from) params.set('date_from', filters.date_from);
      if (filters.date_to) params.set('date_to', filters.date_to);
      if (filters.search) params.set('search', filters.search);
      const data = await api.get(`/api/funds?${params}`);
      setFunds(data);
    } catch (err) {
      toast.error('Failed to load funds');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchFunds(); }, [filters]);

  const openAdd = () => {
    setEditingFund(null);
    setForm({ source_name: '', amount_inr: '', category: 'Donation', date_received: '', notes: '' });
    setShowModal(true);
  };

  const openEdit = (fund) => {
    setEditingFund(fund);
    setForm({
      source_name: fund.source_name,
      amount_inr: fund.amount_inr,
      category: fund.category,
      date_received: fund.date_received,
      notes: fund.notes || '',
    });
    setShowModal(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.source_name || !form.amount_inr || !form.date_received) {
      toast.error('Please fill required fields');
      return;
    }
    if (Number(form.amount_inr) <= 0) {
      toast.error('Amount must be positive');
      return;
    }
    try {
      const body = { ...form, amount_inr: Number(form.amount_inr) };
      if (editingFund) {
        await api.put(`/api/funds/${editingFund.fund_id}`, body);
        toast.success('Fund updated');
      } else {
        await api.post('/api/funds', body);
        toast.success('Fund added');
      }
      setShowModal(false);
      fetchFunds();
    } catch (err) {
      toast.error('Operation failed');
    }
  };

  const handleDelete = async () => {
    try {
      await api.del(`/api/funds/${deleteConfirm.fund_id}`);
      toast.success('Fund deleted');
      setDeleteConfirm(null);
      fetchFunds();
    } catch (err) {
      toast.error('Delete failed');
    }
  };

  const canModify = (fund) => user?.role === 'admin' || fund.added_by_user_id === user?.user_id;

  // Calculate utilization per fund (simplified - we'd need utilization data)
  // For now, show category-based status
  const getFundStatus = () => ({ class: 'badge-healthy', text: 'Active' });

  return (
    <div data-testid="fund-list-page">
      <div className="flex items-center justify-between mb-4">
        <h3 style={{ fontSize: 16 }}>{funds.length} Fund{funds.length !== 1 ? 's' : ''}</h3>
        {canEdit && (
          <button className="btn btn-primary btn-sm" onClick={openAdd} data-testid="add-fund-btn">
            <Plus size={16} /> Add Fund
          </button>
        )}
      </div>

      <div className="filters-bar">
        <div className="form-group">
          <label>Search</label>
          <div style={{ position: 'relative' }}>
            <input
              type="text"
              placeholder="Search funds..."
              value={filters.search}
              onChange={e => setFilters(f => ({ ...f, search: e.target.value }))}
              data-testid="fund-search-input"
            />
          </div>
        </div>
        <div className="form-group">
          <label>Category</label>
          <select value={filters.category} onChange={e => setFilters(f => ({ ...f, category: e.target.value }))} data-testid="fund-category-filter">
            <option value="">All Categories</option>
            <option value="Donation">Donation</option>
            <option value="Grant">Grant</option>
            <option value="Revenue">Revenue</option>
            <option value="Other">Other</option>
          </select>
        </div>
        <div className="form-group">
          <label>From</label>
          <input type="date" value={filters.date_from} onChange={e => setFilters(f => ({ ...f, date_from: e.target.value }))} data-testid="fund-date-from" />
        </div>
        <div className="form-group">
          <label>To</label>
          <input type="date" value={filters.date_to} onChange={e => setFilters(f => ({ ...f, date_to: e.target.value }))} data-testid="fund-date-to" />
        </div>
      </div>

      <div className="card">
        {loading ? (
          <div className="loading-page" style={{ minHeight: 200 }}><div className="spinner"></div></div>
        ) : funds.length === 0 ? (
          <div className="empty-state"><p>No funds found</p></div>
        ) : (
          <div className="table-container">
            <table data-testid="funds-table">
              <thead>
                <tr>
                  <th>Source</th>
                  <th>Amount</th>
                  <th>Category</th>
                  <th>Date</th>
                  <th>Added By</th>
                  <th>Status</th>
                  {canEdit && <th>Actions</th>}
                </tr>
              </thead>
              <tbody>
                {funds.map(fund => {
                  const status = getFundStatus();
                  return (
                    <tr key={fund.fund_id} data-testid={`fund-row-${fund.fund_id}`}>
                      <td style={{ fontWeight: 500 }}>{fund.source_name}</td>
                      <td>{formatINR(fund.amount_inr)}</td>
                      <td><span className="badge badge-role">{fund.category}</span></td>
                      <td>{formatDate(fund.date_received)}</td>
                      <td>{fund.added_by_name}</td>
                      <td><span className={`badge ${status.class}`}>{status.text}</span></td>
                      {canEdit && (
                        <td>
                          <div className="flex gap-2">
                            {canModify(fund) && (
                              <>
                                <button className="btn btn-secondary btn-sm" onClick={() => openEdit(fund)} data-testid={`edit-fund-${fund.fund_id}`}><Pencil size={14} /></button>
                                <button className="btn btn-danger btn-sm" onClick={() => setDeleteConfirm(fund)} data-testid={`delete-fund-${fund.fund_id}`}><Trash2 size={14} /></button>
                              </>
                            )}
                          </div>
                        </td>
                      )}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {showModal && (
        <div className="modal-overlay" data-testid="fund-modal">
          <div className="modal-content">
            <div className="modal-header">
              <h3>{editingFund ? 'Edit Fund' : 'Add New Fund'}</h3>
              <button className="modal-close" onClick={() => setShowModal(false)} data-testid="close-fund-modal">&times;</button>
            </div>
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label>Source Name *</label>
                <input type="text" value={form.source_name} onChange={e => setForm(f => ({ ...f, source_name: e.target.value }))} required data-testid="fund-source-input" />
              </div>
              <div className="form-group">
                <label>Amount (INR) *</label>
                <input type="number" min="0" step="0.01" value={form.amount_inr} onChange={e => setForm(f => ({ ...f, amount_inr: e.target.value }))} required data-testid="fund-amount-input" />
              </div>
              <div className="form-group">
                <label>Category *</label>
                <select value={form.category} onChange={e => setForm(f => ({ ...f, category: e.target.value }))} data-testid="fund-category-select">
                  <option value="Donation">Donation</option>
                  <option value="Grant">Grant</option>
                  <option value="Revenue">Revenue</option>
                  <option value="Other">Other</option>
                </select>
              </div>
              <div className="form-group">
                <label>Date Received *</label>
                <input type="date" value={form.date_received} onChange={e => setForm(f => ({ ...f, date_received: e.target.value }))} required data-testid="fund-date-input" />
              </div>
              <div className="form-group">
                <label>Notes</label>
                <textarea value={form.notes} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))} data-testid="fund-notes-input"></textarea>
              </div>
              <div className="modal-actions">
                <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary" data-testid="fund-submit-btn">{editingFund ? 'Update' : 'Add Fund'}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {deleteConfirm && (
        <div className="modal-overlay" data-testid="delete-confirm-modal">
          <div className="modal-content confirm-dialog">
            <h3 style={{ marginBottom: 12 }}>Delete Fund</h3>
            <p>Are you sure you want to delete "{deleteConfirm.source_name}"? This action cannot be undone.</p>
            <div className="confirm-actions">
              <button className="btn btn-secondary" onClick={() => setDeleteConfirm(null)} data-testid="cancel-delete-btn">Cancel</button>
              <button className="btn btn-danger" onClick={handleDelete} data-testid="confirm-delete-btn">Delete</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
