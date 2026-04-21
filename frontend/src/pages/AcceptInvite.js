import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { api } from '../utils';

export default function AcceptInvite() {
  const { inviteId } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [invitation, setInvitation] = useState(null);
  const [status, setStatus] = useState('loading');
  const hasProcessed = useRef(false);

  useEffect(() => {
    api.getPublic(`/api/invitations/${inviteId}`)
      .then(inv => {
        setInvitation(inv);
        setStatus(inv.status !== 'pending' ? 'already_accepted' : 'ready');
      })
      .catch(() => setStatus('not_found'));
  }, [inviteId]);

  useEffect(() => {
    if (user && status === 'ready' && !hasProcessed.current) {
      hasProcessed.current = true;
      (async () => {
        try {
          setStatus('accepting');
          const result = await api.post(`/api/invitations/${inviteId}/accept`);
          setStatus('accepted');
          setTimeout(() => navigate(`/groups/${result.group_id}/dashboard`, { replace: true }), 1500);
        } catch { setStatus('error'); }
      })();
    }
  }, [user, status, inviteId, navigate]);

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20 }} data-testid="accept-invite-page">
      <div className="card" style={{ maxWidth: 440, width: '100%', textAlign: 'center', padding: 32 }}>
        <div className="logo-icon" style={{ margin: '0 auto 16px', width: 48, height: 48, fontSize: 20 }}>FT</div>
        <h2 style={{ fontFamily: "'Outfit', sans-serif", marginBottom: 8, color: 'var(--primary)' }}>FundTrack</h2>

        {status === 'loading' && <div><div className="spinner" style={{ margin: '24px auto' }}></div><p style={{ color: 'var(--text-secondary)' }}>Loading invitation...</p></div>}

        {status === 'not_found' && <div><p style={{ color: 'var(--status-danger-text)', marginTop: 16 }}>Invitation not found or expired.</p><button className="btn btn-primary" style={{ marginTop: 16 }} onClick={() => navigate('/groups')}>Go to FundTrack</button></div>}

        {status === 'already_accepted' && <div><p style={{ color: 'var(--text-secondary)', marginTop: 16 }}>This invitation has already been accepted.</p><button className="btn btn-primary" style={{ marginTop: 16 }} onClick={() => navigate('/groups')}>Go to Groups</button></div>}

        {status === 'ready' && !user && invitation && (
          <div>
            <p style={{ color: 'var(--text-body)', marginTop: 16, marginBottom: 8 }}>You've been invited to join</p>
            <h3 style={{ color: 'var(--text-primary)', fontFamily: "'Outfit', sans-serif", marginBottom: 4 }}>{invitation.group_name}</h3>
            <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 24 }}>as <strong style={{ color: 'var(--primary)', textTransform: 'capitalize' }}>{invitation.role}</strong></p>
            <p style={{ fontSize: 14, color: 'var(--text-body)', marginBottom: 12 }}>Please login or create an account to accept.</p>
            <button className="btn btn-primary" onClick={() => navigate('/login')} data-testid="invite-login-btn">Sign In / Register</button>
          </div>
        )}

        {(status === 'accepting' || (status === 'ready' && user)) && <div><div className="spinner" style={{ margin: '24px auto' }}></div><p style={{ color: 'var(--text-secondary)' }}>Joining group...</p></div>}

        {status === 'accepted' && (
          <div>
            <div style={{ width: 48, height: 48, borderRadius: '50%', background: 'var(--status-healthy-bg)', color: 'var(--status-healthy-text)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '16px auto', fontSize: 24 }}>&#10003;</div>
            <p style={{ color: 'var(--status-healthy-text)', fontWeight: 500 }}>You've joined the group!</p>
            <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 4 }}>Redirecting...</p>
          </div>
        )}

        {status === 'error' && <div><p style={{ color: 'var(--status-danger-text)', marginTop: 16 }}>Failed to accept invitation. It may be for a different email.</p><button className="btn btn-primary" style={{ marginTop: 16 }} onClick={() => navigate('/groups')}>Go to FundTrack</button></div>}
      </div>
    </div>
  );
}
