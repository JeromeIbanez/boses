import type {
  Briefing,
  ConjointDesign,
  ConvergenceResult,
  IDIMessage,
  LibraryPersona,
  LibraryPersonaListResponse,
  Persona,
  PersonaGroup,
  Project,
  ReliabilityCheck,
  Simulation,
  SimulationResult,
} from "@/types";

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export class QuotaExceededError extends Error {
  code = "quota_exceeded";
  plan: string;
  limit: number;
  used: number;
  constructor(detail: { plan: string; limit: number; used: number; message: string }) {
    super(detail.message ?? "Simulation limit reached.");
    this.plan = detail.plan;
    this.limit = detail.limit;
    this.used = detail.used;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    if (res.status === 402 && body?.detail?.error === "quota_exceeded") {
      throw new QuotaExceededError(body.detail);
    }
    throw new Error(
      typeof body.detail === "string" ? body.detail : body.detail?.message ?? "Request failed"
    );
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

// Projects
export const getProjects = () => request<Project[]>("/projects");
export const getProject = (id: string) => request<Project>(`/projects/${id}`);
export const createProject = (body: { name: string; description?: string }) =>
  request<Project>("/projects", { method: "POST", body: JSON.stringify(body) });
export const deleteProject = (id: string) =>
  request<void>(`/projects/${id}`, { method: "DELETE" });

// Persona Groups
export const parsePersonaPrompt = (projectId: string, prompt: string) =>
  request<{
    name: string; age_min: number; age_max: number; gender: string;
    location: string; occupation: string; income_level: string;
    psychographic_notes: string; persona_count: number;
  }>(`/projects/${projectId}/persona-groups/parse-prompt`, {
    method: "POST",
    body: JSON.stringify({ prompt }),
  });
export const getPersonaGroups = (projectId: string) =>
  request<PersonaGroup[]>(`/projects/${projectId}/persona-groups`);
export const getPersonaGroup = (projectId: string, groupId: string) =>
  request<PersonaGroup>(`/projects/${projectId}/persona-groups/${groupId}`);
export const createPersonaGroup = (projectId: string, body: Partial<PersonaGroup>) =>
  request<PersonaGroup>(`/projects/${projectId}/persona-groups`, {
    method: "POST",
    body: JSON.stringify(body),
  });
export const generatePersonas = (projectId: string, groupId: string) =>
  request<{ status: string; persona_count: number }>(
    `/projects/${projectId}/persona-groups/${groupId}/generate`,
    { method: "POST" }
  );
export const deletePersonaGroup = (projectId: string, groupId: string) =>
  request<void>(`/projects/${projectId}/persona-groups/${groupId}`, { method: "DELETE" });

// Personas
export const getPersonas = (projectId: string, groupId: string) =>
  request<Persona[]>(`/projects/${projectId}/persona-groups/${groupId}/personas`);
export const getPersona = (projectId: string, groupId: string, personaId: string) =>
  request<Persona>(`/projects/${projectId}/persona-groups/${groupId}/personas/${personaId}`);
export const deletePersona = (projectId: string, groupId: string, personaId: string) =>
  request<void>(`/projects/${projectId}/persona-groups/${groupId}/personas/${personaId}`, { method: "DELETE" });
export const deleteAllPersonas = (projectId: string, groupId: string) =>
  request<void>(`/projects/${projectId}/persona-groups/${groupId}/personas`, { method: "DELETE" });

// Briefings
export const getBriefings = (projectId: string) =>
  request<Briefing[]>(`/projects/${projectId}/briefings`);
export const getBriefing = (projectId: string, briefingId: string) =>
  request<Briefing>(`/projects/${projectId}/briefings/${briefingId}`);
export const uploadBriefing = (projectId: string, formData: FormData) =>
  fetch(`${BASE}/projects/${projectId}/briefings`, {
    method: "POST",
    credentials: "include",
    body: formData,
  }).then((r) => {
    if (!r.ok) throw new Error("Upload failed");
    return r.json() as Promise<Briefing>;
  });
export const updateBriefing = (projectId: string, briefingId: string, body: { title: string; description?: string | null }) =>
  request<Briefing>(`/projects/${projectId}/briefings/${briefingId}`, { method: "PATCH", body: JSON.stringify(body) });
export const deleteBriefing = (projectId: string, briefingId: string) =>
  request<void>(`/projects/${projectId}/briefings/${briefingId}`, { method: "DELETE" });

// Simulations
export const getSimulations = (projectId: string) =>
  request<Simulation[]>(`/projects/${projectId}/simulations`);
export const getSimulation = (projectId: string, simId: string) =>
  request<Simulation>(`/projects/${projectId}/simulations/${simId}`);
export const createSimulation = (
  projectId: string,
  body: {
    simulation_type: string;
    persona_group_ids: string[];
    briefing_ids?: string[];
    prompt_question?: string | null;
    idi_script_text?: string | null;
    idi_persona_id?: string | null;
  }
) =>
  request<Simulation>(`/projects/${projectId}/simulations`, {
    method: "POST",
    body: JSON.stringify(body),
  });
export const uploadIDIScript = (projectId: string, simId: string, formData: FormData) =>
  fetch(`${BASE}/projects/${projectId}/simulations/${simId}/script`, {
    method: "POST",
    credentials: "include",
    body: formData,
  }).then(async r => {
    if (!r.ok) {
      const err = await r.json().catch(() => ({ detail: r.statusText }));
      throw new Error(err.detail || "Upload failed");
    }
    return r.json() as Promise<Simulation>;
  });
export const getSimulationResults = (projectId: string, simId: string) =>
  request<SimulationResult[]>(`/projects/${projectId}/simulations/${simId}/results`);
export const deleteSimulation = (projectId: string, simId: string) =>
  request<void>(`/projects/${projectId}/simulations/${simId}`, { method: "DELETE" });
export const getIDIMessages = (projectId: string, simId: string) =>
  request<IDIMessage[]>(`/projects/${projectId}/simulations/${simId}/messages`);
export const sendIDIMessage = (projectId: string, simId: string, content: string) =>
  request<IDIMessage>(`/projects/${projectId}/simulations/${simId}/messages`, {
    method: "POST",
    body: JSON.stringify({ content }),
  });
export const endIDISession = (projectId: string, simId: string) =>
  request<Simulation>(`/projects/${projectId}/simulations/${simId}/end`, { method: "POST" });
export const abortSimulation = (projectId: string, simId: string) =>
  request<Simulation>(`/projects/${projectId}/simulations/${simId}/abort`, { method: "POST" });
export const uploadSurveyFile = (projectId: string, simId: string, formData: FormData) =>
  fetch(`${BASE}/projects/${projectId}/simulations/${simId}/survey`, {
    method: "POST",
    credentials: "include",
    body: formData,
  }).then(async r => {
    if (!r.ok) {
      const err = await r.json().catch(() => ({ detail: r.statusText }));
      throw new Error(err.detail || "Upload failed");
    }
    return r.json() as Promise<Simulation>;
  });
export const runSurvey = (projectId: string, simId: string) =>
  request<Simulation>(`/projects/${projectId}/simulations/${simId}/run`, { method: "POST" });
export const runConjointDesign = (projectId: string, simId: string, design: ConjointDesign) =>
  request<Simulation>(`/projects/${projectId}/simulations/${simId}/conjoint-design`, {
    method: "POST",
    body: JSON.stringify(design),
  });

// Library
export const getLibraryPersonas = (params?: {
  location?: string;
  gender?: string;
  income_level?: string;
  age_min?: number;
  age_max?: number;
  occupation?: string;
  limit?: number;
  offset?: number;
}) => {
  const query = new URLSearchParams();
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== "") query.set(k, String(v));
    });
  }
  const qs = query.toString();
  return request<LibraryPersonaListResponse>(`/library/personas${qs ? `?${qs}` : ""}`);
};

export const getLibraryPersona = (id: string) =>
  request<LibraryPersona>(`/library/personas/${id}`);

export const deleteLibraryPersona = (id: string) =>
  request<void>(`/library/personas/${id}`, { method: "DELETE" });

export const deleteAllLibraryPersonas = () =>
  request<void>(`/library/personas`, { method: "DELETE" });

// Reliability check
export const createReliabilityCheck = (projectId: string, simId: string, nRuns = 3) =>
  request<ReliabilityCheck>(`/projects/${projectId}/simulations/${simId}/reliability-check`, {
    method: "POST",
    body: JSON.stringify({ n_runs: nRuns }),
  });
export const getReliabilityCheck = (projectId: string, simId: string) =>
  request<ReliabilityCheck>(`/projects/${projectId}/simulations/${simId}/reliability-check`);

// Prediction commitments
export interface PredictionOutcome {
  id: string;
  simulation_id: string;
  project_id: string;
  created_by_user_id: string | null;
  predicted_sentiment: string | null;
  predicted_themes: string[] | null;
  kpi_description: string;
  outcome_due_date: string;
  actual_outcome_description: string | null;
  directional_match: boolean | null;
  notes: string | null;
  status: "pending" | "received";
  created_at: string;
  updated_at: string;
}
export const getPredictionCommitment = (projectId: string, simId: string) =>
  request<PredictionOutcome | null>(`/projects/${projectId}/simulations/${simId}/prediction-commitment`);
export const createPredictionCommitment = (projectId: string, simId: string, body: {
  kpi_description: string;
  outcome_due_date: string;
  predicted_sentiment?: string | null;
  predicted_themes?: string[] | null;
}) =>
  request<PredictionOutcome>(`/projects/${projectId}/simulations/${simId}/prediction-commitment`, {
    method: "POST",
    body: JSON.stringify(body),
  });
export const updatePredictionCommitment = (projectId: string, simId: string, body: {
  actual_outcome_description?: string;
  directional_match?: boolean;
  notes?: string;
}) =>
  request<PredictionOutcome>(`/projects/${projectId}/simulations/${simId}/prediction-commitment`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });

// Cross-simulation convergence
export const getConvergence = (projectId: string, personaGroupId: string, briefingId?: string | null) => {
  const qs = new URLSearchParams({ persona_group_id: personaGroupId });
  if (briefingId) qs.set("briefing_id", briefingId);
  return request<ConvergenceResult>(`/projects/${projectId}/simulations/convergence?${qs}`);
};

// Settings
export const getCompanySettings = () => request<{ id: string; name: string; slug: string; slack_webhook_url: string | null; created_at: string }>("/settings/company");
export const updateCompanySettings = (body: { name?: string; slack_webhook_url?: string | null }) => request<{ id: string; name: string; slug: string; slack_webhook_url: string | null; created_at: string }>("/settings/company", { method: "PATCH", body: JSON.stringify(body) });
export const updateNotificationPrefs = (email_notifications: boolean) => request<void>("/settings/notifications", { method: "PATCH", body: JSON.stringify({ email_notifications }) });

// Simulation Ratings
export interface SimulationRating { id: string; rating: number; feedback: string | null; created_at: string; }
export const getSimulationRating = (projectId: string, simulationId: string) => request<SimulationRating>(`/projects/${projectId}/simulations/${simulationId}/rating`);
export const rateSimulation = (projectId: string, simulationId: string, rating: number, feedback?: string) => request<SimulationRating>(`/projects/${projectId}/simulations/${simulationId}/rating`, { method: "POST", body: JSON.stringify({ rating, feedback: feedback ?? null }) });


// Admin — Boses-curated personas (staff only)
export interface AdminPersonaListResponse {
  items: LibraryPersona[];
  total: number;
  limit: number;
  offset: number;
}

export const getAdminPersonas = (params?: {
  curated_only?: boolean;
  source_type?: string;
  location?: string;
  is_retired?: boolean;
  limit?: number;
  offset?: number;
}) => {
  const query = new URLSearchParams();
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== "") query.set(k, String(v));
    });
  }
  const qs = query.toString();
  return request<{ items: LibraryPersona[]; total: number; limit: number; offset: number }>(
    `/admin/personas${qs ? `?${qs}` : ""}`
  );
};

export const getAdminPersona = (id: string) =>
  request<LibraryPersona>(`/admin/personas/${id}`);

export const createAdminPersona = (body: Partial<LibraryPersona> & {
  full_name: string; age: number; gender: string; location: string; occupation: string; income_level: string;
}) =>
  request<LibraryPersona>("/admin/personas", { method: "POST", body: JSON.stringify(body) });

export const updateAdminPersona = (id: string, body: Partial<LibraryPersona>) =>
  request<LibraryPersona>(`/admin/personas/${id}`, { method: "PATCH", body: JSON.stringify(body) });

export const retireAdminPersona = (id: string) =>
  request<void>(`/admin/personas/${id}`, { method: "DELETE" });

export const regenerateAdminAvatar = (id: string) =>
  request<LibraryPersona>(`/admin/personas/${id}/avatar`, { method: "POST" });

export const generateAdminPersonaFromNotes = (body: {
  full_name: string;
  age: number;
  gender: string;
  location: string;
  occupation: string;
  income_level: string;
  research_notes: string;
  source_type?: string;
}) =>
  request<LibraryPersona>("/admin/personas/generate", { method: "POST", body: JSON.stringify(body) });

// Admin — Invites
export interface Invite {
  id: string;
  email: string;
  status: "pending" | "used" | "expired";
  invite_url: string;
  created_at: string;
  expires_at: string;
  used_at: string | null;
}

export const getAdminInvites = () =>
  request<{ items: Invite[]; total: number }>("/admin/invites");

export const createAdminInvite = (email: string) =>
  request<Invite>("/admin/invites", { method: "POST", body: JSON.stringify({ email }) });

export const revokeAdminInvite = (id: string) =>
  request<void>(`/admin/invites/${id}`, { method: "DELETE" });

// Share
export const generateShareLink = (projectId: string, simId: string) =>
  request<Simulation>(`/projects/${projectId}/simulations/${simId}/share`, { method: "POST" });
export const revokeShareLink = (projectId: string, simId: string) =>
  request<Simulation>(`/projects/${projectId}/simulations/${simId}/share`, { method: "DELETE" });
export const getSharedSimulation = (shareToken: string) =>
  request<Simulation & { project_name: string; results: SimulationResult[] }>(`/share/${shareToken}`);

// API Keys
export interface APIKey {
  id: string;
  name: string;
  key_prefix: string;
  is_active: boolean;
  created_at: string;
  last_used_at: string | null;
  expires_at: string | null;
}

export interface APIKeyCreated extends APIKey {
  key: string; // full key — shown once
}

export const listApiKeys = () =>
  request<APIKey[]>("/settings/api-keys");

export const createApiKey = (name: string, expires_at?: string | null) =>
  request<APIKeyCreated>("/settings/api-keys", {
    method: "POST",
    body: JSON.stringify({ name, expires_at: expires_at ?? null }),
  });

export const revokeApiKey = (id: string) =>
  request<void>(`/settings/api-keys/${id}`, { method: "DELETE" });

// Team
export interface TeamMember {
  id: string;
  email: string;
  full_name: string | null;
  role: string;
  created_at: string;
}

export interface PendingInvite {
  id: string;
  email: string;
  role: string;
  expires_at: string;
  created_at: string;
  invited_by_name: string | null;
}

export interface TeamResponse {
  members: TeamMember[];
  pending_invites: PendingInvite[];
}

export const getTeam = () =>
  request<TeamResponse>("/settings/team");

export const inviteMember = (email: string, role = "member") =>
  request<PendingInvite>("/settings/team/invite", {
    method: "POST",
    body: JSON.stringify({ email, role }),
  });

export const cancelInvite = (id: string) =>
  request<void>(`/settings/team/invites/${id}`, { method: "DELETE" });

export const removeMember = (id: string) =>
  request<void>(`/settings/team/members/${id}`, { method: "DELETE" });

// Password
export const changePassword = (current_password: string, new_password: string) =>
  request<void>("/settings/password", {
    method: "PATCH",
    body: JSON.stringify({ current_password, new_password }),
  });

export const deleteAccount = (password: string) =>
  request<void>("/settings/account", {
    method: "DELETE",
    body: JSON.stringify({ password }),
  });

// Billing
export interface BillingStatus {
  plan: string;
  simulations_used: number;
  plan_limit: number;
  billing_period_ends_at: string | null;
  stripe_customer_id: string | null;
}

export const getBillingStatus = () =>
  request<BillingStatus>("/billing/status");

export const createCheckoutSession = (plan: string) =>
  request<{ url: string }>("/billing/checkout", {
    method: "POST",
    body: JSON.stringify({ plan }),
  });

export const createPortalSession = () =>
  request<{ url: string }>("/billing/portal", { method: "POST" });

