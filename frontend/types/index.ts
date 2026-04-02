export interface Project {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface PersonaGroup {
  id: string;
  project_id: string;
  name: string;
  description: string | null;
  age_min: number;
  age_max: number;
  gender: string;
  location: string;
  occupation: string;
  income_level: string;
  psychographic_notes: string | null;
  persona_count: number;
  generation_status: "pending" | "generating" | "complete" | "failed";
  generation_progress: {
    current: number;
    total: number;
    current_name: string | null;
    completed: string[];
  } | null;
  created_at: string;
  updated_at: string;
}

export interface Persona {
  id: string;
  persona_group_id: string;
  full_name: string;
  age: number;
  gender: string;
  location: string;
  occupation: string;
  income_level: string;
  educational_background: string | null;
  family_situation: string | null;
  personality_traits: string[] | null;
  values_and_motivations: string | null;
  pain_points: string | null;
  media_consumption: string | null;
  purchase_behavior: string | null;
  archetype_label: string | null;
  psychographic_segment: string | null;
  brand_attitudes: string | null;
  buying_triggers: string | null;
  aspirational_identity: string | null;
  digital_behavior: string | null;
  day_in_the_life: string | null;
  persona_code: string;
  data_source: string | null;
  data_source_references: string[] | null;
  library_persona_id: string | null;
  created_at: string;
}

export interface LibraryPersona {
  id: string;
  full_name: string;
  age: number;
  gender: string;
  location: string;
  occupation: string;
  income_level: string;
  educational_background: string | null;
  family_situation: string | null;
  background: string | null;
  personality_traits: string[] | null;
  goals: string | null;
  pain_points: string | null;
  tech_savviness: string | null;
  media_consumption: string | null;
  spending_habits: string | null;
  archetype_label: string | null;
  psychographic_segment: string | null;
  brand_attitudes: string | null;
  buying_triggers: string | null;
  aspirational_identity: string | null;
  digital_behavior: string | null;
  day_in_the_life: string | null;
  data_source: string;
  data_source_references: string[] | null;
  simulation_count: number;
  is_retired: boolean;
  created_at: string;
  updated_at: string;
}

export interface LibraryPersonaListResponse {
  items: LibraryPersona[];
  total: number;
  limit: number;
  offset: number;
}

export interface Briefing {
  id: string;
  project_id: string;
  title: string;
  description: string | null;
  file_name: string;
  file_type: "pdf" | "image" | "text";
  extracted_text: string | null;
  created_at: string;
}

export interface SurveyQuestion {
  id: string;
  type: "likert" | "multiple_choice" | "open_ended";
  text: string;
  scale?: number;
  low_label?: string;
  high_label?: string;
  options?: string[];
}

export interface SurveySchema {
  questions: SurveyQuestion[];
}

export interface Simulation {
  id: string;
  project_id: string;
  persona_group_id: string;
  briefing_id: string | null;
  prompt_question: string | null;
  simulation_type: "concept_test" | "idi_ai" | "idi_manual" | "survey" | "focus_group" | "conjoint";
  idi_script_text: string | null;
  idi_persona_id: string | null;
  survey_schema: SurveySchema | null;
  status: "pending" | "running" | "active" | "generating_report" | "complete" | "failed";
  error_message: string | null;
  progress: {
    current: number;
    total: number;
    current_name: string | null;
    completed: string[];
    failed: string[];
    stage: "interviewing" | "round_1" | "moderator_bridge" | "round_2" | "choice_tasks" | "generating_report";
  } | null;
  created_at: string;
  completed_at: string | null;
}

export interface SimulationResult {
  id: string;
  simulation_id: string;
  persona_id: string | null;
  result_type: "individual" | "aggregate" | "idi_individual" | "idi_aggregate" | "survey_individual" | "survey_aggregate" | "focus_group_individual" | "focus_group_aggregate" | "conjoint_individual" | "conjoint_aggregate";
  // Concept test individual fields
  sentiment: "Positive" | "Neutral" | "Negative" | null;
  sentiment_score: number | null;
  reaction_text: string | null;
  key_themes: string[] | null;
  notable_quote: string | null;
  // Concept test aggregate fields
  summary_text: string | null;
  sentiment_distribution: Record<string, number> | null;
  top_themes: string[] | null;
  recommendations: string | null;
  // IDI / Survey fields
  transcript: string | null;
  report_sections: Record<string, unknown> | null;
  created_at: string;
}

export interface ConjointAttribute {
  name: string;
  levels: string[];
}

export interface ConjointDesign {
  attributes: ConjointAttribute[];
  n_tasks: number;
}

export interface ConjointTaskResult {
  task_index: number;
  profile_a: Record<string, string>;
  profile_b: Record<string, string>;
  chosen: "A" | "B";
  reasoning: string;
}

export interface ConjointIndividualSections {
  tasks: ConjointTaskResult[];
  attribute_importances: Record<string, number>;
  part_worths: Record<string, Record<string, number>>;
  top_driver: string;
}

export interface ConjointMarketShare {
  profiles_tested: Array<{ name: string; attributes: Record<string, string> }>;
  shares: Record<string, number>;
}

export interface ConjointAggregateSections {
  attribute_importances: Record<string, number>;
  part_worths: Record<string, Record<string, number>>;
  market_share_simulation: ConjointMarketShare;
  persona_segments: Array<{ label: string; persona_ids: string[]; top_driver: string }>;
  executive_summary: string;
  recommendations: string;
}

// ---------------------------------------------------------------------------
// Benchmarking types
// ---------------------------------------------------------------------------

export interface BenchmarkGroundTruth {
  sentiment: "Positive" | "Neutral" | "Negative";
  positive_pct?: number;
  neutral_pct?: number;
  negative_pct?: number;
  top_themes: string[];
  outcome_summary: string;
  source_notes?: string;
}

export interface BenchmarkCase {
  id: string;
  slug: string;
  title: string;
  category: string;
  description: string;
  briefing_text?: string;
  prompt_question?: string;
  simulation_type: string;
  ground_truth: BenchmarkGroundTruth;
  source_citations?: string[];
}

export interface BenchmarkRun {
  id: string;
  benchmark_case_id: string;
  benchmark_case_title: string | null;
  benchmark_case_slug: string | null;
  simulation_id: string;
  status: "pending" | "complete" | "failed";
  overall_accuracy_score: number | null;
  score_breakdown: Record<string, unknown> | null;
  created_at: string;
  completed_at: string | null;
}

export interface ReliabilityCheck {
  exists: boolean;
  id?: string;
  source_simulation_id?: string;
  n_runs?: number;
  status?: "pending" | "running" | "complete" | "failed";
  confidence_score?: number | null;
  sentiment_agreement_rate?: number | null;
  distribution_variance_score?: number | null;
  theme_overlap_coefficient?: number | null;
  score_breakdown?: Record<string, unknown> | null;
  created_at?: string;
  completed_at?: string | null;
}

export interface ConvergencePair {
  sim_a_id: string;
  sim_a_type: string;
  sim_b_id: string;
  sim_b_type: string;
  convergence_score: number;
  direction_match: boolean | null;
  distribution_similarity: number | null;
  theme_overlap: number;
  shared_themes: string[];
  diverging_themes: string[];
}

export interface ConvergenceResult {
  simulations_analysed: Array<{ simulation_id: string; simulation_type: string; completed_at: string | null }>;
  pairwise_convergence: ConvergencePair[];
  overall_convergence_score: number | null;
  interpretation: "strong" | "moderate" | "weak" | null;
  message?: string;
}

export interface IDIMessage {
  id: string;
  simulation_id: string;
  persona_id: string | null;
  role: "user" | "persona";
  content: string;
  created_at: string;
}
