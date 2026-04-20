import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import toast from 'react-hot-toast';
import { UserPlus, UserX, Mail, Clock, CheckCircle } from 'lucide-react';
import { api, formatDate } from '../utils';

export default function GroupMembers() {
  const { groupId } = useParams();
  const [members, setMembers] = useState([]);
  const [invitations, setInvitations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showInvite, setShowInvite] = useState(false);
  const [inviteForm, setInviteForm] = useState({ email: '', role: 'viewer' });
  const [sending, setSending] = useState(false);
  const [removeConfirm, setRemoveConfirm] = useState(null);

  const fetchData = async () => {
    try {
      const [m, inv] = await Promise.all([
        api.get(`/api/groups/${groupId}/members`),
        api.get(`/api/groups/${groupId}/invitations`),
      ]);
      setMembers(m);
      setInvitations(inv);
    } catch { toast.error('Failed to load members'); }
    finally { setLoading(false); }
  };

  useEffect(() => { if (groupId) fetchData(); }, [groupId]);

  const updateRole = async (userId, newRole) => {
    try {
      await api.put(`/api/groups/${groupId}/members/${userId}/role`, { role: newRole });
      toast.success('Role updated');
      fetchData();
    } catch { toast.error('Failed to update role'); }
  };

  const removeMember = async () => {
    try {
      await api.del(`/api/groups/${groupId}/members/${removeConfirm.user_id}`);
      toast.success('Member removed');
      setRemoveConfirm(null);
      fetchData();
    } catch { toast.error('Failed to remove member'); }
  };

  const handleInvite = async (e) => {
    e.preventDefault();
    if (!inviteForm.email) { toast.error('Email is required'); return; }
    setSending(true);
    try {
      await api.post(`/api/groups/${groupId}/invite`, inviteForm);
      toast.success(`Invitation sent to ${inviteForm.email}`);
      setShowInvite(false);
      setInviteForm({ email: '', role: 'viewer' });
      fetchData();
    } catch (err) {
      toast.error('Failed to send invitation');
    } finally { setSending(false); }
  };

  return (
    <div data-testid="group-members-page">
      <div className="flex items-center justify-between mb-4">
        <h3 style={{ fontSize: 16 }}>{members.length} Member{members.length !== 1 ? 's' : ''}</h3>
        <button className="btn btn-primary btn-sm" onClick={() => setShowInvite(true)} data-testid="invite-member-btn">
          <UserPlus size={16} /> Invite Member
        </button>
      </div>

      {/* Members Table */}
      <div className="card mb-6">
        <h3 style={{ marginBottom: 16, fontSize: 15 }}>Members</h3>
        {loading ? <div className="loading-page" style={{ minHeight: 120 }}><div className="spinner"></div></div> : (
          <div className="table-container">
            <table data-testid="members-table">
              <thead><tr><th>User</th><th>Email</th><th>Role</th><th>Joined</th><th>Actions</th></tr></thead>
              <tbody>
                {members.map(m => (
                  <tr key={m.user_id} data-testid={`member-row-${m.user_id}`}>
                    <td>
                      <div className="flex items-center gap-2">
                        <img src={m.avatar_url || 'https://via.placeholder.com/28'} alt={m.name} style={{ width: 28, height: 28, borderRadius: '50%' }} />
                        <span style={{ fontWeight: 500 }}>{m.name}</span>
                      </div>
                    </td>
                    <td>{m.email}</td>
                    <td>
                      <select
                        value={m.role}
                        onChange={e => updateRole(m.user_id, e.target.value)}
                        style={{ padding: '4px 8px', border: '1px solid var(--border)', borderRadius: 8, background: 'transparent', color: 'var(--text-body)', fontSize: 13 }}
                        data-testid={`role-select-${m.user_id}`}
                      >
                        <option value="admin">Admin</option>
                        <option value="contributor">Contributor</option>
                        <option value="viewer">Viewer</option>
                      </select>
                    </td>
                    <td>{formatDate(m.joined_at)}</td>
                    <td>
                      <button className="btn btn-danger btn-sm" onClick={() => setRemoveConfirm(m)} data-testid={`remove-member-${m.user_id}`}>
                        <UserX size={14} /> Remove
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Pending Invitations */}
      {invitations.length > 0 && (
        <div className="card">
          <h3 style={{ marginBottom: 16, fontSize: 15 }}>Invitations</h3>
          <div className="table-container">
            <table data-testid="invitations-table">
              <thead><tr><th>Email</th><th>Role</th><th>Status</th><th>Sent</th><th>Invited By</th></tr></thead>
              <tbody>
                {invitations.map(inv => (
                  <tr key={inv.invite_id} data-testid={`invite-row-${inv.invite_id}`}>
                    <td><div className="flex items-center gap-2"><Mail size={14} style={{ color: 'var(--text-secondary)' }} /> {inv.email}</div></td>
                    <td><span className="badge badge-role" style={{ textTransform: 'capitalize' }}>{inv.role}</span></td>
                    <td>
                      {inv.status === 'pending' ? (
                        <span className="badge badge-warning" style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}><Clock size={12} /> Pending</span>
                      ) : (
                        <span className="badge badge-healthy" style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}><CheckCircle size={12} /> Accepted</span>
                      )}
                    </td>
                    <td>{formatDate(inv.created_at)}</td>
                    <td>{inv.invited_by_name}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Invite Modal */}
      {showInvite && (
        <div className="modal-overlay" data-testid="invite-modal">
          <div className="modal-content">
            <div className="modal-header">
              <h3>Invite Member</h3>
              <button className="modal-close" onClick={() => setShowInvite(false)} data-testid="close-invite-modal">&times;</button>
            </div>
            <form onSubmit={handleInvite}>
              <div className="form-group">
                <label>Email Address *</label>
                <input type="email" value={inviteForm.email} onChange={e => setInviteForm(f => ({ ...f, email: e.target.value }))} placeholder="user@example.com" required data-testid="invite-email-input" />
              </div>
              <div className="form-group">
                <label>Role</label>
                <select value={inviteForm.role} onChange={e => setInviteForm(f => ({ ...f, role: e.target.value }))} data-testid="invite-role-select">
                  <option value="admin">Admin</option>
                  <option value="contributor">Contributor</option>
                  <option value="viewer">Viewer</option>
                </select>
              </div>
              <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 16 }}>
                An email invitation will be sent. Once the user clicks the link and signs in with Google, they'll automatically join this group.
              </p>
              <div className="modal-actions">
                <button type="button" className="btn btn-secondary" onClick={() => setShowInvite(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary" disabled={sending} data-testid="send-invite-btn">
                  {sending ? 'Sending...' : 'Send Invitation'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Remove Confirmation */}
      {removeConfirm && (
        <div className="modal-overlay" data-testid="remove-member-confirm">
          <div className="modal-content confirm-dialog">
            <h3 style={{ marginBottom: 12 }}>Remove Member</h3>
            <p>Remove {removeConfirm.name} from this group? They will lose access to all group data.</p>
            <div className="confirm-actions">
              <button className="btn btn-secondary" onClick={() => setRemoveConfirm(null)}>Cancel</button>
              <button className="btn btn-danger" onClick={removeMember} data-testid="confirm-remove-btn">Remove</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
