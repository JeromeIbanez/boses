import type {
  Briefing,
  LibraryPersona,
  LibraryPersonaListResponse,
  Persona,
  PersonaGroup,
  Project,
  Simulation,
  SimulationResult,
} from "@/types";

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Request failed");
  }
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

// Personas
export const getPersonas = (projectId: string, groupId: string) =>
  request<Persona[]>(`/projects/${projectId}/persona-groups/${groupId}/personas`);

// Briefings
export const getBriefings = (projectId: string) =>
  request<Briefing[]>(`/projects/${projectId}/briefings`);
export const getBriefing = (projectId: string, briefingId: string) =>
  request<Briefing>(`/projects/${projectId}/briefings/${briefingId}`);
export const uploadBriefing = (projectId: string, formData: FormData) =>
  fetch(`${BASE}/projects/${projectId}/briefings`, {
    method: "POST",
    body: formData,
  }).then((r) => {
    if (!r.ok) throw new Error("Upload failed");
    return r.json() as Promise<Briefing>;
  });
export const deleteBriefing = (projectId: string, briefingId: string) =>
  request<void>(`/projects/${projectId}/briefings/${briefingId}`, { method: "DELETE" });

// Simulations
export const getSimulations = (projectId: string) =>
  request<Simulation[]>(`/projects/${projectId}/simulations`);
export const getSimulation = (projectId: string, simId: string) =>
  request<Simulation>(`/projects/${projectId}/simulations/${simId}`);
export const createSimulation = (
  projectId: string,
  body: { persona_group_id: string; briefing_id: string; prompt_question: string }
) =>
  request<Simulation>(`/projects/${projectId}/simulations`, {
    method: "POST",
    body: JSON.stringify(body),
  });
export const getSimulationResults = (projectId: string, simId: string) =>
  request<SimulationResult[]>(`/projects/${projectId}/simulations/${simId}/results`);

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
