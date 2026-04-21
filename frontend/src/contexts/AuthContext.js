import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { setToken, getToken } from '../utils';

const API = process.env.REACT_APP_BACKEND_URL || '';
const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const checkAuth = useCallback(async () => {
    const token = getToken();
    if (!token) { setUser(null); setLoading(false); return; }
    try {
      const res = await fetch(`${API}/api/auth/me`, { headers: { 'Authorization': `Bearer ${token}` } });
      if (!res.ok) { setToken(null); throw new Error('Not authenticated'); }
      setUser(await res.json());
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { checkAuth(); }, [checkAuth]);

  const logout = async () => {
    const token = getToken();
    try { await fetch(`${API}/api/auth/logout`, { method: 'POST', headers: { 'Authorization': `Bearer ${token}` } }); } catch {}
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, setUser, loading, logout, checkAuth }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
