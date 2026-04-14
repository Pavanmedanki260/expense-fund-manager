import React, { useState, useEffect } from 'react';
import toast from 'react-hot-toast';
import { Shield, UserX, UserCheck } from 'lucide-react';
import { api, formatDate } from '../utils';

export default function UserManagement() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchUsers = async () => {
    try {
      const data = await api.get('/api/users');
      setUsers(data);
    } catch (err) {
      toast.error('Failed to load users');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchUsers(); }, []);

  const updateRole = async (userId, newRole) => {
    try {
      await api.put(`/api/users/${userId}/role`, { role: newRole });
      toast.success('Role updated');
      fetchUsers();
    } catch (err) {
      toast.error('Failed to update role');
    }
  };

  const toggleStatus = async (userId, currentStatus) => {
    try {
      await api.put(`/api/users/${userId}/status`, { is_active: !currentStatus });
      toast.success(currentStatus ? 'User deactivated' : 'User activated');
      fetchUsers();
    } catch (err) {
      toast.error('Failed to update status');
    }
  };

  return (
    <div data-testid="user-management-page">
      <div className="flex items-center justify-between mb-4">
        <h3 style={{ fontSize: 16 }}>{users.length} User{users.length !== 1 ? 's' : ''}</h3>
      </div>

      <div className="card">
        {loading ? (
          <div className="loading-page" style={{ minHeight: 200 }}><div className="spinner"></div></div>
        ) : users.length === 0 ? (
          <div className="empty-state"><p>No users found</p></div>
        ) : (
          <div className="table-container">
            <table data-testid="users-table">
              <thead>
                <tr>
                  <th>User</th>
                  <th>Email</th>
                  <th>Role</th>
                  <th>Status</th>
                  <th>Joined</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map(u => (
                  <tr key={u.user_id} data-testid={`user-row-${u.user_id}`}>
                    <td>
                      <div className="flex items-center gap-2">
                        <img src={u.avatar_url || 'https://via.placeholder.com/28'} alt={u.name} style={{ width: 28, height: 28, borderRadius: '50%' }} />
                        <span style={{ fontWeight: 500 }}>{u.name}</span>
                      </div>
                    </td>
                    <td>{u.email}</td>
                    <td>
                      <select
                        value={u.role}
                        onChange={e => updateRole(u.user_id, e.target.value)}
                        style={{
                          padding: '4px 8px',
                          border: '1px solid var(--border)',
                          borderRadius: 8,
                          background: 'transparent',
                          color: 'var(--text-body)',
                          fontSize: 13,
                        }}
                        data-testid={`role-select-${u.user_id}`}
                      >
                        <option value="admin">Admin</option>
                        <option value="contributor">Contributor</option>
                        <option value="viewer">Viewer</option>
                      </select>
                    </td>
                    <td>
                      <span className={`badge ${u.is_active ? 'badge-healthy' : 'badge-danger'}`}>
                        {u.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td>{formatDate(u.created_at)}</td>
                    <td>
                      <button
                        className={`btn btn-sm ${u.is_active ? 'btn-danger' : 'btn-primary'}`}
                        onClick={() => toggleStatus(u.user_id, u.is_active)}
                        data-testid={`toggle-status-${u.user_id}`}
                      >
                        {u.is_active ? <UserX size={14} /> : <UserCheck size={14} />}
                        {u.is_active ? 'Deactivate' : 'Activate'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
