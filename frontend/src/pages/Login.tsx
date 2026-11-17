import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import apiClient from '../api/client';
import { useAuth } from '../contexts/AuthContext';
import { AuthResponse } from '../types';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const { data } = await apiClient.post<AuthResponse>('/auth/login', { email, password });
      await login(data.access_token);
      navigate('/dashboard');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-slate-900">
      <div className="max-w-md w-full bg-slate-800 rounded-xl shadow-lg p-8 border border-slate-700">
        <h1 className="text-2xl font-bold text-center mb-6 text-white">Welcome Back</h1>
        {error && <div className="mb-4 p-3 bg-red-900/30 text-red-400 border border-red-800 rounded-lg text-sm">{error}</div>}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">Email</label>
            <input type="email" required value={email} onChange={e => setEmail(e.target.value)}
              className="w-full px-4 py-2 bg-slate-900 border border-slate-700 rounded-lg text-white focus:ring-2 focus:ring-brand-500 outline-none" />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">Password</label>
            <input type="password" required value={password} onChange={e => setPassword(e.target.value)}
              className="w-full px-4 py-2 bg-slate-900 border border-slate-700 rounded-lg text-white focus:ring-2 focus:ring-brand-500 outline-none" />
          </div>
          <button disabled={loading} type="submit"
            className="w-full bg-brand-600 hover:bg-brand-500 text-white font-medium py-2 rounded-lg transition-colors mt-2">
            {loading ? 'Logging in...' : 'Log In'}
          </button>
        </form>
        <p className="mt-4 text-center text-sm text-slate-400">
          Don't have an account? <Link to="/register" className="text-brand-400 font-medium hover:underline">Register</Link>
        </p>
      </div>
    </div>
  );
}