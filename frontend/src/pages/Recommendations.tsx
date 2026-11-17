import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import apiClient from '../api/client';
import { Recommendation } from '../types';
import { Target, Lock, RefreshCw, ChevronRight, ExternalLink, Code } from 'lucide-react';

export default function Recommendations() {
  const [recs, setRecs] = useState<Recommendation[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchRecs = async () => {
    try {
      const { data } = await apiClient.get('/recommendations');
      setRecs(data.items);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchRecs();
  }, []);

  const handleRefresh = async () => {
    setRefreshing(true);
    await apiClient.post('/recommendations/refresh');
    await fetchRecs();
  };

  if (loading) return <div className="text-slate-400">Loading recommendations...</div>;

  const actionable = recs.filter(r => r.kind === 'ACTIONABLE');
  const locked = recs.filter(r => r.kind === 'LOCKED_PREVIEW');
  const revision = recs.filter(r => r.kind === 'REVISION');

  return (
    <div className="max-w-5xl mx-auto">
      <div className="flex justify-between items-end mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Personalized Recommendations</h1>
          <p className="text-slate-400">Practice problems tailored to your skill profile.</p>
        </div>
        <button 
          onClick={handleRefresh} 
          disabled={refreshing}
          className="flex items-center space-x-2 bg-slate-800 hover:bg-slate-700 text-white px-4 py-2 rounded-lg border border-slate-700 transition-colors disabled:opacity-50"
        >
          <RefreshCw size={16} className={refreshing ? 'animate-spin' : ''} />
          <span>{refreshing ? 'Refreshing...' : 'Refresh'}</span>
        </button>
      </div>

      {recs.length === 0 ? (
        <div className="bg-slate-800 p-8 rounded-xl border border-slate-700 text-center">
          <Target size={48} className="mx-auto text-slate-500 mb-4" />
          <h2 className="text-xl font-bold text-white mb-2">No recommendations yet</h2>
          <p className="text-slate-400 mb-6">Take a diagnostic assessment to generate personalized recommendations.</p>
          <Link to="/dashboard" className="text-brand-400 hover:underline">Go to Dashboard</Link>
        </div>
      ) : (
        <div className="space-y-8">
          {/* Actionable */}
          {actionable.length > 0 && (
            <section>
              <h2 className="text-xl font-bold text-white mb-4 flex items-center space-x-2">
                <Target className="text-brand-500" />
                <span>Practice Now</span>
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {actionable.map(rec => (
                  <div key={rec.id} className="bg-slate-800 p-5 rounded-xl border border-slate-700 hover:border-brand-500/50 transition-colors flex flex-col justify-between">
                    <div>
                      <div className="flex justify-between items-start mb-3">
                        <div className="flex items-center space-x-2">
                          <Code size={18} className="text-brand-400" />
                          <h3 className="font-semibold text-white">{rec.item_title || rec.section_title || 'Practice'}</h3>
                        </div>
                        <span className="text-xs font-bold text-brand-400 uppercase tracking-wide bg-brand-900/30 px-2 py-1 rounded">
                          Actionable
                        </span>
                      </div>
                      <p className="text-sm text-slate-400 mb-4">{rec.reason}</p>
                    </div>
                    <div className="flex justify-between items-center mt-2 pt-4 border-t border-slate-700/50">
                      <span className="text-xs text-slate-500 capitalize">{rec.topic.replace('_', ' ')} • {rec.target_difficulty}</span>
                      {rec.item_url && (
                        <a href={rec.item_url} target="_blank" rel="noopener noreferrer" className="text-brand-400 text-sm font-medium flex items-center hover:underline">
                          Solve on LeetCode <ExternalLink size={14} className="ml-1.5" />
                        </a>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Revision */}
          {revision.length > 0 && (
            <section>
              <h2 className="text-xl font-bold text-white mb-4 flex items-center space-x-2">
                <RefreshCw className="text-blue-400" />
                <span>Review & Reinforce</span>
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {revision.map(rec => (
                  <div key={rec.id} className="bg-slate-800 p-5 rounded-xl border border-slate-700 flex flex-col justify-between">
                    <div>
                      <div className="flex justify-between items-start mb-3">
                        <div className="flex items-center space-x-2">
                          <Code size={18} className="text-blue-400" />
                          <h3 className="font-semibold text-white">{rec.item_title}</h3>
                        </div>
                        <span className="text-xs font-bold text-blue-400 uppercase tracking-wide bg-blue-900/30 px-2 py-1 rounded">
                          Revision
                        </span>
                      </div>
                      <p className="text-sm text-slate-400 mb-4">{rec.reason}</p>
                    </div>
                    <div className="flex justify-between items-center mt-2 pt-4 border-t border-slate-700/50">
                      <span className="text-xs text-slate-500 capitalize">{rec.topic.replace('_', ' ')}</span>
                      {rec.item_url && (
                        <a href={rec.item_url} target="_blank" rel="noopener noreferrer" className="text-blue-400 text-sm font-medium flex items-center hover:underline">
                          Solve Again <ExternalLink size={14} className="ml-1.5" />
                        </a>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Locked */}
          {locked.length > 0 && (
            <section>
              <h2 className="text-xl font-bold text-white mb-4 flex items-center space-x-2">
                <Lock className="text-slate-400" />
                <span>Locked Content</span>
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {locked.map(rec => (
                  <div key={rec.id} className="bg-slate-800/50 p-5 rounded-xl border border-slate-700/50 opacity-80 flex flex-col justify-between">
                    <div>
                      <div className="flex justify-between items-start mb-3">
                        <div className="flex items-center space-x-2">
                          <Lock size={18} className="text-slate-500" />
                          <h3 className="font-semibold text-slate-300">{rec.section_title || rec.item_title || 'Upcoming Content'}</h3>
                        </div>
                        <span className="text-xs font-bold text-slate-400 uppercase tracking-wide bg-slate-900 px-2 py-1 rounded">
                          Locked
                        </span>
                      </div>
                      <p className="text-sm text-slate-500 mb-4">{rec.reason}</p>
                    </div>
                    <div className="flex justify-between items-center mt-2 pt-4 border-t border-slate-700/50">
                      <span className="text-xs text-slate-600 capitalize">{rec.topic.replace('_', ' ')}</span>
                      <Link to="/roadmap" className="text-slate-400 text-sm font-medium flex items-center hover:text-white transition-colors">
                        View Roadmap <ChevronRight size={14} className="ml-1" />
                      </Link>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>
      )}
    </div>
  );
}