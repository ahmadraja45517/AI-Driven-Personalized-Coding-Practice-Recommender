import { useEffect, useState } from 'react';
import apiClient from '../api/client';
import { SkillProfile } from '../types';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import { Award, Target } from 'lucide-react';

export default function Analytics() {
  const [skill, setSkill] = useState<SkillProfile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiClient.get('/skills').then(res => {
      setSkill(res.data);
    }).catch(err => {
      console.error("No skill profile yet", err);
    }).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="text-slate-400">Loading analytics...</div>;
  if (!skill) return (
    <div className="text-center mt-20">
      <Target size={48} className="mx-auto text-slate-500 mb-4" />
      <h2 className="text-xl font-bold text-white mb-2">No Analytics Available</h2>
      <p className="text-slate-400">Complete an assessment to generate your skill profile and analytics.</p>
    </div>
  );

  // Format data for Recharts
  const chartData = skill.topics
    .filter(t => t.accuracy !== null && t.evidence_count > 0)
    .map(t => ({
      name: t.topic.replace('_', ' ').toUpperCase(),
      accuracy: Math.round((t.accuracy || 0) * 100),
      fill: (t.accuracy || 0) >= 0.7 ? '#10b981' : (t.accuracy || 0) < 0.4 ? '#ef4444' : '#f59e0b'
    }));

  return (
    <div className="max-w-5xl mx-auto space-y-8">
      <header>
        <h1 className="text-3xl font-bold text-white mb-2">Analytics</h1>
        <p className="text-slate-400">Your performance across different DSA topics based on assessment data.</p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-slate-800 p-6 rounded-xl border border-slate-700">
          <div className="flex items-center space-x-3 mb-2">
            <Award className="text-brand-500" />
            <h3 className="font-semibold text-slate-300">Overall Accuracy</h3>
          </div>
          <p className="text-4xl font-bold text-white">{Math.round((skill.overall_accuracy || 0) * 100)}%</p>
        </div>
        
        <div className="bg-slate-800 p-6 rounded-xl border border-slate-700">
          <div className="flex items-center space-x-3 mb-2">
            <Target className="text-blue-500" />
            <h3 className="font-semibold text-slate-300">Demonstrated Level</h3>
          </div>
          <p className="text-2xl font-bold text-white">{skill.demonstrated_level}</p>
        </div>

        <div className="bg-slate-800 p-6 rounded-xl border border-slate-700">
          <h3 className="font-semibold text-slate-300 mb-1">Evidence Collected</h3>
          <p className="text-slate-400 text-sm mb-2">Questions answered in assessments</p>
          <p className="text-4xl font-bold text-white">{skill.evidence_count}</p>
        </div>
      </div>

      <div className="bg-slate-800 p-6 md:p-8 rounded-xl border border-slate-700">
        <h2 className="text-xl font-bold text-white mb-6">Topic-wise Accuracy</h2>
        <div className="h-80 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 20, right: 30, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
              <XAxis dataKey="name" stroke="#94a3b8" tick={{ fill: '#94a3b8', fontSize: 12 }} />
              <YAxis stroke="#94a3b8" tick={{ fill: '#94a3b8' }} domain={[0, 100]} />
              <Tooltip 
                cursor={{ fill: '#1e293b' }}
                contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', color: '#f8fafc' }}
              />
              <Bar dataKey="accuracy" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}