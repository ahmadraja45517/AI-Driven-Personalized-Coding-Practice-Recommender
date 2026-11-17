import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import apiClient from '../api/client';
import { SectionDetail as SectionDetailType, LearningItem } from '../types';
import { ArrowLeft, ExternalLink, BookOpen, Code } from 'lucide-react';

export default function SectionDetail() {
  const { id } = useParams();
  const [data, setData] = useState<SectionDetailType | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiClient.get(`/sections/${id}`).then(res => {
      setData(res.data);
    }).catch(err => {
      console.error(err);
      // Typically handle 403 Locked here
    }).finally(() => setLoading(false));
  }, [id]);

  const toggleProgress = async (item: LearningItem) => {
    if (!data) return;
    // Optimistic UI update
    const newItems = data.items.map(i => 
      i.id === item.id ? { ...i, is_completed: !i.is_completed } : i
    );
    setData({ ...data, items: newItems });

    try {
      await apiClient.patch(`/progress/${item.id}`, { is_completed: !item.is_completed });
    } catch (err) {
      // Revert on failure
      setData(data);
      alert('Failed to update progress');
    }
  };

  if (loading) return <div className="text-slate-400">Loading section...</div>;
  if (!data) return <div className="text-red-400">Failed to load section. It may be locked.</div>;

  return (
    <div className="max-w-4xl mx-auto">
      <Link to="/roadmap" className="inline-flex items-center text-slate-400 hover:text-white mb-6 transition-colors">
        <ArrowLeft size={16} className="mr-2" />
        Back to Roadmap
      </Link>

      <header className="mb-8">
        <h1 className="text-3xl font-bold text-white mb-2">{data.title}</h1>
        <p className="text-slate-400">{data.description}</p>
      </header>

      <div className="space-y-4">
        {data.items.map((item) => (
          <div key={item.id} className="bg-slate-800 border border-slate-700 rounded-xl p-5 flex items-start space-x-4 transition-colors hover:border-slate-600">
            
            {/* Checkbox (Self-reported) */}
            <div className="pt-1">
              <input 
                type="checkbox" 
                checked={item.is_completed}
                onChange={() => toggleProgress(item)}
                className="w-5 h-5 rounded border-slate-600 text-brand-500 focus:ring-brand-500 focus:ring-offset-slate-800 bg-slate-900 cursor-pointer"
              />
            </div>

            <div className="flex-1">
              <div className="flex justify-between items-start">
                <div>
                  <h3 className={`font-semibold text-lg ${item.is_completed ? 'text-slate-500 line-through' : 'text-white'}`}>
                    {item.title}
                  </h3>
                  <div className="flex items-center space-x-3 mt-2 text-sm text-slate-400">
                    {item.kind === 'LESSON' ? <BookOpen size={16} /> : <Code size={16} />}
                    <span className="capitalize">{item.kind.replace('_', ' ').toLowerCase()}</span>
                    {item.difficulty && (
                      <span className={`px-2 py-0.5 rounded text-xs font-medium
                        ${item.difficulty === 'EASY' ? 'bg-green-900/50 text-green-400' : 
                          item.difficulty === 'MEDIUM' ? 'bg-yellow-900/50 text-yellow-400' : 
                          'bg-red-900/50 text-red-400'}`}>
                        {item.difficulty}
                      </span>
                    )}
                  </div>
                </div>

                {item.external_url && (
                  <a href={item.external_url} target="_blank" rel="noopener noreferrer"
                     className="flex items-center space-x-1 text-brand-400 hover:text-brand-300 text-sm font-medium bg-brand-900/30 px-3 py-1.5 rounded-lg border border-brand-800/50">
                    <span>Solve on LeetCode</span>
                    <ExternalLink size={14} />
                  </a>
                )}
              </div>

              {item.kind === 'LESSON' && item.content_md && (
                <div className="mt-4 p-4 bg-slate-900 rounded-lg text-sm text-slate-300">
                  {/* In a real app, you would use React Markdown here */}
                  {item.content_md}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}