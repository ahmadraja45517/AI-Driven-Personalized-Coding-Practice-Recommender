import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import apiClient from '../api/client';
import { DashboardData, AssessmentSummary } from '../types';
import { BookOpen, Award, CheckCircle, Lightbulb, FileText, ChevronRight, ExternalLink, Code } from 'lucide-react';

export default function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [assessments, setAssessments] = useState<AssessmentSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      apiClient.get('/dashboard'),
      apiClient.get('/assessments')
    ]).then(([dashRes, assessRes]) => {
      setData(dashRes.data);
      setAssessments(assessRes.data);
    }).catch(err => {
      console.error("Failed to load dashboard", err);
    }).finally(() => {
      setLoading(false);
    });
  }, []);

  if (loading) return <div className="animate-pulse text-slate-400">Loading dashboard...</div>;
  if (!data) return <div className="text-red-400">Failed to load data.</div>;

  return (
    <div className="space-y-6">
      <header className="mb-8">
        <h1 className="text-3xl font-bold text-white">Welcome, {data.full_name}!</h1>
        <p className="text-slate-400 mt-1">Here is a summary of your learning journey so far.</p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-slate-800 p-6 rounded-xl border border-slate-700">
          <div className="flex items-center space-x-3 mb-4">
            <BookOpen className="text-brand-500" />
            <h3 className="font-semibold text-slate-300">Overall Progress</h3>
          </div>
          <div className="text-3xl font-bold text-white">
            {Math.round(data.progress.completion_ratio * 100)}%
          </div>
          <p className="text-sm text-slate-400 mt-2">
            {data.progress.completed_items} of {data.progress.total_items} items completed
          </p>
        </div>
        
        <div className="bg-slate-800 p-6 rounded-xl border border-slate-700">
          <div className="flex items-center space-x-3 mb-4">
            <Award className="text-blue-500" />
            <h3 className="font-semibold text-slate-300">Skill Profile</h3>
          </div>
          <div className="text-lg text-slate-300 font-medium">
            Self: <span className="text-slate-400">{data.selected_level || 'N/A'}</span>
          </div>
          <div className="text-lg text-slate-300 font-medium mt-1">
            Demonstrated: <span className="text-blue-400 font-bold">{data.demonstrated_level || 'Not Assessed'}</span>
          </div>
        </div>

        <div className="bg-slate-800 p-6 rounded-xl border border-slate-700">
          <div className="flex items-center space-x-3 mb-4">
            <CheckCircle className="text-brand-500" />
            <h3 className="font-semibold text-slate-300">Sections Unlocked</h3>
          </div>
          <div className="text-3xl font-bold text-white">
            {data.progress.unlocked_sections}
          </div>
          <p className="text-sm text-slate-400 mt-2">
            {data.progress.completed_sections} sections fully completed
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Assessments Widget */}
        <div className="bg-slate-800 p-6 rounded-xl border border-slate-700">
          <div className="flex items-center space-x-3 mb-4">
            <FileText className="text-purple-400" />
            <h3 className="text-xl font-semibold text-white">Assessments</h3>
          </div>
          {assessments.length === 0 ? (
            <p className="text-slate-400">No assessments available right now.</p>
          ) : (
            <div className="space-y-3">
              {assessments.map(a => (
                <Link key={a.id} to={`/assessment/${a.id}`} 
                      className="flex items-center justify-between p-4 bg-slate-900 rounded-lg hover:bg-slate-700 transition-colors group border border-slate-700">
                  <div>
                    <p className="font-medium text-white">{a.title}</p>
                    <p className="text-sm text-slate-400 mt-1">
                      {a.attempts_count > 0 ? `Best: ${a.best_pct}%` : 'Not attempted yet'}
                    </p>
                  </div>
                  <ChevronRight className="text-slate-500 group-hover:text-brand-400" />
                </Link>
              ))}
            </div>
          )}
        </div>

        {/* Recommendations Widget */}
        <div className="bg-slate-800 p-6 rounded-xl border border-slate-700">
          <div className="flex items-center space-x-3 mb-4">
            <Lightbulb className="text-yellow-400" />
            <h3 className="text-xl font-semibold text-white">Recommendations</h3>
          </div>
          {data.recommendations.length === 0 ? (
            <p className="text-slate-400">Take an assessment to generate personalized recommendations.</p>
          ) : (
            <ul className="space-y-3">
              {data.recommendations.slice(0, 3).map((rec: any) => (
                <li key={rec.id} className="p-4 bg-slate-900 rounded-lg border border-slate-700">
                  
                  {/* Title Row */}
                  <div className="flex justify-between items-start mb-2">
                    <div className="flex items-center space-x-2">
                      <Code size={16} className="text-brand-400" />
                      <p className="font-semibold text-white">
                        {rec.item_title || rec.section_title || 'Review Topic'}
                      </p>
                    </div>
                    <span className="text-xs font-bold text-brand-400 uppercase tracking-wide bg-brand-900/30 px-2 py-1 rounded">
                      {rec.kind.replace('_', ' ')}
                    </span>
                  </div>

                  {/* Reason text */}
                  <p className="text-sm text-slate-400 mt-2 mb-3">{rec.reason}</p>
                  
                  {/* Action Link */}
                  {rec.item_url && (
                    <a href={rec.item_url} target="_blank" rel="noopener noreferrer" 
                       className="inline-flex items-center text-brand-400 hover:text-brand-300 text-sm font-medium transition-colors">
                      Solve on LeetCode <ExternalLink size={14} className="ml-1.5" />
                    </a>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}