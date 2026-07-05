export const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

export type Health = {
  status: string;
  api: boolean;
  database: boolean;
  redis: boolean;
};

export type Project = {
  id: string;
  name: string;
  slug: string;
  description?: string | null;
  status: string;
  version: number;
  created_at: string;
  updated_at: string;
};

export type Repository = {
  id: string;
  project_id: string;
  name: string;
  local_path: string;
  default_branch?: string | null;
  remote_url?: string | null;
  is_read_only: boolean;
  status: string;
  last_scanned_at: string | null;
  version: number;
  created_at: string;
  updated_at: string;
};

export type RepositoryDna = {
  repository_id: string;
  language_mix: Record<string, number>;
  package_managers: string[];
  deployment_files: string[];
  risk_flags: string[];
  scan_summary: {
    summary?: {
      primary_language_hints?: string[];
      has_docker?: boolean;
      has_ci?: boolean;
      has_tests?: boolean;
      has_env_example?: boolean;
      [key: string]: unknown;
    };
    [key: string]: unknown;
  };
  confidence: number;
  status: string;
  version: number;
  created_at: string;
  updated_at: string;
};

export type ArchitectureNode = {
  id: string;
  label: string;
  type: string;
  confidence: number;
  manual_correction: string | null;
};

export type ArchitectureEdge = {
  id: string;
  type: string;
};

export type ArchitectureGraph = {
  nodes: ArchitectureNode[];
  edges: ArchitectureEdge[];
};

export type ScanResponse = {
  repository_id: string;
  summary: Record<string, unknown>;
  dna: Record<string, unknown>;
  architecture_nodes: unknown[];
  architecture_edges: unknown[];
  artifacts: unknown[];
};

export type EvidenceEntry = {
  type?: string;
  id?: string;
  [key: string]: unknown;
};

export type Decision = {
  id: string;
  title: string;
  decision?: string | null;
  confidence: number;
  evidence: EvidenceEntry[];
};

export type ResearchNote = {
  id: string;
  title: string;
  summary?: string | null;
  freshness?: string | null;
  confidence: number;
};

export type Recommendation = {
  id: string;
  title: string;
  confidence: number;
  evidence: EvidenceEntry[];
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, init);
  if (!response.ok) {
    throw new Error(`Request to ${path} failed with status ${response.status}`);
  }
  return (await response.json()) as T;
}

export async function fetchHealth(): Promise<Health> {
  return request<Health>('/health');
}

export async function fetchProjects(): Promise<Project[]> {
  return request<Project[]>('/projects');
}

export async function createProject(name: string, description?: string): Promise<Project> {
  return request<Project>('/projects', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, description: description ?? null }),
  });
}

export async function fetchRepositories(projectId: string): Promise<Repository[]> {
  return request<Repository[]>(`/projects/${projectId}/repositories`);
}

export async function registerRepository(
  projectId: string,
  name: string,
  localPath: string,
): Promise<Repository> {
  return request<Repository>(`/projects/${projectId}/repositories`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, local_path: localPath }),
  });
}

export async function scanRepository(repositoryId: string): Promise<ScanResponse> {
  return request<ScanResponse>(`/repositories/${repositoryId}/scan`, { method: 'POST' });
}

export async function fetchDna(repositoryId: string): Promise<RepositoryDna | null> {
  const response = await fetch(`${API_BASE_URL}/repositories/${repositoryId}/dna`);
  if (response.status === 404) {
    return null;
  }
  if (!response.ok) {
    throw new Error(`Failed to load DNA with status ${response.status}`);
  }
  return (await response.json()) as RepositoryDna;
}

export async function fetchArchitecture(
  projectId: string,
  repositoryId?: string,
): Promise<ArchitectureGraph> {
  const query = repositoryId ? `?repository_id=${encodeURIComponent(repositoryId)}` : '';
  return request<ArchitectureGraph>(`/projects/${projectId}/architecture${query}`);
}

export async function fetchDecisions(projectId: string): Promise<Decision[]> {
  return request<Decision[]>(`/projects/${projectId}/decisions`);
}

export async function createDecision(
  projectId: string,
  payload: { title: string; decision: string; research_note_ids?: string[] },
): Promise<Decision> {
  return request<Decision>(`/projects/${projectId}/decisions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      title: payload.title,
      decision: payload.decision,
      research_note_ids: payload.research_note_ids ?? [],
    }),
  });
}

export async function fetchResearchNotes(projectId: string): Promise<ResearchNote[]> {
  return request<ResearchNote[]>(`/projects/${projectId}/research-notes`);
}

export async function createResearchNote(
  projectId: string,
  payload: { title: string; summary: string },
): Promise<ResearchNote> {
  return request<ResearchNote>(`/projects/${projectId}/research-notes`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title: payload.title, summary: payload.summary }),
  });
}

export async function fetchRecommendations(projectId: string): Promise<Recommendation[]> {
  return request<Recommendation[]>(`/projects/${projectId}/recommendations`);
}
