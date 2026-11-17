import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import apiClient from '../api/client';
import { useAuth } from '../contexts/AuthContext';
import { AuthResponse } from '../types';

export default function Register() {
  const [formData, setFormData] = useState({
    full_name: '', email: '', course: '', academic_year: 1,
    password: '', confirm_password: ''
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await apiClient.post('/auth/register', formData);
      const { data } = await apiClient.post<AuthResponse>('/auth/login', { email: formData.email, password: formData.password });
      await login(data.access_token);
      navigate('/onboarding');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Registration failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 py-12 bg-slate-900">
      <div className="max-w-md w-full bg-slate-800 rounded-xl shadow-lg p-8 border border-slate-700">
        <h1 className="text-2xl font-bold text-center mb-6 text-white">Create an Account</h1>
        {error && <div className="mb-4 p-3 bg-red-900/30 text-red-400 border border-red-800 rounded-lg text-sm">{error}</div>}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">Full Name</label>
            <input type="text" required value={formData.full_name} onChange={e => setFormData({...formData, full_name: e.target.value})}
              className="w-full px-4 py-2 bg-slate-900 border border-slate-700 rounded-lg text-white focus:ring-2 focus:ring-brand-500 outline-none" />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">Email</label>
            <input type="email" required value={formData.email} onChange={e => setFormData({...formData, email: e.target.value})}
              className="w-full px-4 py-2 bg-slate-900 border border-slate-700 rounded-lg text-white focus:ring-2 focus:ring-brand-500 outline-none" />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">Course</label>
              <input type="text" required value={formData.course} onChange={e => setFormData({...formData, course: e.target.value})}
                className="w-full px-4 py-2 bg-slate-900 border border-slate-700 rounded-lg text-white focus:ring-2 focus:ring-brand-500 outline-none" />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">Year</label>
              <input type="number" min="1" max="8" required value={formData.academic_year} onChange={e => setFormData({...formData, academic_year: parseInt(e.target.value)})}
                className="w-full px-4 py-2 bg-slate-900 border border-slate-700 rounded-lg text-white focus:ring-2 focus:ring-brand-500 outline-none" />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">Password</label>
            <input type="password" required value={formData.password} onChange={e => setFormData({...formData, password: e.target.value})}
              className="w-full px-4 py-2 bg-slate-900 border border-slate-700 rounded-lg text-white focus:ring-2 focus:ring-brand-500 outline-none" />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">Confirm Password</label>
            <input type="password" required value={formData.confirm_password} onChange={e => setFormData({...formData, confirm_password: e.target.value})}
              className="w-full px-4 py-2 bg-slate-900 border border-slate-700 rounded-lg text-white focus:ring-2 focus:ring-brand-500 outline-none" />
          </div>
          <button disabled={loading} type="submit"
            className="w-full bg-brand-600 hover:bg-brand-500 text-white font-medium py-2 rounded-lg transition-colors mt-2">
            {loading ? 'Creating...' : 'Register'}
          </button>
        </form>
        <p className="mt-4 text-center text-sm text-slate-400">
          Already have an account? <Link to="/login" className="text-brand-400 font-medium hover:underline">Log in</Link>
        </p>
      </div>
    </div>
  );
}