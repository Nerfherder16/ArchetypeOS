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
  audits_enabled: boolean;
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
  // AOS-AUTHORITY-HARDEN-001: data-sensitivity policy; drives egress approval.
  sensitivity: string;
  status: string;
  last_scanned_at: string | null;
  version: number;
  created_at: string;
  updated_at: string;
};

export type RepositoryDna = {
  repository_id: string;
  // AOS-CONTRACT-001: the reasoned evidence the backend computes, no longer dropped
  // at the API seam.
  purpose: string | null;
  maturity: string | null;
  language_mix: Record<string, number>;
  package_managers: string[];
  frameworks: string[];
  runtime_services: string[];
  deployment_files: string[];
  risk_flags: string[];
  evidence: unknown[];
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
  project_id: string;
  repository_id: string | null;
  label: string;
  type: string;
  parent_id: string | null;
  confidence: number;
  // AOS-CONTRACT-001 / AOS-ARCH-STUDIO-001: evidence + risks the backend already
  // exposes, surfaced in the node detail drawer alongside the correction state.
  evidence: unknown[];
  risks: unknown[];
  manual_correction: string | null;
};

export type ArchitectureEdge = {
  id: string;
  project_id: string;
  repository_id: string | null;
  type: string;
  // AOS-CONTRACT-001: full edge evidence the backend already exposes.
  from_node_id: string;
  to_node_id: string;
  confidence: number;
  evidence: unknown[];
  manual_correction: string | null;
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
  project_id: string;
  title: string;
  context: string | null;
  decision: string | null;
  alternatives: unknown[];
  tradeoffs: unknown[];
  consequences: unknown[];
  confidence: number;
  evidence: EvidenceEntry[];
  status: string;
  approved_by: string | null;
  approved_at: string | null;
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
  agent_model?: string | null;
};

export type CouncilReview = {
  id: string;
  project_id: string;
  question: string | null;
  verdict: string;
  confidence: number;
  provider: string | null;
  job_id: string | null;
  status: string;
  agreements: unknown[];
  disagreements: unknown[];
  unsupported_claims: unknown[];
  follow_up: unknown[];
  agent_outputs: CouncilAgentOutput[];
};

export type ResearchNote = {
  id: string;
  project_id?: string;
  title: string;
  question?: string | null;
  summary?: string | null;
  // AOS-CONTRACT-001: the sources/findings/status the backend records.
  sources: string[];
  findings: string[];
  freshness?: string | null;
  status?: string;
  confidence: number;
};

export type Recommendation = {
  id: string;
  project_id: string;
  title: string;
  recommendation: string | null;
  rationale: string | null;
  alternatives: unknown[];
  pros: unknown[];
  cons: unknown[];
  risk: string | null;
  effort: string | null;
  dependencies: unknown[];
  acceptance_criteria: unknown[];
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
  project_id: string;
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
  priority: number;
  payload: Record<string, unknown>;
  result: Record<string, unknown> | null;
  queued_at: string;
  // Optional lifecycle timestamps + failure reason (all exposed by `JobRead`).
  // Older/queued jobs leave `started_at`/`finished_at` null; `error` is set only
  // on failure. The Live Activity feed (AOS-OPS-002) reads these for its time
  // ordering and failed-row snippet, so they are surfaced on the frontend type.
  started_at: string | null;
  finished_at: string | null;
  error: string | null;
  attempts: number;
  project_id: string | null;
  repository_id: string | null;
  // AOS-NODE-EXECUTION-001: routing fields, surfaced for the Control Tower audit.
  required_capability: string | null;
  sensitivity: string;
  requires_write: boolean;
  assigned_node_id: string | null;
  routing_status: string;
  routing_explanation: string | null;
  routed_at: string | null;
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

export async function updateProject(
  projectId: string,
  patch: { audits_enabled?: boolean },
): Promise<Project> {
  return request<Project>(`/projects/${projectId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(patch),
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

// AOS-ARCH-STUDIO-001: set/clear an operator correction on a node or edge. A null
// or empty string clears it. The corrected graph feeds Council context (backend).
export async function correctArchitectureNode(
  nodeId: string,
  manualCorrection: string | null,
): Promise<ArchitectureNode> {
  return request<ArchitectureNode>(`/architecture/nodes/${nodeId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ manual_correction: manualCorrection || null }),
  });
}

export async function correctArchitectureEdge(
  edgeId: string,
  manualCorrection: string | null,
): Promise<ArchitectureEdge> {
  return request<ArchitectureEdge>(`/architecture/edges/${edgeId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ manual_correction: manualCorrection || null }),
  });
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

// Voice Command Center (AOS-VOICE-001/002). A typed or spoken command is one
// "turn": the backend classifies the intent, persists a review-first inbox draft,
// and returns a short spoken reply. The CommandDeck funnels both typed and
// Sotto-transcribed input through here, so the pipeline is identical either way.
export type VoiceInboxItem = {
  id: string;
  project_id: string | null;
  transcript: string;
  summary: string;
  detected_intent: string;
  detected_project: string | null;
  suggested_action: string;
  confidence: number;
  required_review: boolean;
  review_state: string;
  source_device: string;
  reply_text: string;
  promoted_kind: string | null;
  promoted_id: string | null;
  created_at: string;
};

export async function postVoiceTurn(
  transcript: string,
  sourceDevice = 'web',
  projectId?: string,
): Promise<VoiceInboxItem> {
  return request<VoiceInboxItem>('/voice/turns', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      transcript,
      source_device: sourceDevice,
      project_id: projectId ?? null,
    }),
  });
}

export async function fetchVoiceInbox(): Promise<VoiceInboxItem[]> {
  return request<VoiceInboxItem[]>('/voice/inbox');
}

// Approve / dismiss / re-open a review-first Voice Inbox draft (AOS-VOICE-003).
// Review-first: this only transitions review_state; promoting an approved draft
// into its concrete action is a later slice (AOS-VOICE-005).
export type VoiceReviewState = 'pending' | 'approved' | 'dismissed';

export async function updateVoiceInboxItem(
  id: string,
  reviewState: VoiceReviewState,
): Promise<VoiceInboxItem> {
  return request<VoiceInboxItem>(`/voice/inbox/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ review_state: reviewState }),
  });
}

// Server-side TTS (Groq Orpheus, AOS-VOICE-004). Returns the WAV blob to play, or
// null when TTS is unconfigured (204) or the request fails — the caller then falls
// back to the browser's speechSynthesis. The Groq key stays server-side. Never
// throws: a spoken reply must not be blocked on TTS.
export async function fetchSpeech(text: string): Promise<Blob | null> {
  try {
    const response = await fetch(`${API_BASE_URL}/voice/speak`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    });
    if (response.status === 204 || !response.ok) return null;
    return await response.blob();
  } catch {
    return null;
  }
}

// Node registry (AOS-NODE-001). Read-only surface for Operations → Nodes.
export type NodeCapability = {
  id: string;
  capability: string;
  capability_version: string | null;
  capability_status: string;
  limits: Record<string, unknown>;
};

export type NodeInfo = {
  id: string;
  name: string;
  node_type: string;
  endpoint: string | null;
  node_status: string;
  last_seen_at: string | null;
  max_sensitivity: string;
  write_access: boolean;
  capabilities: NodeCapability[];
  status: string;
  version: number;
  created_at: string;
  updated_at: string;
};

export async function fetchNodes(): Promise<NodeInfo[]> {
  return request<NodeInfo[]>('/nodes');
}

// Connector registry (AOS-CONNECTOR-001). Read-only governance surface.
export type Connector = {
  id: string;
  name: string;
  connector_type: string;
  tier: string;
  enabled: boolean;
  configured: boolean;
  // AOS-CONNECTOR-RUNTIME-001 (P0-4): decomposed status — credential present vs reachable.
  credential_present: boolean;
  reachable: boolean | null;
  privacy_class: string;
  egress_allowed: boolean;
  browser_exposed: boolean;
  quota_policy: string;
  last_health_status: string;
  last_error: string | null;
  last_checked_at: string | null;
  status: string;
  version: number;
  created_at: string;
  updated_at: string;
};

export async function fetchConnectors(): Promise<Connector[]> {
  return request<Connector[]>('/connectors');
}

// Authority action policy (AOS-AUTHORITY-001). The queue of high-impact actions
// awaiting a human decision (ApprovalRecord rows with approval_status "pending").
export type PendingAuthorityAction = {
  id: string;
  project_id: string | null;
  actor: string | null;
  agent: string | null;
  tool: string | null;
  action_level: number;
  requested_capability: string | null;
  target: string | null;
  reason: string | null;
  approval_status: string;
  created_at: string;
  updated_at: string;
};

export async function fetchPendingAuthorityActions(): Promise<PendingAuthorityAction[]> {
  return request<PendingAuthorityAction[]>('/authority/pending');
}

// Multi-phase research plans + runs (AOS-RESEARCH-003).
export type ResearchPlan = {
  id: string;
  project_id: string;
  question: string;
  sensitivity: string;
  plan_status: string;
  required_source_types: string[];
  search_queries: string[];
  verification_steps: string[];
  synthesis_policy: Record<string, unknown>;
  status: string;
  version: number;
  created_at: string;
  updated_at: string;
};

export type ResearchRunSource = {
  ref: string;
  title: string;
  tier: string | null;
  score: number;
  accepted: boolean;
  reason: string | null;
};

export type ResearchRunFinding = {
  claim: string;
  source_ref: string;
  tier?: string;
  label?: string;
};

export type ResearchRunPhase = { phase: string; detail: string };

export type ResearchRun = {
  id: string;
  plan_id: string;
  project_id: string;
  job_id: string | null;
  run_status: string;
  phases: ResearchRunPhase[];
  sources: ResearchRunSource[];
  findings: ResearchRunFinding[];
  conflicts: unknown[];
  open_questions: string[];
  confidence: number;
  status: string;
  version: number;
  created_at: string;
  updated_at: string;
};

// AOS-SELFHEAL observability — one heartbeat row per nightly self-learn routine
// (conflict / toil / coherence / session-pain). Mirrors AuditHeartbeatRead.
// `project_id` is null for global routines; per-project audits carry the owning project.
export type AuditHeartbeat = {
  id: string;
  routine: string;
  heartbeat_status: string;
  day: string;
  pr_url: string | null;
  detail: string | null;
  project_id: string | null;
  status: string;
  version: number;
  created_at: string;
  updated_at: string;
};

export async function fetchAuditHeartbeats(): Promise<AuditHeartbeat[]> {
  return request<AuditHeartbeat[]>('/audits/heartbeats');
}

export async function createResearchPlan(
  projectId: string,
  question: string,
  sensitivity = 'public',
): Promise<ResearchPlan> {
  return request<ResearchPlan>(`/projects/${projectId}/research-plans`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, sensitivity }),
  });
}

export async function fetchResearchPlans(projectId: string): Promise<ResearchPlan[]> {
  return request<ResearchPlan[]>(`/projects/${projectId}/research-plans`);
}

export async function fetchResearchPlan(planId: string): Promise<ResearchPlan> {
  return request<ResearchPlan>(`/research-plans/${planId}`);
}

export async function runResearchPlan(planId: string): Promise<Job> {
  return request<Job>(`/research-plans/${planId}/run`, { method: 'POST' });
}

export async function fetchResearchRuns(planId: string): Promise<ResearchRun[]> {
  return request<ResearchRun[]>(`/research-plans/${planId}/runs`);
}

export async function decideSource(
  runId: string,
  sourceRef: string,
  accepted: boolean,
  reason: string,
): Promise<ResearchRun> {
  // The backend route is `{source_ref:path}`, so raw slashes in a ref (e.g. a
  // vault path) are matched as-is — do not percent-encode them away.
  return request<ResearchRun>(
    `/research-runs/${runId}/sources/${sourceRef}/decision`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ accepted, reason }),
    },
  );
}
