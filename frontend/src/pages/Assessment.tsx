import { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import apiClient from '../api/client';
import { AssessmentDetail, AttemptResult } from '../types';
import { ArrowLeft, CheckCircle2, XCircle } from 'lucide-react';

export default function Assessment() {
  const { id } = useParams();
  
  const [assessment, setAssessment] = useState<AssessmentDetail | null>(null);
  const [answers, setAnswers] = useState<Record<number, number>>({});
  const [result, setResult] = useState<AttemptResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!id) {
      setError('No assessment ID provided.');
      setLoading(false);
      return;
    }

    apiClient.get(`/assessments/${id}`).then(res => {
      setAssessment(res.data);
    }).catch(err => {
      // Handle FastAPI 422 arrays or standard 400 strings
      const detail = err.response?.data?.detail;
      if (typeof detail === 'string') {
        setError(detail);
      } else if (Array.isArray(detail)) {
        setError(detail.map((d: any) => d.msg).join(', '));
      } else {
        setError('Failed to load assessment. It may not exist.');
      }
    }).finally(() => setLoading(false));
  }, [id]);

  const handleSelect = (questionId: number, optionId: number) => {
    if (result) return; 
    setAnswers(prev => ({ ...prev, [questionId]: optionId }));
  };

  const handleSubmit = async () => {
    if (!assessment) return;

    setSubmitting(true);
    const payload = {
      answers: Object.entries(answers).map(([qId, oId]) => ({
        question_id: parseInt(qId),
        option_id: oId
      }))
    };

    try {
      const { data } = await apiClient.post<AttemptResult>(`/assessments/${id}/submit`, payload);
      setResult(data);
      window.scrollTo(0, 0);
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      alert(typeof detail === 'string' ? detail : 'Submission failed.');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <div className="text-slate-400 p-8">Loading questions...</div>;
  
  if (error) {
    return (
      <div className="max-w-4xl mx-auto p-8">
        <div className="text-red-400 p-4 bg-red-900/20 rounded-lg border border-red-800">
          <strong>Error:</strong> {error}
        </div>
        <Link to="/dashboard" className="inline-flex items-center text-slate-400 hover:text-white mt-4">
          <ArrowLeft size={16} className="mr-2" /> Back to Dashboard
        </Link>
      </div>
    );
  }

  if (!assessment) return null;

  const totalQuestions = assessment.questions.length;
  const answeredCount = Object.keys(answers).length;
  const isComplete = answeredCount === totalQuestions;

  // --- RESULTS VIEW ---
  if (result) {
    return (
      <div className="max-w-4xl mx-auto pb-12">
        <Link to="/dashboard" className="inline-flex items-center text-slate-400 hover:text-white mb-6">
          <ArrowLeft size={16} className="mr-2" /> Back to Dashboard
        </Link>
        
        <div className={`p-8 rounded-2xl border mb-8 ${result.passed ? 'bg-brand-900/20 border-brand-800' : 'bg-red-900/20 border-red-800'}`}>
          <h1 className="text-3xl font-bold text-white mb-2">
            {result.passed ? 'Assessment Passed!' : 'Needs Improvement'}
          </h1>
          <div className="flex items-end space-x-4 mb-6">
            <span className="text-5xl font-bold text-white">{result.percentage}%</span>
            <span className="text-slate-400 pb-2">({result.score_marks} / {result.total_marks} Marks)</span>
          </div>
          
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
            {result.topic_results.map(t => (
              <div key={t.topic} className="bg-slate-900/50 p-4 rounded-lg border border-slate-700/50">
                <p className="text-sm text-slate-400 capitalize">{t.topic.replace('_', ' ')}</p>
                <p className="text-xl font-bold text-white mt-1">{Math.round(t.accuracy * 100)}%</p>
              </div>
            ))}
          </div>
        </div>

        <h2 className="text-2xl font-bold text-white mb-4">Detailed Review</h2>
        <div className="space-y-6">
          {assessment.questions.map((q, index) => {
            const res = result.question_results.find(r => r.question_id === q.id);
            if (!res) return null;

            return (
              <div key={q.id} className="bg-slate-800 rounded-xl border border-slate-700 p-6">
                <div className="flex items-start space-x-3 mb-4">
                  {res.is_correct ? <CheckCircle2 className="text-brand-500 mt-1 shrink-0" /> : <XCircle className="text-red-500 mt-1 shrink-0" />}
                  <div>
                    <h3 className="text-lg font-medium text-white">{index + 1}. {q.text}</h3>
                    <p className="text-sm text-slate-400 mt-1 capitalize">{q.topic.replace('_', ' ')} • {q.difficulty}</p>
                  </div>
                </div>
                
                <div className="space-y-2 ml-9">
                  {q.options.map(opt => {
                    const isSelected = answers[q.id] === opt.id;
                    const isCorrect = res.correct_option_id === opt.id;
                    return (
                      <div key={opt.id} className={`p-3 rounded-lg border text-sm
                        ${isCorrect ? 'bg-brand-900/30 border-brand-700 text-brand-200' : 
                          isSelected && !isCorrect ? 'bg-red-900/30 border-red-700 text-red-200' : 
                          'bg-slate-900 border-slate-700 text-slate-400'}`}>
                        {opt.text}
                        {isCorrect && <span className="ml-2 font-bold text-brand-400">(Correct)</span>}
                        {isSelected && !isCorrect && <span className="ml-2 font-bold text-red-400">(Your Answer)</span>}
                      </div>
                    );
                  })}
                </div>
                <div className="mt-4 ml-9 p-4 bg-slate-900/50 rounded-lg text-sm text-slate-300 border border-slate-700/50">
                  <span className="font-semibold text-white">Explanation: </span>
                  {res.explanation}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  }

  // --- TEST TAKING VIEW ---
  return (
    <div className="max-w-4xl mx-auto pb-24">
      <div className="mb-8 flex justify-between items-end border-b border-slate-800 pb-6">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">{assessment.title}</h1>
          <p className="text-slate-400">{assessment.description}</p>
        </div>
        <div className="text-right">
          <p className="text-sm text-slate-400 mb-1">Questions Answered</p>
          <p className="text-2xl font-bold text-white">{answeredCount} / {totalQuestions}</p>
        </div>
      </div>

      <div className="space-y-8">
        {assessment.questions.map((q, index) => (
          <div key={q.id} className="bg-slate-800 rounded-xl border border-slate-700 p-6">
            <h3 className="text-lg font-medium text-white mb-1">{index + 1}. {q.text}</h3>
            <div className="flex space-x-3 text-xs text-slate-400 mb-4">
              <span className="capitalize">{q.topic.replace('_', ' ')}</span>
              <span>•</span>
              <span className="capitalize">{q.difficulty}</span>
            </div>
            
            <div className="space-y-3">
              {q.options.map(opt => (
                <div 
                  key={opt.id} 
                  onClick={() => handleSelect(q.id, opt.id)}
                  className={`p-4 rounded-lg border-2 cursor-pointer transition-all text-sm
                    ${answers[q.id] === opt.id 
                      ? 'border-brand-500 bg-brand-900/20 text-white' 
                      : 'border-slate-700 hover:border-slate-500 bg-slate-900 text-slate-300'}`}
                >
                  {opt.text}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Sticky Bottom Bar */}
      <div className="fixed bottom-0 left-0 md:left-72 right-0 bg-slate-950 border-t border-slate-800 p-4 flex justify-between items-center z-10">
        <div className="text-sm text-slate-400">
          {answeredCount} of {totalQuestions} answered
        </div>
        
        <div className="flex items-center space-x-4">
          {!isComplete && (
            <span className="text-sm text-yellow-500 font-medium hidden md:inline">
              Please answer all questions to submit.
            </span>
          )}
          <button 
            onClick={handleSubmit} 
            disabled={submitting || !isComplete}
            className="bg-brand-600 hover:bg-brand-500 text-white font-bold py-2 px-8 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {submitting ? 'Submitting...' : 'Submit Assessment'}
          </button>
        </div>
      </div>
    </div>
  );
}