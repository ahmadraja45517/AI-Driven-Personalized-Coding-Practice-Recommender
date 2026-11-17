export type PreferredLanguage = 'JAVA' | 'CPP' | 'PYTHON';
export type StudentLevel = 'BEGINNER' | 'INTERMEDIATE' | 'ADVANCED';

export interface Profile {
  id: number;
  full_name: string;
  email: string;
  course: string;
  academic_year: number;
  preferred_language: PreferredLanguage | null;
  selected_level: StudentLevel | null;
  onboarding_completed_at: string | null;
  demonstrated_level: StudentLevel | null;
  recommended_level: StudentLevel | null;
  level_recommendation: {
    show: boolean;
    recommended_level: StudentLevel | null;
    message: string | null;
  };
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface DashboardData {
  full_name: string;
  preferred_language: string | null;
  selected_level: string | null;
  demonstrated_level: string | null;
  progress: {
    total_items: number;
    completed_items: number;
    completion_ratio: number;
    unlocked_sections: number;
    completed_sections: number;
  };
  recommendations: any[];
}

export interface Section {
  id: number;
  slug: string;
  title: string;
  description: string | null;
  order_index: number;
  content_status: string;
  status: 'LOCKED' | 'UNLOCKED' | 'COMPLETED' | 'NOT_ENROLLED';
  progress: {
    items_total: number;
    items_completed: number;
    completion_ratio: number;
    requirements_met: boolean;
  } | null;
}

export interface LearningItem {
  id: number;
  title: string;
  kind: 'LESSON' | 'EXTERNAL_PROBLEM';
  source: 'INTERNAL' | 'LEETCODE';
  difficulty: 'EASY' | 'MEDIUM' | 'HARD' | null;
  content_md: string | null;
  external_url: string | null;
  is_completed: boolean;
}

export interface SectionDetail extends Section {
  items: LearningItem[];
}

export interface AssessmentSummary {
  id: number;
  kind: 'DIAGNOSTIC' | 'SECTION_END';
  title: string;
  description: string | null;
  target_level: string | null;
  section_id: number | null;
  total_marks: number;
  pass_ratio: number;
  duration_minutes: number | null;
  attempts_count: number;
  best_pct: number | null;
  latest_pct: number | null;
  passed: boolean;
}

export interface Question {
  id: number;
  order_index: number;
  topic: string;
  difficulty: string;
  text: string;
  marks: number;
  options: { id: number; order_index: number; text: string }[];
}

export interface AssessmentDetail extends AssessmentSummary {
  questions: Question[];
}

export interface AttemptResult {
  attempt_id: number;
  score_marks: number;
  total_marks: number;
  percentage: number;
  passed: boolean;
  topic_results: { topic: string; questions_total: number; questions_correct: number; accuracy: number }[];
  question_results: { question_id: number; is_correct: boolean; explanation: string; correct_option_id: number }[];
}

export interface Recommendation {
  id: number;
  kind: 'ACTIONABLE' | 'LOCKED_PREVIEW' | 'REVISION';
  status: string;
  score: number;
  weak_topic_score: number;
  difficulty_score: number;
  prerequisite_score: number;
  topic: string;
  section_id: number | null;
  section_title: string | null; // Added
  item_id: number | null;
  item_title: string | null;    // Added
  item_url: string | null;      // Added
  target_difficulty: string | null;
  reason: string;
}

export interface SkillTopic {
  topic: string;
  accuracy: number | null;
  evidence_count: number;
  target_difficulty: string | null;
  classification: string;
  trend: string;
}

export interface SkillProfile {
  profile_id: number;
  computed_at: string;
  demonstrated_level: string | null;
  recommended_level: string | null;
  overall_accuracy: number | null;
  evidence_count: number;
  topics: SkillTopic[];
}