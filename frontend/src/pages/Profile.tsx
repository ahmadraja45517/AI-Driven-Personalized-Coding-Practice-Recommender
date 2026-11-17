import { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import apiClient from '../api/client';
import { User, Mail, BookOpen, GraduationCap } from 'lucide-react';

export default function Profile() {
  const { user, refreshProfile } = useAuth();
  const [editing, setEditing] = useState(false);
  const [language, setLanguage] = useState(user?.preferred_language || 'PYTHON');
  const [loading, setLoading] = useState(false);

  const handleSave = async () => {
    setLoading(true);
    try {
      await apiClient.put('/profile', { preferred_language: language });
      await refreshProfile();
      setEditing(false);
    } catch (err) {
      alert('Failed to update profile');
    } finally {
      setLoading(false);
    }
  };

  if (!user) return null;

  return (
    <div className="max-w-3xl mx-auto">
      <h1 className="text-3xl font-bold text-white mb-8">Your Profile</h1>
      
      <div className="bg-slate-800 rounded-xl border border-slate-700 p-8">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          
          <div className="space-y-6">
            <div className="flex items-start space-x-4">
              <User className="text-slate-400 mt-1" />
              <div>
                <p className="text-sm text-slate-400">Full Name</p>
                <p className="text-lg font-medium text-white">{user.full_name}</p>
              </div>
            </div>

            <div className="flex items-start space-x-4">
              <Mail className="text-slate-400 mt-1" />
              <div>
                <p className="text-sm text-slate-400">Email</p>
                <p className="text-lg font-medium text-white">{user.email}</p>
              </div>
            </div>

            <div className="flex items-start space-x-4">
              <BookOpen className="text-slate-400 mt-1" />
              <div>
                <p className="text-sm text-slate-400">Course</p>
                <p className="text-lg font-medium text-white">{user.course}</p>
              </div>
            </div>

            <div className="flex items-start space-x-4">
              <GraduationCap className="text-slate-400 mt-1" />
              <div>
                <p className="text-sm text-slate-400">Academic Year</p>
                <p className="text-lg font-medium text-white">Year {user.academic_year}</p>
              </div>
            </div>
          </div>

          <div className="bg-slate-900 rounded-xl p-6 border border-slate-700/50">
            <h2 className="text-lg font-bold text-white mb-4">Preferences</h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-400 mb-1">Preferred Language</label>
                {editing ? (
                  <select 
                    value={language} 
                    onChange={e => setLanguage(e.target.value as any)}
                    className="w-full bg-slate-800 border border-slate-600 text-white rounded-lg px-4 py-2 outline-none focus:border-brand-500"
                  >
                    <option value="JAVA">Java</option>
                    <option value="CPP">C++</option>
                    <option value="PYTHON">Python</option>
                  </select>
                ) : (
                  <p className="text-white font-medium">{user.preferred_language || 'Not set'}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-400 mb-1">Selected Skill Level</label>
                <p className="text-white font-medium">{user.selected_level || 'Not set'}</p>
                <p className="text-xs text-slate-500 mt-1">Contact support to change your selected track.</p>
              </div>
            </div>

            <div className="mt-8 pt-6 border-t border-slate-700/50">
              {editing ? (
                <div className="flex space-x-3">
                  <button onClick={handleSave} disabled={loading} className="bg-brand-600 hover:bg-brand-500 text-white px-4 py-2 rounded-lg font-medium transition-colors">
                    {loading ? 'Saving...' : 'Save Changes'}
                  </button>
                  <button onClick={() => setEditing(false)} className="bg-slate-700 hover:bg-slate-600 text-white px-4 py-2 rounded-lg font-medium transition-colors">
                    Cancel
                  </button>
                </div>
              ) : (
                <button onClick={() => setEditing(true)} className="text-brand-400 hover:text-brand-300 font-medium">
                  Edit Preferences
                </button>
              )}
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}