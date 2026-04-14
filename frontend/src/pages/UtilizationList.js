import React, { useState, useEffect } from 'react';
import toast from 'react-hot-toast';
import { Plus, Pencil, Trash2 } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { api, formatINR, formatDate } from '../utils';

export default function UtilizationList() {
  const { user } = useAuth();
  const [items, setItems] = useState([]);
  const [funds, setFunds] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingItem, setEditingItem] = useState(null);
  const [deleteConfirm, setDeleteConfirm] = useState(null);
  const [filters, setFilters] = useState({ linked_fund_id: '', date_from: '', date_to: '' });

  const [form, setForm] = useState({ purpose: '', amount_inr: '', date_spent: '', linked_fund_id: '', notes: '' });

  const canEdit = user?.role === 'admin' || user?.role === 'contributor';

  const fetchData = async () => {
    try {
      const params = new URLSearchParams();
      if (filters.linked_fund_id) params.set('linked_fund_id', filters.linked_fund_id);
      if (filters.date_from) params.set('date_from', filters.date_from);
      if (filters.date_to) params.set('date_to', filters.date_to);
      const [utilData, fundData] = await Promise.all([
        api.get(`/api/utilizations?${params}`),
        api.get('/api/funds'),
      ]);
      setItems(utilData);
      setFunds(fundData);
    } catch (err) {
      toast.error('Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, [filters]);

  const openAdd = () => {
    setEditingItem(null);
    setForm({ purpose: '', amount_inr: '', date_spent: '', linked_fund_id: funds[0]?.fund_id || '', notes: '' });
    setShowModal(true);
  };

  const openEdit = (item) => {
    setEditingItem(item);
    setForm({
      purpose: item.purpose,
      amount_inr: item.amount_inr,
      date_spent: item.date_spent,
      linked_fund_id: item.linked_fund_id,
      notes: item.notes || '',
    });
    setShowModal(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.purpose || !form.amount_inr || !form.date_spent || !form.linked_fund_id) {
      toast.error('Please fill required fields');
      return;
    }
    if (Number(form.amount_inr) <= 0) {
      toast.error('Amount must be positive');
      return;
    }
    const today = new Date().toISOString().split('T')[0];
    if (form.date_spent > today) {
      toast.error('Date cannot be in the future');
      return;
    }
    try {
      const body = { ...form, amount_inr: Number(form.amount_inr) };
      if (editingItem) {
        await api.put(`/api/utilizations/${editingItem.util_id}`, body);
        toast.success('Utilization updated');
      } else {
        await api.post('/api/utilizations', body);
        toast.success('Utilization added');
      }
      setShowModal(false);
      fetchData();
    } catch (err) {
      toast.error('Operation failed');
    }
  };

  const handleDelete = async () => {
    try {
      await api.del(`/api/utilizations/${deleteConfirm.util_id}`);
      toast.success('Utilization deleted');
      setDeleteConfirm(null);
      fetchData();
    } catch (err) {
      toast.error('Delete failed');
    }
  };

  const canModify = (item) => user?.role === 'admin' || item.spent_by_user_id === user?.user_id;

  return (
    <div data-testid="utilization-list-page">
      <div className="flex items-center justify-between mb-4">
        <h3 style={{ fontSize: 16 }}>{items.length} Utilization{items.length !== 1 ? 's' : ''}</h3>
        {canEdit && (
          <button className="btn btn-primary btn-sm" onClick={openAdd} data-testid="add-utilization-btn">
            <Plus size={16} /> Add Utilization
          </button>
        )}
      </div>

      <div className="filters-bar">
        <div className="form-group">
          <label>Linked Fund</label>
          <select value={filters.linked_fund_id} onChange={e => setFilters(f => ({ ...f, linked_fund_id: e.target.value }))} data-testid="util-fund-filter">
            <option value="">All Funds</option>
            {funds.map(f => <option key={f.fund_id} value={f.fund_id}>{f.source_name}</option>)}
          </select>
        </div>
        <div className="form-group">
          <label>From</label>
          <input type="date" value={filters.date_from} onChange={e => setFilters(f => ({ ...f, date_from: e.target.value }))} data-testid="util-date-from" />
        </div>
        <div className="form-group">
          <label>To</label>
          <input type="date" value={filters.date_to} onChange={e => setFilters(f => ({ ...f, date_to: e.target.value }))} data-testid="util-date-to" />
        </div>
      </div>

      <div className="card">
        {loading ? (
          <div className="loading-page" style={{ minHeight: 200 }}><div className="spinner"></div></div>
        ) : items.length === 0 ? (
          <div className="empty-state"><p>No utilizations found</p></div>
        ) : (
          <div className="table-container">
            <table data-testid="utilizations-table">
              <thead>
                <tr>
                  <th>Purpose</th>
                  <th>Amount</th>
                  <th>Date</th>
                  <th>Fund Source</th>
                  <th>Spent By</th>
                  {canEdit && <th>Actions</th>}
                </tr>
              </thead>
              <tbody>
                {items.map(item => (
                  <tr key={item.util_id} data-testid={`util-row-${item.util_id}`}>
                    <td style={{ fontWeight: 500 }}>{item.purpose}</td>
                    <td>{formatINR(item.amount_inr)}</td>
                    <td>{formatDate(item.date_spent)}</td>
                    <td>{item.linked_fund_name}</td>
                    <td>{item.spent_by_name}</td>
                    {canEdit && (
                      <td>
                        <div className="flex gap-2">
                          {canModify(item) && (
                            <>
                              <button className="btn btn-secondary btn-sm" onClick={() => openEdit(item)} data-testid={`edit-util-${item.util_id}`}><Pencil size={14} /></button>
                              <button className="btn btn-danger btn-sm" onClick={() => setDeleteConfirm(item)} data-testid={`delete-util-${item.util_id}`}><Trash2 size={14} /></button>
                            </>
                          )}
                        </div>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {showModal && (
        <div className="modal-overlay" data-testid="utilization-modal">
          <div className="modal-content">
            <div className="modal-header">
              <h3>{editingItem ? 'Edit Utilization' : 'Add New Utilization'}</h3>
              <button className="modal-close" onClick={() => setShowModal(false)} data-testid="close-util-modal">&times;</button>
            </div>
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label>Purpose *</label>
                <input type="text" value={form.purpose} onChange={e => setForm(f => ({ ...f, purpose: e.target.value }))} required data-testid="util-purpose-input" />
              </div>
              <div className="form-group">
                <label>Amount (INR) *</label>
                <input type="number" min="0" step="0.01" value={form.amount_inr} onChange={e => setForm(f => ({ ...f, amount_inr: e.target.value }))} required data-testid="util-amount-input" />
              </div>
              <div className="form-group">
                <label>Date Spent *</label>
                <input type="date" value={form.date_spent} onChange={e => setForm(f => ({ ...f, date_spent: e.target.value }))} required data-testid="util-date-input" />
              </div>
              <div className="form-group">
                <label>Linked Fund *</label>
                <select value={form.linked_fund_id} onChange={e => setForm(f => ({ ...f, linked_fund_id: e.target.value }))} required data-testid="util-fund-select">
                  <option value="">Select Fund</option>
                  {funds.map(f => <option key={f.fund_id} value={f.fund_id}>{f.source_name} ({formatINR(f.amount_inr)})</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Notes</label>
                <textarea value={form.notes} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))} data-testid="util-notes-input"></textarea>
              </div>
              <div className="modal-actions">
                <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary" data-testid="util-submit-btn">{editingItem ? 'Update' : 'Add Utilization'}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {deleteConfirm && (
        <div className="modal-overlay" data-testid="util-delete-confirm">
          <div className="modal-content confirm-dialog">
            <h3 style={{ marginBottom: 12 }}>Delete Utilization</h3>
            <p>Are you sure you want to delete "{deleteConfirm.purpose}"? This action cannot be undone.</p>
            <div className="confirm-actions">
              <button className="btn btn-secondary" onClick={() => setDeleteConfirm(null)} data-testid="cancel-util-delete">Cancel</button>
              <button className="btn btn-danger" onClick={handleDelete} data-testid="confirm-util-delete">Delete</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
