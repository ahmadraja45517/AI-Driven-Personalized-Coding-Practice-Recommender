import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import apiClient from '../api/client';
import { useAuth } from '../contexts/AuthContext';
import { PreferredLanguage, StudentLevel } from '../types';

const LANGUAGES: { id: PreferredLanguage; label: string }[] = [
  { id: 'JAVA', label: 'Java' },
  { id: 'CPP', label: 'C++' },
  { id: 'PYTHON', label: 'Python' },
];

const LEVELS: { id: StudentLevel; label: string; desc: string }[] = [
  { id: 'BEGINNER', label: 'Beginner', desc: 'Start with the fundamentals.' },
  { id: 'INTERMEDIATE', label: 'Intermediate', desc: 'Take a diagnostic to find gaps.' },
  { id: 'ADVANCED', label: 'Advanced', desc: 'Tackle hard algorithmic problems.' },
];

export default function Onboarding() {
  const { user, refreshProfile } = useAuth();
  const navigate = useNavigate();
  const [language, setLanguage] = useState<PreferredLanguage>('PYTHON');
  const [level, setLevel] = useState<StudentLevel>('BEGINNER');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (user?.onboarding_completed_at) navigate('/dashboard');
  }, [user, navigate]);

  const handleSubmit = async () => {
    setLoading(true);
    try {
      await apiClient.post('/onboarding', { preferred_language: language, selected_level: level });
      await refreshProfile();
      navigate('/dashboard');
    } catch (err) {
      alert('Failed to save onboarding.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 p-6 py-12">
      <div className="max-w-3xl mx-auto">
        <h1 className="text-3xl font-bold text-center mb-2 text-white">Set Up Your Profile</h1>
        <p className="text-center text-slate-400 mb-10">Tell us about your preferences so we can personalize your roadmap.</p>
        <div className="space-y-8">
          <div>
            <h2 className="text-xl font-semibold mb-4 text-slate-200">Preferred Language</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {LANGUAGES.map(l => (
                <div key={l.id} onClick={() => setLanguage(l.id)}
                  className={`p-4 rounded-xl border-2 cursor-pointer transition-all ${language === l.id ? 'border-brand-500 bg-slate-800' : 'border-slate-700 bg-slate-800/50 hover:border-slate-500'}`}>
                  <span className="font-medium text-white">{l.label}</span>
                </div>
              ))}
            </div>
          </div>
          <div>
            <h2 className="text-xl font-semibold mb-4 text-slate-200">Current Skill Level</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {LEVELS.map(l => (
                <div key={l.id} onClick={() => setLevel(l.id)}
                  className={`p-4 rounded-xl border-2 cursor-pointer transition-all ${level === l.id ? 'border-brand-500 bg-slate-800' : 'border-slate-700 bg-slate-800/50 hover:border-slate-500'}`}>
                  <div className="font-medium mb-1 text-white">{l.label}</div>
                  <div className="text-sm text-slate-400">{l.desc}</div>
                </div>
              ))}
            </div>
          </div>
          <button onClick={handleSubmit} disabled={loading}
            className="w-full bg-brand-600 hover:bg-brand-500 text-white font-semibold py-3 rounded-xl transition-colors">
            {loading ? 'Saving...' : 'Complete Setup'}
          </button>
        </div>
      </div>
    </div>
  );
}