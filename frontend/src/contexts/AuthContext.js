import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import axios from 'axios';

const AuthContext = createContext(null);
// Empty in local dev → calls go to `/api` (setupProxy.js forwards to localhost:8001).
// Set REACT_APP_BACKEND_URL in production to point at the deployed backend host.
const API = `${process.env.REACT_APP_BACKEND_URL || ''}/api`;

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [loading, setLoading] = useState(true);
  const [employers, setEmployers] = useState([]);
  const [selectedEmployer, setSelectedEmployer] = useState(null);

  const authHeaders = useCallback(() => ({
    headers: { Authorization: `Bearer ${token}` }
  }), [token]);

  useEffect(() => {
    if (token) {
      axios.get(`${API}/auth/me`, { headers: { Authorization: `Bearer ${token}` } })
        .then(res => {
          setUser(res.data);
          setLoading(false);
        })
        .catch(() => {
          localStorage.removeItem('token');
          setToken(null);
          setUser(null);
          setLoading(false);
        });
    } else {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    if (user && token) {
      axios.get(`${API}/employers`, { headers: { Authorization: `Bearer ${token}` } })
        .then(res => {
          setEmployers(res.data);
          if (res.data.length > 0 && !selectedEmployer) {
            setSelectedEmployer(res.data[0]);
          }
        })
        .catch(console.error);
    }
  }, [user, token, selectedEmployer]);

  const login = async (email, password) => {
    const res = await axios.post(`${API}/auth/login`, { email, password });
    localStorage.setItem('token', res.data.token);
    setToken(res.data.token);
    setUser(res.data.user);
    return res.data;
  };

  const register = async (data) => {
    const res = await axios.post(`${API}/auth/register`, data);
    localStorage.setItem('token', res.data.token);
    setToken(res.data.token);
    setUser(res.data.user);
    return res.data;
  };

  const registerEmployee = async (data) => {
    const res = await axios.post(`${API}/enrollment/employee/register`, {
      email: data.email,
      password: data.password,
      name: data.name,
      employer_code: data.employer_code,
    });
    localStorage.setItem('token', res.data.token);
    setToken(res.data.token);
    setUser(res.data.user);
    return res.data;
  };

  const logout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
    setEmployers([]);
    setSelectedEmployer(null);
  };

  const createEmployer = async (data) => {
    const res = await axios.post(`${API}/employers`, data, authHeaders());
    setEmployers(prev => [...prev, res.data]);
    if (!selectedEmployer) setSelectedEmployer(res.data);
    return res.data;
  };

  const refreshEmployers = async () => {
    const res = await axios.get(`${API}/employers`, authHeaders());
    setEmployers(res.data);
    return res.data;
  };

  return (
    <AuthContext.Provider value={{
      user, token, loading, login, register, registerEmployee, logout,
      employers, selectedEmployer, setSelectedEmployer,
      createEmployer, refreshEmployers, authHeaders, API
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
