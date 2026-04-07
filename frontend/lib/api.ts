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

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Request failed");
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
    persona_group_id: string;
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

// Cross-simulation convergence
export const getConvergence = (projectId: string, personaGroupId: string, briefingId?: string | null) => {
  const qs = new URLSearchParams({ persona_group_id: personaGroupId });
  if (briefingId) qs.set("briefing_id", briefingId);
  return request<ConvergenceResult>(`/projects/${projectId}/simulations/convergence?${qs}`);
};
