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
  status: string;
  approved_by?: string | null;
  approved_at?: string | null;
};

export type CouncilAgentOutput = {
  id: string;
  review_id: string;
  agent_name: string;
  agent_type: string;
  status: string;
  summary?: string | null;
  findings: unknown[];
  evidence: unknown[];
  concerns: unknown[];
  confidence: number;
};

export type CouncilReview = {
  id: string;
  question?: string | null;
  verdict: string;
  confidence: number;
  provider?: string | null;
  status?: string;
  agreements?: unknown[];
  disagreements?: unknown[];
  unsupported_claims?: unknown[];
  follow_up?: unknown[];
  agent_outputs?: CouncilAgentOutput[];
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

// Portfolio reuse recommendation (RFC-0009). Evidence is a discriminated union:
// a distilled repository page (`distillation`, cited by vault-path `ref`) or the
// underlying repository row (`repository`, keyed by `id`).
export type TransferEvidence =
  | { type: 'distillation'; ref: string }
  | { type: 'repository'; id: string };

export type TransferRecommendation = {
  source_repository: string;
  source_project_id: string | null;
  reusable_asset: string;
  reason: string;
  matched_terms: string[];
  evidence: TransferEvidence[];
  required_changes: string | null;
  risks: string | null;
  confidence: number;
};

export type DigestRecommendation = {
  title?: string;
  reason?: string;
  status?: string;
  [key: string]: unknown;
};

export type NightlyDigest = {
  id: string;
  digest_date: string;
  summary: string | null;
  changes: unknown[];
  recommendations: DigestRecommendation[];
  repeated_tasks: unknown[];
};

export type Schedule = {
  id: string;
  project_id: string | null;
  name: string;
  job_type: string;
  interval_seconds: number;
  enabled: boolean;
  last_run_at: string | null;
  next_run_at: string;
};

export type Job = {
  id: string;
  job_type: string;
  status: string;
  queued_at: string;
  attempts: number;
  project_id: string | null;
  repository_id: string | null;
};

export type KnowledgePage = {
  id: string;
  project_id: string | null;
  title: string;
  vault_path: string;
  page_type: string;
  validation_state: string;
  source_refs: EvidenceEntry[];
  checksum: string;
  created_at: string;
  updated_at: string;
};

export type KnowledgeSyncResult = {
  synced: number;
  created: number;
  updated: number;
  open_lessons: number;
};

// LLM usage ledger (AOS-USAGE-001/002). `GET /usage/summary?window=today|7d|30d`
// returns real token/cost usage across the three reported tiers (claude / local
// / free). `estimated: true` on a bucket means at least one figure was
// length-derived (an envelope lacked `usage`), so it must never be shown as
// exact. Tiers are always present in `by_tier` (zeroed when empty); `by_model` is
// busiest-first.
export type UsageWindow = 'today' | '7d' | '30d';

export type UsageBucket = {
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  cost_usd: number;
  events: number;
  estimated: boolean;
};

export type UsageModelRow = UsageBucket & { model: string; tier: string };

export type UsageSummary = {
  window: UsageWindow;
  since: string; // ISO timestamp
  totals: UsageBucket;
  by_tier: { claude: UsageBucket; local: UsageBucket; free: UsageBucket };
  by_model: UsageModelRow[];
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, init);
  if (!response.ok) {
    // Surface the API error `detail` (FastAPI HTTPException bodies are
    // `{"detail": ...}`) so callers can show human-readable 409 messages
    // (e.g. abstention-blocks-approval, read-only vault). Fall back to the
    // status line when the body is missing or not JSON.
    let detail: string | null = null;
    try {
      const body = (await response.json()) as { detail?: unknown };
      if (body && body.detail !== undefined && body.detail !== null) {
        detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail);
      }
    } catch {
      detail = null;
    }
    throw new Error(detail ?? `Request to ${path} failed with status ${response.status}`);
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

export async function fetchCouncilReviews(projectId: string): Promise<CouncilReview[]> {
  return request<CouncilReview[]>(`/projects/${projectId}/council-reviews`);
}

export async function fetchCouncilReview(reviewId: string): Promise<CouncilReview> {
  return request<CouncilReview>(`/council-reviews/${reviewId}`);
}

export async function enqueueCouncilReview(projectId: string, question: string): Promise<Job> {
  return request<Job>(`/projects/${projectId}/council-reviews`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  });
}

export async function draftDecisionFromReview(reviewId: string): Promise<Decision> {
  return request<Decision>(`/council-reviews/${reviewId}/draft-decision`, { method: 'POST' });
}

export async function approveDecision(
  decisionId: string,
  approver: string,
  rationale?: string,
): Promise<Decision> {
  return request<Decision>(`/decisions/${decisionId}/approve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ approver, rationale: rationale ?? null }),
  });
}

export async function rejectDecision(
  decisionId: string,
  approver: string,
  rationale: string,
): Promise<Decision> {
  return request<Decision>(`/decisions/${decisionId}/reject`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ approver, rationale }),
  });
}

export async function exportDecisionAdr(decisionId: string): Promise<KnowledgePage> {
  return request<KnowledgePage>(`/decisions/${decisionId}/adr`, { method: 'POST' });
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

export async function fetchDigests(projectId: string): Promise<NightlyDigest[]> {
  return request<NightlyDigest[]>(`/projects/${projectId}/digests`);
}

export async function runDigest(projectId: string): Promise<NightlyDigest> {
  return request<NightlyDigest>(`/projects/${projectId}/digests`, { method: 'POST' });
}

export async function fetchSchedules(projectId: string): Promise<Schedule[]> {
  return request<Schedule[]>(`/projects/${projectId}/schedules`);
}

export async function createSchedule(
  projectId: string,
  payload: { name: string; job_type: string; interval_seconds: number },
): Promise<Schedule> {
  return request<Schedule>(`/projects/${projectId}/schedules`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      name: payload.name,
      job_type: payload.job_type,
      interval_seconds: payload.interval_seconds,
    }),
  });
}

export async function setScheduleEnabled(scheduleId: string, enabled: boolean): Promise<Schedule> {
  return request<Schedule>(`/schedules/${scheduleId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ enabled }),
  });
}

export async function deleteSchedule(scheduleId: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/schedules/${scheduleId}`, { method: 'DELETE' });
  if (!response.ok) {
    throw new Error(`Failed to delete schedule with status ${response.status}`);
  }
}

export async function runSchedule(scheduleId: string): Promise<Job> {
  return request<Job>(`/schedules/${scheduleId}/run`, { method: 'POST' });
}

export async function enqueueJob(body: {
  project_id?: string;
  repository_id?: string;
  job_type: string;
}): Promise<Job> {
  return request<Job>('/jobs', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

export async function fetchJobs(projectId: string): Promise<Job[]> {
  return request<Job[]>(`/projects/${projectId}/jobs`);
}

export async function fetchKnowledgePages(params?: {
  page_type?: string;
  validation_state?: string;
}): Promise<KnowledgePage[]> {
  const query = new URLSearchParams();
  if (params?.page_type) {
    query.set('page_type', params.page_type);
  }
  if (params?.validation_state) {
    query.set('validation_state', params.validation_state);
  }
  const suffix = query.toString() ? `?${query.toString()}` : '';
  return request<KnowledgePage[]>(`/knowledge/pages${suffix}`);
}

export async function syncKnowledge(): Promise<KnowledgeSyncResult> {
  return request<KnowledgeSyncResult>('/knowledge/sync', { method: 'POST' });
}

// Knowledge Transfer Engine: scan the portfolio's distilled knowledge for a
// described need. The backend excludes the target project's own repos and sorts
// results by confidence; an empty portfolio / no match returns `[]`.
export async function fetchReuseRecommendations(
  projectId: string,
  need: string,
): Promise<TransferRecommendation[]> {
  return request<TransferRecommendation[]>(`/projects/${projectId}/transfer`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ need }),
  });
}

// LLM usage ledger summary for the Providers & Model Routing view (AOS-USAGE-002).
// Read-only; the ledger is written centrally by the InstrumentedProvider wrapper,
// never from the UI. An empty ledger returns zeroed totals + tiers with `[]`
// models — the caller renders that as the empty state, not an error.
export async function fetchUsageSummary(window: UsageWindow): Promise<UsageSummary> {
  return request<UsageSummary>(`/usage/summary?window=${encodeURIComponent(window)}`);
}
