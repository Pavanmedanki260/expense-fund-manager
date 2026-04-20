import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { api } from '../utils';

const API = process.env.REACT_APP_BACKEND_URL;

export default function AcceptInvite() {
  const { inviteId } = useParams();
  const { user, setUser } = useAuth();
  const navigate = useNavigate();
  const [invitation, setInvitation] = useState(null);
  const [status, setStatus] = useState('loading');
  const hasProcessed = useRef(false);

  useEffect(() => {
    // Fetch invitation details (public endpoint)
    api.getPublic(`/api/invitations/${inviteId}`)
      .then(inv => {
        setInvitation(inv);
        if (inv.status !== 'pending') {
          setStatus('already_accepted');
        } else {
          setStatus('ready');
        }
      })
      .catch(() => setStatus('not_found'));
  }, [inviteId]);

  useEffect(() => {
    // If user is logged in and invitation is ready, auto-accept
    if (user && status === 'ready' && !hasProcessed.current) {
      hasProcessed.current = true;
      acceptInvite();
    }
  }, [user, status]);

  const acceptInvite = async () => {
    try {
      setStatus('accepting');
      const result = await api.post(`/api/invitations/${inviteId}/accept`);
      setStatus('accepted');
      setTimeout(() => navigate(`/groups/${result.group_id}/dashboard`, { replace: true }), 1500);
    } catch (err) {
      setStatus('error');
    }
  };

  const handleLogin = () => {
    // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    // After login, user will return to /groups and pending invites will auto-accept
    const redirectUrl = window.location.origin + '/invite/' + inviteId;
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20 }} data-testid="accept-invite-page">
      <div className="card" style={{ maxWidth: 440, width: '100%', textAlign: 'center', padding: 32 }}>
        <div className="logo-icon" style={{ margin: '0 auto 16px', width: 48, height: 48, fontSize: 20 }}>FT</div>
        <h2 style={{ fontFamily: "'Outfit', sans-serif", marginBottom: 8, color: 'var(--primary)' }}>FundTrack</h2>

        {status === 'loading' && (
          <div><div className="spinner" style={{ margin: '24px auto' }}></div><p style={{ color: 'var(--text-secondary)' }}>Loading invitation...</p></div>
        )}

        {status === 'not_found' && (
          <div><p style={{ color: 'var(--status-danger-text)', marginTop: 16 }}>Invitation not found or has expired.</p>
            <button className="btn btn-primary" style={{ marginTop: 16 }} onClick={() => navigate('/groups')}>Go to FundTrack</button>
          </div>
        )}

        {status === 'already_accepted' && (
          <div><p style={{ color: 'var(--text-secondary)', marginTop: 16 }}>This invitation has already been accepted.</p>
            <button className="btn btn-primary" style={{ marginTop: 16 }} onClick={() => navigate('/groups')}>Go to Groups</button>
          </div>
        )}

        {status === 'ready' && !user && invitation && (
          <div>
            <p style={{ color: 'var(--text-body)', marginTop: 16, marginBottom: 8 }}>You've been invited to join</p>
            <h3 style={{ color: 'var(--text-primary)', fontFamily: "'Outfit', sans-serif", marginBottom: 4 }}>{invitation.group_name}</h3>
            <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 24 }}>as <strong style={{ color: 'var(--primary)', textTransform: 'capitalize' }}>{invitation.role}</strong></p>
            <button className="google-btn" onClick={handleLogin} data-testid="invite-login-btn" style={{ maxWidth: 300, margin: '0 auto' }}>
              <svg viewBox="0 0 24 24" width="20" height="20">
                <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4"/>
                <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
                <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
              </svg>
              Sign in with Google to Accept
            </button>
          </div>
        )}

        {status === 'ready' && user && (
          <div><div className="spinner" style={{ margin: '24px auto' }}></div><p style={{ color: 'var(--text-secondary)' }}>Accepting invitation...</p></div>
        )}

        {status === 'accepting' && (
          <div><div className="spinner" style={{ margin: '24px auto' }}></div><p style={{ color: 'var(--text-secondary)' }}>Joining group...</p></div>
        )}

        {status === 'accepted' && (
          <div>
            <div style={{ width: 48, height: 48, borderRadius: '50%', background: 'var(--status-healthy-bg)', color: 'var(--status-healthy-text)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '16px auto', fontSize: 24 }}>✓</div>
            <p style={{ color: 'var(--status-healthy-text)', fontWeight: 500 }}>You've joined the group!</p>
            <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 4 }}>Redirecting to dashboard...</p>
          </div>
        )}

        {status === 'error' && (
          <div><p style={{ color: 'var(--status-danger-text)', marginTop: 16 }}>Failed to accept invitation. It may be for a different email address.</p>
            <button className="btn btn-primary" style={{ marginTop: 16 }} onClick={() => navigate('/groups')}>Go to FundTrack</button>
          </div>
        )}
      </div>
    </div>
  );
}
