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
  day_in_the_life: string | null;
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

export interface Simulation {
  id: string;
  project_id: string;
  persona_group_id: string;
  briefing_id: string;
  prompt_question: string;
  status: "pending" | "running" | "complete" | "failed";
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface SimulationResult {
  id: string;
  simulation_id: string;
  persona_id: string | null;
  result_type: "individual" | "aggregate";
  // Individual fields
  sentiment: "Positive" | "Neutral" | "Negative" | null;
  sentiment_score: number | null;
  reaction_text: string | null;
  key_themes: string[] | null;
  notable_quote: string | null;
  // Aggregate fields
  summary_text: string | null;
  sentiment_distribution: Record<string, number> | null;
  top_themes: string[] | null;
  recommendations: string | null;
  created_at: string;
}
