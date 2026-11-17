import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import apiClient from '../api/client';
import { Section } from '../types';
import { Lock, CheckCircle, PlayCircle } from 'lucide-react';

export default function Roadmap() {
  const [sections, setSections] = useState<Section[]>([]);
  const [enrolled, setEnrolled] = useState(false);
  const [loading, setLoading] = useState(true);

  const fetchSections = async () => {
    try {
      const { data } = await apiClient.get('/sections');
      setSections(data.sections);
      setEnrolled(data.enrolled);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSections();
  }, []);

  const handleEnroll = async () => {
    try {
      await apiClient.post('/roadmap/enroll', { level: 'BEGINNER' });
      fetchSections();
    } catch (err) {
      alert('Failed to enroll');
    }
  };

  if (loading) return <div className="text-slate-400">Loading roadmap...</div>;

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white mb-2">Learning Roadmap</h1>
        <p className="text-slate-400">Master Data Structures and Algorithms step by step.</p>
      </div>

      {!enrolled && (
        <div className="bg-slate-800 p-6 rounded-xl border border-slate-700 mb-8 flex justify-between items-center">
          <div>
            <h3 className="text-lg font-bold text-white">Start the Beginner Path</h3>
            <p className="text-slate-400 text-sm mt-1">Enroll to unlock the Fundamentals section and begin tracking your progress.</p>
          </div>
          <button onClick={handleEnroll} className="bg-brand-600 hover:bg-brand-500 text-white px-6 py-2 rounded-lg font-medium transition-colors">
            Enroll Now
          </button>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {sections.map((section) => {
          const isLocked = section.status === 'LOCKED' || section.status === 'NOT_ENROLLED';
          const isCompleted = section.status === 'COMPLETED';
          const isUnlocked = section.status === 'UNLOCKED';

          return (
            <div key={section.id} 
                 className={`relative bg-slate-800 rounded-xl border p-6 flex flex-col transition-all
                   ${isLocked ? 'border-slate-800 opacity-70' : 'border-slate-700 hover:border-brand-500/50 hover:shadow-[0_0_15px_rgba(16,185,129,0.1)]'}`}>
              
              <div className="flex justify-between items-start mb-4">
                <h3 className="text-xl font-bold text-white">{section.title}</h3>
                {isLocked && <Lock className="text-slate-500" size={20} />}
                {isCompleted && <CheckCircle className="text-brand-500" size={20} />}
              </div>
              
              <p className="text-slate-400 text-sm mb-6 flex-1">
                {section.description || 'Master this topic with curated practice problems.'}
              </p>

              {section.progress && !isLocked && (
                <div className="mb-4">
                  <div className="flex justify-between text-xs text-slate-400 mb-1">
                    <span>Progress</span>
                    <span>{Math.round(section.progress.completion_ratio * 100)}%</span>
                  </div>
                  <div className="w-full bg-slate-900 rounded-full h-2">
                    <div className="bg-brand-500 h-2 rounded-full" style={{ width: `${section.progress.completion_ratio * 100}%` }}></div>
                  </div>
                </div>
              )}

              {isLocked ? (
                <button disabled className="w-full bg-slate-900 text-slate-500 py-2 rounded-lg font-medium cursor-not-allowed">
                  Locked
                </button>
              ) : (
                <Link to={`/roadmap/${section.id}`} 
                      className="w-full flex items-center justify-center space-x-2 bg-slate-700 hover:bg-slate-600 text-white py-2 rounded-lg font-medium transition-colors">
                  <PlayCircle size={18} />
                  <span>{isCompleted ? 'Review Section' : 'Continue Learning'}</span>
                </Link>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}