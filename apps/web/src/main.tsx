import React, { useCallback, useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import {
  approveDecision,
  createDecision,
  createProject,
  createResearchNote,
  createSchedule,
  deleteSchedule,
  draftDecisionFromReview,
  enqueueCouncilReview,
  enqueueJob,
  exportDecisionAdr,
  fetchArchitecture,
  fetchCouncilReview,
  fetchCouncilReviews,
  fetchDecisions,
  fetchDigests,
  fetchDna,
  fetchHealth,
  fetchJobs,
  fetchKnowledgePages,
  fetchProjects,
  fetchRecommendations,
  fetchRepositories,
  fetchResearchNotes,
  fetchSchedules,
  registerRepository,
  rejectDecision,
  runDigest,
  runSchedule,
  scanRepository,
  setScheduleEnabled,
  syncKnowledge,
  type ArchitectureGraph,
  type CouncilReview,
  type Decision,
  type Health,
  type Job,
  type KnowledgePage,
  type NightlyDigest,
  type Project,
  type Recommendation,
  type Repository,
  type RepositoryDna,
  type ResearchNote,
  type Schedule,
} from './api';
import { ReuseView } from './features/reuse/ReuseView';
import { ProvidersView } from './features/providers/ProvidersView';
import { ApprovalsView } from './features/approvals/ApprovalsView';
import { ActivityView } from './features/activity/ActivityView';
import { VoiceInboxView } from './features/voice/VoiceInboxView';
import { ResearchInboxView } from './features/research/ResearchInboxView';
import { CommandDeck } from './features/command/CommandDeck';
import { Shell, type ViewId } from './shell/Shell';
import { WORKSPACE_MODES } from './shell/workspaces';
import './design/tokens.css';

const errorMessage = (err: unknown): string =>
  err instanceof Error ? err.message : 'Request failed';

// Palette for the decision-loop status badge; unknown statuses fall back to grey.
// Ops-deck `.aos-pill` tier per decision status (blue+red palette):
// draft → info (periwinkle), needs_evidence → warn (muted red),
// approved → good (cyan), rejected → risk (red), active/unknown → neutral.
const DECISION_STATUS_PILL_TIER: Record<string, string> = {
  draft: 'info',
  needs_evidence: 'warn',
  approved: 'good',
  rejected: 'risk',
  active: 'neutral',
};

// Ops-deck `.aos-pill` tier per council verdict. "Insufficient evidence"
// (abstention) additionally carries the `abstain` modifier — dashed border +
// italic label — to stay visually distinct exactly as the legacy badge was.
const VERDICT_PILL_TIER: Record<string, string> = {
  Accept: 'good',
  'Accept with warnings': 'good',
  Reject: 'risk',
  Defer: 'info',
  'Research further': 'info',
  'Simulate first': 'info',
  'Escalate to human': 'warn',
  'Insufficient evidence': 'neutral',
};

function VerdictBadge({ verdict }: { verdict: string }) {
  const isAbstention = verdict === 'Insufficient evidence';
  const tier = VERDICT_PILL_TIER[verdict] ?? 'neutral';
  return <span className={`aos-pill ${tier}${isAbstention ? ' abstain' : ''}`}>{verdict}</span>;
}

// Defensive renderer for list items whose shape may be a plain string or a
// small object (e.g. { text: '...' } or { summary: '...' }).  Never crashes.
function renderListItem(item: unknown): string {
  if (typeof item === 'string') {
    return item;
  }
  if (item !== null && typeof item === 'object') {
    const obj = item as Record<string, unknown>;
    const field = obj.text ?? obj.summary ?? obj.description ?? obj.message ?? obj.content;
    if (typeof field === 'string') {
      return field;
    }
    return JSON.stringify(item);
  }
  return String(item ?? '');
}

function DecisionStatusBadge({ status }: { status: string }) {
  const tier = DECISION_STATUS_PILL_TIER[status] ?? 'neutral';
  return <span className={`aos-pill ${tier}`}>{status}</span>;
}

// Prompt shown inside a view that needs a selected project when none is active.
function SelectProjectNotice() {
  return (
    <div className="aos-legacy">
      <p style={{ margin: 0 }}>
        Select or create a project in the rail to load this view.
      </p>
    </div>
  );
}

function App() {
  const [activeView, setActiveView] = useState<ViewId>('overview');

  const [health, setHealth] = useState<Health | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);

  const [knowledgePages, setKnowledgePages] = useState<KnowledgePage[]>([]);
  const [knowledgeError, setKnowledgeError] = useState<string | null>(null);
  const [knowledgeFilter, setKnowledgeFilter] = useState<'all' | 'open'>('all');
  const [knowledgeSyncing, setKnowledgeSyncing] = useState(false);
  const [knowledgeSyncSummary, setKnowledgeSyncSummary] = useState<string | null>(null);

  const [projects, setProjects] = useState<Project[]>([]);
  const [projectsError, setProjectsError] = useState<string | null>(null);
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [newProjectName, setNewProjectName] = useState('');
  const [creatingProject, setCreatingProject] = useState(false);

  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [repositoriesError, setRepositoriesError] = useState<string | null>(null);
  const [selectedRepositoryId, setSelectedRepositoryId] = useState<string | null>(null);
  const [newRepoName, setNewRepoName] = useState('');
  const [newRepoPath, setNewRepoPath] = useState('');
  const [registeringRepo, setRegisteringRepo] = useState(false);
  const [scanningRepoId, setScanningRepoId] = useState<string | null>(null);

  const [dna, setDna] = useState<RepositoryDna | null>(null);
  const [dnaError, setDnaError] = useState<string | null>(null);
  const [dnaLoading, setDnaLoading] = useState(false);

  const [architecture, setArchitecture] = useState<ArchitectureGraph | null>(null);
  const [architectureError, setArchitectureError] = useState<string | null>(null);

  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [researchNotes, setResearchNotes] = useState<ResearchNote[]>([]);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [artifactsError, setArtifactsError] = useState<string | null>(null);
  const [newNoteTitle, setNewNoteTitle] = useState('');
  const [newNoteSummary, setNewNoteSummary] = useState('');
  const [creatingNote, setCreatingNote] = useState(false);
  const [newDecisionTitle, setNewDecisionTitle] = useState('');
  const [newDecisionText, setNewDecisionText] = useState('');
  const [newDecisionNoteId, setNewDecisionNoteId] = useState('');
  const [creatingDecision, setCreatingDecision] = useState(false);

  const [councilReviews, setCouncilReviews] = useState<CouncilReview[]>([]);
  const [councilError, setCouncilError] = useState<string | null>(null);
  const [councilQuestion, setCouncilQuestion] = useState('');
  const [councilBusy, setCouncilBusy] = useState(false);
  // Which loop action is currently in flight (keyed `${action}:${id}`), so only
  // the acting control is disabled and spinners don't fight across rows.
  const [loopBusyKey, setLoopBusyKey] = useState<string | null>(null);
  // Per-decision approver name inputs and inline action errors (409s render here,
  // scoped to their decision row rather than blanking the section).
  const [approverInputs, setApproverInputs] = useState<Record<string, string>>({});
  const [decisionErrors, setDecisionErrors] = useState<Record<string, string>>({});
  const [adrResults, setAdrResults] = useState<Record<string, string>>({});

  const [digests, setDigests] = useState<NightlyDigest[]>([]);
  const [digestsError, setDigestsError] = useState<string | null>(null);
  const [runningDigest, setRunningDigest] = useState(false);

  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [schedulingError, setSchedulingError] = useState<string | null>(null);
  const [newScheduleName, setNewScheduleName] = useState('');
  const [newScheduleJobType, setNewScheduleJobType] = useState('repository_scan');
  const [newScheduleInterval, setNewScheduleInterval] = useState('3600');
  const [creatingSchedule, setCreatingSchedule] = useState(false);
  const [scanJobRepoId, setScanJobRepoId] = useState('');
  const [schedulingBusy, setSchedulingBusy] = useState(false);

  // Agent Council section state (separate from Decision Loop).
  const [councilSectionLoading, setCouncilSectionLoading] = useState(false);
  const [councilSectionError, setCouncilSectionError] = useState<string | null>(null);
  const [councilExpandedId, setCouncilExpandedId] = useState<string | null>(null);
  const [councilDetailMap, setCouncilDetailMap] = useState<Record<string, CouncilReview>>({});
  const [councilDetailLoading, setCouncilDetailLoading] = useState<string | null>(null);
  const [councilDetailError, setCouncilDetailError] = useState<Record<string, string>>({});

  const loadHealth = useCallback(async () => {
    setHealthError(null);
    try {
      setHealth(await fetchHealth());
    } catch (err) {
      setHealth(null);
      setHealthError(errorMessage(err));
    }
  }, []);

  const loadKnowledge = useCallback(async (filter: 'all' | 'open') => {
    setKnowledgeError(null);
    try {
      const params = filter === 'open' ? { validation_state: 'open' } : undefined;
      setKnowledgePages(await fetchKnowledgePages(params));
    } catch (err) {
      setKnowledgePages([]);
      setKnowledgeError(errorMessage(err));
    }
  }, []);

  const loadProjects = useCallback(async () => {
    setProjectsError(null);
    try {
      setProjects(await fetchProjects());
    } catch (err) {
      setProjectsError(errorMessage(err));
    }
  }, []);

  const loadRepositories = useCallback(async (projectId: string) => {
    setRepositoriesError(null);
    try {
      setRepositories(await fetchRepositories(projectId));
    } catch (err) {
      setRepositories([]);
      setRepositoriesError(errorMessage(err));
    }
  }, []);

  const loadDna = useCallback(async (repositoryId: string) => {
    setDnaError(null);
    setDnaLoading(true);
    try {
      setDna(await fetchDna(repositoryId));
    } catch (err) {
      setDna(null);
      setDnaError(errorMessage(err));
    } finally {
      setDnaLoading(false);
    }
  }, []);

  const loadArchitecture = useCallback(async (projectId: string, repositoryId: string) => {
    setArchitectureError(null);
    try {
      setArchitecture(await fetchArchitecture(projectId, repositoryId));
    } catch (err) {
      setArchitecture(null);
      setArchitectureError(errorMessage(err));
    }
  }, []);

  const loadArtifacts = useCallback(async (projectId: string) => {
    setArtifactsError(null);
    try {
      const [nextDecisions, nextNotes, nextRecommendations] = await Promise.all([
        fetchDecisions(projectId),
        fetchResearchNotes(projectId),
        fetchRecommendations(projectId),
      ]);
      setDecisions(nextDecisions);
      setResearchNotes(nextNotes);
      setRecommendations(nextRecommendations);
    } catch (err) {
      setDecisions([]);
      setResearchNotes([]);
      setRecommendations([]);
      setArtifactsError(errorMessage(err));
    }
  }, []);

  const loadCouncilReviews = useCallback(async (projectId: string) => {
    setCouncilError(null);
    try {
      setCouncilReviews(await fetchCouncilReviews(projectId));
    } catch (err) {
      setCouncilReviews([]);
      setCouncilError(errorMessage(err));
    }
  }, []);

  const loadDigests = useCallback(async (projectId: string) => {
    setDigestsError(null);
    try {
      setDigests(await fetchDigests(projectId));
    } catch (err) {
      setDigests([]);
      setDigestsError(errorMessage(err));
    }
  }, []);

  const loadScheduling = useCallback(async (projectId: string) => {
    setSchedulingError(null);
    try {
      const [nextSchedules, nextJobs] = await Promise.all([
        fetchSchedules(projectId),
        fetchJobs(projectId),
      ]);
      setSchedules(nextSchedules);
      setJobs(nextJobs);
    } catch (err) {
      setSchedules([]);
      setJobs([]);
      setSchedulingError(errorMessage(err));
    }
  }, []);

  const loadJobs = useCallback(async (projectId: string) => {
    setSchedulingError(null);
    try {
      setJobs(await fetchJobs(projectId));
    } catch (err) {
      setJobs([]);
      setSchedulingError(errorMessage(err));
    }
  }, []);

  useEffect(() => {
    void loadHealth();
    void loadProjects();
  }, [loadHealth, loadProjects]);

  // Knowledge is a GLOBAL surface (lessons have no project); it loads on mount
  // and refetches whenever the All/Open filter changes, never gated on a project.
  useEffect(() => {
    void loadKnowledge(knowledgeFilter);
  }, [loadKnowledge, knowledgeFilter]);

  useEffect(() => {
    setSelectedRepositoryId(null);
    setRepositories([]);
    setDna(null);
    setArchitecture(null);
    setDecisions([]);
    setResearchNotes([]);
    setRecommendations([]);
    setArtifactsError(null);
    setNewDecisionNoteId('');
    setCouncilReviews([]);
    setCouncilError(null);
    setCouncilQuestion('');
    setApproverInputs({});
    setDecisionErrors({});
    setAdrResults({});
    setDigests([]);
    setDigestsError(null);
    setSchedules([]);
    setJobs([]);
    setSchedulingError(null);
    setScanJobRepoId('');
    setCouncilSectionLoading(false);
    setCouncilSectionError(null);
    setCouncilExpandedId(null);
    setCouncilDetailMap({});
    setCouncilDetailLoading(null);
    setCouncilDetailError({});
    if (selectedProjectId) {
      void loadRepositories(selectedProjectId);
      void loadArtifacts(selectedProjectId);
      void loadCouncilReviews(selectedProjectId);
      void loadDigests(selectedProjectId);
      void loadScheduling(selectedProjectId);
    }
  }, [
    selectedProjectId,
    loadRepositories,
    loadArtifacts,
    loadCouncilReviews,
    loadDigests,
    loadScheduling,
  ]);

  useEffect(() => {
    if (selectedProjectId && selectedRepositoryId) {
      void loadDna(selectedRepositoryId);
      void loadArchitecture(selectedProjectId, selectedRepositoryId);
    } else {
      setDna(null);
      setArchitecture(null);
    }
  }, [selectedProjectId, selectedRepositoryId, loadDna, loadArchitecture]);

  const handleSyncKnowledge = useCallback(async () => {
    setKnowledgeSyncing(true);
    setKnowledgeError(null);
    try {
      const result = await syncKnowledge();
      setKnowledgeSyncSummary(`synced ${result.synced} · ${result.open_lessons} open`);
      await loadKnowledge(knowledgeFilter);
    } catch (err) {
      setKnowledgeError(errorMessage(err));
    } finally {
      setKnowledgeSyncing(false);
    }
  }, [loadKnowledge, knowledgeFilter]);

  const handleCreateProject = useCallback(
    async (event: React.FormEvent) => {
      event.preventDefault();
      const name = newProjectName.trim();
      if (!name) {
        return;
      }
      setCreatingProject(true);
      setProjectsError(null);
      try {
        const created = await createProject(name);
        setNewProjectName('');
        await loadProjects();
        setSelectedProjectId(created.id);
      } catch (err) {
        setProjectsError(errorMessage(err));
      } finally {
        setCreatingProject(false);
      }
    },
    [newProjectName, loadProjects],
  );

  const handleRegisterRepository = useCallback(
    async (event: React.FormEvent) => {
      event.preventDefault();
      if (!selectedProjectId) {
        return;
      }
      const name = newRepoName.trim();
      const localPath = newRepoPath.trim();
      if (!name || !localPath) {
        return;
      }
      setRegisteringRepo(true);
      setRepositoriesError(null);
      try {
        await registerRepository(selectedProjectId, name, localPath);
        setNewRepoName('');
        setNewRepoPath('');
        await loadRepositories(selectedProjectId);
      } catch (err) {
        setRepositoriesError(errorMessage(err));
      } finally {
        setRegisteringRepo(false);
      }
    },
    [selectedProjectId, newRepoName, newRepoPath, loadRepositories],
  );

  const handleScan = useCallback(
    async (repositoryId: string) => {
      if (!selectedProjectId) {
        return;
      }
      setScanningRepoId(repositoryId);
      setDnaError(null);
      try {
        await scanRepository(repositoryId);
        setSelectedRepositoryId(repositoryId);
        await Promise.all([
          loadDna(repositoryId),
          loadArchitecture(selectedProjectId, repositoryId),
          loadRepositories(selectedProjectId),
        ]);
      } catch (err) {
        setDnaError(errorMessage(err));
      } finally {
        setScanningRepoId(null);
      }
    },
    [selectedProjectId, loadDna, loadArchitecture, loadRepositories],
  );

  const handleCreateResearchNote = useCallback(
    async (event: React.FormEvent) => {
      event.preventDefault();
      if (!selectedProjectId) {
        return;
      }
      const title = newNoteTitle.trim();
      if (!title) {
        return;
      }
      setCreatingNote(true);
      setArtifactsError(null);
      try {
        await createResearchNote(selectedProjectId, { title, summary: newNoteSummary.trim() });
        setNewNoteTitle('');
        setNewNoteSummary('');
        await loadArtifacts(selectedProjectId);
      } catch (err) {
        setArtifactsError(errorMessage(err));
      } finally {
        setCreatingNote(false);
      }
    },
    [selectedProjectId, newNoteTitle, newNoteSummary, loadArtifacts],
  );

  const handleCreateDecision = useCallback(
    async (event: React.FormEvent) => {
      event.preventDefault();
      if (!selectedProjectId) {
        return;
      }
      const title = newDecisionTitle.trim();
      if (!title) {
        return;
      }
      setCreatingDecision(true);
      setArtifactsError(null);
      try {
        await createDecision(selectedProjectId, {
          title,
          decision: newDecisionText.trim(),
          research_note_ids: newDecisionNoteId ? [newDecisionNoteId] : [],
        });
        setNewDecisionTitle('');
        setNewDecisionText('');
        setNewDecisionNoteId('');
        await loadArtifacts(selectedProjectId);
      } catch (err) {
        setArtifactsError(errorMessage(err));
      } finally {
        setCreatingDecision(false);
      }
    },
    [selectedProjectId, newDecisionTitle, newDecisionText, newDecisionNoteId, loadArtifacts],
  );

  const handleEnqueueCouncilReview = useCallback(
    async (event: React.FormEvent) => {
      event.preventDefault();
      if (!selectedProjectId) {
        return;
      }
      const question = councilQuestion.trim();
      if (!question) {
        return;
      }
      setCouncilBusy(true);
      setCouncilError(null);
      try {
        await enqueueCouncilReview(selectedProjectId, question);
        setCouncilQuestion('');
        // The worker produces the review asynchronously; the operator clicks
        // Refresh (or it is polled in e2e) until it appears.
        await loadCouncilReviews(selectedProjectId);
      } catch (err) {
        setCouncilError(errorMessage(err));
      } finally {
        setCouncilBusy(false);
      }
    },
    [selectedProjectId, councilQuestion, loadCouncilReviews],
  );

  const handleRefreshLoop = useCallback(async () => {
    if (!selectedProjectId) {
      return;
    }
    await Promise.all([loadCouncilReviews(selectedProjectId), loadArtifacts(selectedProjectId)]);
  }, [selectedProjectId, loadCouncilReviews, loadArtifacts]);

  // Agent Council section: independent refresh button with its own loading/error
  // state so it does not interfere with the Decision Loop's councilError.
  const handleRefreshCouncilSection = useCallback(async () => {
    if (!selectedProjectId) {
      return;
    }
    setCouncilSectionLoading(true);
    setCouncilSectionError(null);
    try {
      setCouncilReviews(await fetchCouncilReviews(selectedProjectId));
    } catch (err) {
      setCouncilSectionError(errorMessage(err));
    } finally {
      setCouncilSectionLoading(false);
    }
  }, [selectedProjectId]);

  const handleExpandReview = useCallback(
    async (reviewId: string) => {
      if (councilExpandedId === reviewId) {
        setCouncilExpandedId(null);
        return;
      }
      setCouncilExpandedId(reviewId);
      // Already cached — no re-fetch needed.
      if (councilDetailMap[reviewId]) {
        return;
      }
      setCouncilDetailLoading(reviewId);
      setCouncilDetailError((prev) => ({ ...prev, [reviewId]: '' }));
      try {
        const detail = await fetchCouncilReview(reviewId);
        setCouncilDetailMap((prev) => ({ ...prev, [reviewId]: detail }));
      } catch (err) {
        setCouncilDetailError((prev) => ({ ...prev, [reviewId]: errorMessage(err) }));
      } finally {
        setCouncilDetailLoading((prev) => (prev === reviewId ? null : prev));
      }
    },
    [councilExpandedId, councilDetailMap],
  );

  const handleDraftDecision = useCallback(
    async (reviewId: string) => {
      if (!selectedProjectId) {
        return;
      }
      setLoopBusyKey(`draft:${reviewId}`);
      setCouncilError(null);
      try {
        await draftDecisionFromReview(reviewId);
        await Promise.all([
          loadArtifacts(selectedProjectId),
          loadCouncilReviews(selectedProjectId),
        ]);
      } catch (err) {
        setCouncilError(errorMessage(err));
      } finally {
        setLoopBusyKey(null);
      }
    },
    [selectedProjectId, loadArtifacts, loadCouncilReviews],
  );

  const handleApproveDecision = useCallback(
    async (decisionId: string) => {
      if (!selectedProjectId) {
        return;
      }
      const approver = (approverInputs[decisionId] ?? '').trim();
      if (!approver) {
        setDecisionErrors((prev) => ({ ...prev, [decisionId]: 'Enter an approver name.' }));
        return;
      }
      setLoopBusyKey(`approve:${decisionId}`);
      setDecisionErrors((prev) => ({ ...prev, [decisionId]: '' }));
      try {
        await approveDecision(decisionId, approver);
        await loadArtifacts(selectedProjectId);
      } catch (err) {
        setDecisionErrors((prev) => ({ ...prev, [decisionId]: errorMessage(err) }));
      } finally {
        setLoopBusyKey(null);
      }
    },
    [selectedProjectId, approverInputs, loadArtifacts],
  );

  const handleRejectDecision = useCallback(
    async (decisionId: string) => {
      if (!selectedProjectId) {
        return;
      }
      const approver = (approverInputs[decisionId] ?? '').trim();
      if (!approver) {
        setDecisionErrors((prev) => ({ ...prev, [decisionId]: 'Enter an approver name.' }));
        return;
      }
      setLoopBusyKey(`reject:${decisionId}`);
      setDecisionErrors((prev) => ({ ...prev, [decisionId]: '' }));
      try {
        await rejectDecision(decisionId, approver, 'Rejected via Control Tower');
        await loadArtifacts(selectedProjectId);
      } catch (err) {
        setDecisionErrors((prev) => ({ ...prev, [decisionId]: errorMessage(err) }));
      } finally {
        setLoopBusyKey(null);
      }
    },
    [selectedProjectId, approverInputs, loadArtifacts],
  );

  const handleExportAdr = useCallback(
    async (decisionId: string) => {
      if (!selectedProjectId) {
        return;
      }
      setLoopBusyKey(`adr:${decisionId}`);
      setDecisionErrors((prev) => ({ ...prev, [decisionId]: '' }));
      try {
        const page = await exportDecisionAdr(decisionId);
        setAdrResults((prev) => ({ ...prev, [decisionId]: `ADR exported to ${page.vault_path}` }));
        await loadArtifacts(selectedProjectId);
      } catch (err) {
        setDecisionErrors((prev) => ({ ...prev, [decisionId]: errorMessage(err) }));
      } finally {
        setLoopBusyKey(null);
      }
    },
    [selectedProjectId, loadArtifacts],
  );

  const handleRunDigest = useCallback(async () => {
    if (!selectedProjectId) {
      return;
    }
    setRunningDigest(true);
    setDigestsError(null);
    try {
      await runDigest(selectedProjectId);
      await loadDigests(selectedProjectId);
    } catch (err) {
      setDigestsError(errorMessage(err));
    } finally {
      setRunningDigest(false);
    }
  }, [selectedProjectId, loadDigests]);

  const handleCreateSchedule = useCallback(
    async (event: React.FormEvent) => {
      event.preventDefault();
      if (!selectedProjectId) {
        return;
      }
      const name = newScheduleName.trim();
      const intervalSeconds = Number.parseInt(newScheduleInterval, 10);
      if (!name || !Number.isFinite(intervalSeconds) || intervalSeconds <= 0) {
        return;
      }
      setCreatingSchedule(true);
      setSchedulingError(null);
      try {
        await createSchedule(selectedProjectId, {
          name,
          job_type: newScheduleJobType,
          interval_seconds: intervalSeconds,
        });
        setNewScheduleName('');
        setNewScheduleInterval('3600');
        await loadScheduling(selectedProjectId);
      } catch (err) {
        setSchedulingError(errorMessage(err));
      } finally {
        setCreatingSchedule(false);
      }
    },
    [selectedProjectId, newScheduleName, newScheduleJobType, newScheduleInterval, loadScheduling],
  );

  const handleRunSchedule = useCallback(
    async (scheduleId: string) => {
      if (!selectedProjectId) {
        return;
      }
      setSchedulingBusy(true);
      setSchedulingError(null);
      try {
        await runSchedule(scheduleId);
        await loadScheduling(selectedProjectId);
      } catch (err) {
        setSchedulingError(errorMessage(err));
      } finally {
        setSchedulingBusy(false);
      }
    },
    [selectedProjectId, loadScheduling],
  );

  const handleToggleSchedule = useCallback(
    async (schedule: Schedule) => {
      if (!selectedProjectId) {
        return;
      }
      setSchedulingBusy(true);
      setSchedulingError(null);
      try {
        await setScheduleEnabled(schedule.id, !schedule.enabled);
        await loadScheduling(selectedProjectId);
      } catch (err) {
        setSchedulingError(errorMessage(err));
      } finally {
        setSchedulingBusy(false);
      }
    },
    [selectedProjectId, loadScheduling],
  );

  const handleDeleteSchedule = useCallback(
    async (scheduleId: string) => {
      if (!selectedProjectId) {
        return;
      }
      setSchedulingBusy(true);
      setSchedulingError(null);
      try {
        await deleteSchedule(scheduleId);
        await loadScheduling(selectedProjectId);
      } catch (err) {
        setSchedulingError(errorMessage(err));
      } finally {
        setSchedulingBusy(false);
      }
    },
    [selectedProjectId, loadScheduling],
  );

  const handleEnqueueDigest = useCallback(async () => {
    if (!selectedProjectId) {
      return;
    }
    setSchedulingBusy(true);
    setSchedulingError(null);
    try {
      await enqueueJob({ project_id: selectedProjectId, job_type: 'project_digest' });
      await loadJobs(selectedProjectId);
    } catch (err) {
      setSchedulingError(errorMessage(err));
    } finally {
      setSchedulingBusy(false);
    }
  }, [selectedProjectId, loadJobs]);

  const handleEnqueueScan = useCallback(async () => {
    if (!selectedProjectId || !scanJobRepoId) {
      return;
    }
    setSchedulingBusy(true);
    setSchedulingError(null);
    try {
      await enqueueJob({
        project_id: selectedProjectId,
        repository_id: scanJobRepoId,
        job_type: 'repository_scan',
      });
      await loadJobs(selectedProjectId);
    } catch (err) {
      setSchedulingError(errorMessage(err));
    } finally {
      setSchedulingBusy(false);
    }
  }, [selectedProjectId, scanJobRepoId, loadJobs]);

  const summary = dna?.scan_summary.summary;
  const primaryLanguages =
    summary?.primary_language_hints && summary.primary_language_hints.length > 0
      ? summary.primary_language_hints
      : dna
        ? Object.keys(dna.language_mix)
        : [];

  const selectedProject = projects.find((project) => project.id === selectedProjectId) ?? null;

  // Compact runtime-health pip for the topbar (the full Runtime Health list lives
  // in the Overview view). Derives from the same health/healthError state.
  const healthPip = (
    <span
      className="aos-mono"
      style={{ display: 'inline-flex', alignItems: 'center', gap: 7, fontSize: 11, color: 'var(--ink-2)' }}
    >
      <span
        aria-hidden="true"
        style={{
          width: 8,
          height: 8,
          borderRadius: '50%',
          background: healthError ? 'var(--red)' : health ? 'var(--signal)' : 'var(--ink-3)',
          boxShadow: healthError ? undefined : 'var(--glow-soft)',
        }}
      />
      {healthError ? 'degraded' : health ? 'operational' : 'checking…'}
    </span>
  );

  // The active-project selector lives in the rail foot and persists across views.
  const projectSelector = (
    <div className="aos-rail-projects">
      <h2 className="aos-eyebrow" style={{ margin: '0 0 8px' }}>
        Projects
      </h2>
      {projectsError ? (
        <p role="alert" style={{ color: 'var(--red)', margin: '0 0 6px', fontSize: 12 }}>
          {projectsError}
        </p>
      ) : null}
      {projects.length === 0 ? (
        <p style={{ margin: '0 0 6px', color: 'var(--ink-3)', fontSize: 12 }}>
          No projects registered yet.
        </p>
      ) : null}
      <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: 4 }}>
        {projects.map((project) => {
          const selected = project.id === selectedProjectId;
          return (
            <li key={project.id}>
              <button
                type="button"
                className={selected ? 'aos-nav-item active' : 'aos-nav-item'}
                aria-current={selected ? 'true' : undefined}
                onClick={() => setSelectedProjectId(project.id)}
                style={{ fontSize: 12 }}
              >
                {project.name} — {project.status}
              </button>
            </li>
          );
        })}
      </ul>
      <form onSubmit={handleCreateProject} style={{ marginTop: 10, display: 'flex', flexDirection: 'column', gap: 6 }}>
        <input
          className="aos-input"
          type="text"
          value={newProjectName}
          placeholder="New project name"
          onChange={(event) => setNewProjectName(event.target.value)}
          style={{ fontSize: 13, padding: '8px 10px' }}
        />
        <button type="submit" className="aos-btn-ghost" disabled={creatingProject}>
          {creatingProject ? 'Creating...' : 'Create project'}
        </button>
      </form>
    </div>
  );

  // Each view relocates the pre-existing section JSX verbatim, wrapped in a
  // light `.aos-legacy` panel so the un-restyled inline-styled markup stays
  // legible on the dark deck. The Reuse view renders native `.aos-*` bare.
  const renderView = (): React.ReactNode => {
    switch (activeView) {
      case 'command':
        return <CommandDeck projectId={selectedProjectId} projectName={selectedProject?.name ?? null} />;

      case 'overview':
        return (
          <div className="aos-view">
            <div className="aos-view-head">
              <span className="aos-eyebrow">Control Tower</span>
              <h2>Overview</h2>
            </div>
            <div className="aos-hud glass aos-card">
              <span className="aos-eyebrow">Runtime health</span>
              {healthError ? (
                <p role="alert" className="aos-error">
                  Health unavailable: {healthError}
                </p>
              ) : health ? (
                <div className="aos-pills">
                  <span className={`aos-pill ${health.api ? 'good' : 'risk'}`}>API {health.api ? 'ok' : 'down'}</span>
                  <span className={`aos-pill ${health.database ? 'good' : 'risk'}`}>Postgres {health.database ? 'ok' : 'down'}</span>
                  <span className={`aos-pill ${health.redis ? 'good' : 'risk'}`}>Redis {health.redis ? 'ok' : 'down'}</span>
                </div>
              ) : (
                <p className="aos-muted" style={{ margin: 0 }}>Loading health…</p>
              )}
            </div>
            <div className="aos-hud glass aos-card">
              <span className="aos-eyebrow">Active project</span>
              {selectedProject ? (
                <p style={{ margin: 0, color: 'var(--ink-2)' }}>
                  <span className="aos-strong">{selectedProject.name}</span> — {selectedProject.status}.
                  Use the rail to move between Repositories, Council &amp; Decisions, Digest and more.
                </p>
              ) : (
                <p style={{ margin: 0, color: 'var(--ink-2)' }}>
                  No project selected. Create or select one in the rail foot to begin.
                </p>
              )}
              <p className="aos-mono aos-muted" style={{ marginTop: 12, fontSize: 12 }}>
                Voice inbox text capture — planned (v0.1).
              </p>
            </div>
          </div>
        );

      case 'knowledge':
        return (
          <section className="aos-view">
            <div className="aos-view-head">
              <span className="aos-eyebrow">Engineering memory</span>
              <h2>Knowledge</h2>
            </div>
            <div className="aos-hud glass aos-card">
              <span className="aos-eyebrow">Lessons vault</span>
              {knowledgeError ? (
                <p role="alert" className="aos-error">
                  Knowledge unavailable: {knowledgeError}
                </p>
              ) : null}
              <div className="aos-form-row" style={{ marginTop: 0 }}>
                <button
                  type="button"
                  className="aos-btn aos-btn-sm"
                  disabled={knowledgeSyncing}
                  onClick={() => void handleSyncKnowledge()}
                >
                  {knowledgeSyncing ? 'Syncing...' : 'Sync from vault'}
                </button>
                {knowledgeSyncSummary ? (
                  <span className="aos-mono aos-muted">{knowledgeSyncSummary}</span>
                ) : null}
              </div>
              <div className="aos-form-row">
                <button
                  type="button"
                  className={knowledgeFilter === 'all' ? 'aos-mchip on' : 'aos-mchip'}
                  onClick={() => setKnowledgeFilter('all')}
                >
                  All
                </button>
                <button
                  type="button"
                  className={knowledgeFilter === 'open' ? 'aos-mchip on' : 'aos-mchip'}
                  onClick={() => setKnowledgeFilter('open')}
                >
                  Open
                </button>
              </div>
              {knowledgePages.length === 0 ? (
                <p className="aos-muted" style={{ margin: '12px 0 0' }}>
                  No knowledge pages yet. Sync from the vault to load lessons.
                </p>
              ) : (
                <ul className="aos-rows" style={{ marginTop: 12 }}>
                  {knowledgePages.map((page) => {
                    const isOpen = page.validation_state === 'open';
                    return (
                      <li key={page.id}>
                        {isOpen ? <span className="aos-pill risk">open</span> : null}
                        <span className={isOpen ? 'aos-strong' : undefined}>{page.title}</span>{' '}
                        <span className="aos-rowmeta">
                          ({page.page_type} · {page.validation_state})
                        </span>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>
          </section>
        );

      case 'reuse':
        return <ReuseView projectId={selectedProjectId} />;

      case 'providers':
        return <ProvidersView />;

      case 'approvals':
        return <ApprovalsView />;

      case 'activity':
        return <ActivityView />;

      case 'research':
        return <ResearchInboxView />;

      case 'voice-inbox':
        return <VoiceInboxView />;

      case 'repositories':
        if (!selectedProjectId) {
          return <SelectProjectNotice />;
        }
        return (
          <div className="aos-view">
            <div className="aos-view-head">
              <span className="aos-eyebrow">Portfolio</span>
              <h2>Repositories</h2>
            </div>
            <div className="aos-hud glass aos-card">
              <span className="aos-eyebrow">Registered repositories</span>
              {repositoriesError ? <p role="alert" className="aos-error">{repositoriesError}</p> : null}
              {repositories.length === 0 ? (
                <p className="aos-muted" style={{ margin: 0 }}>No repositories registered yet.</p>
              ) : (
                <table className="aos-table">
                  <thead>
                    <tr>
                      <th>Name</th>
                      <th>Local path</th>
                      <th>Last scanned</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {repositories.map((repository) => {
                      const selected = repository.id === selectedRepositoryId;
                      return (
                        <tr key={repository.id} className={selected ? 'sel' : undefined}>
                          <td>
                            <button
                              type="button"
                              className={`aos-linkbtn${selected ? ' sel' : ''}`}
                              onClick={() => setSelectedRepositoryId(repository.id)}
                            >
                              {repository.name}
                            </button>
                          </td>
                          <td>{repository.local_path}</td>
                          <td>{repository.last_scanned_at ?? 'never'}</td>
                          <td>
                            <button
                              type="button"
                              className="aos-btn aos-btn-sm"
                              disabled={scanningRepoId === repository.id}
                              onClick={() => void handleScan(repository.id)}
                            >
                              {scanningRepoId === repository.id ? 'Scanning...' : 'Run scan'}
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              )}
              <form onSubmit={handleRegisterRepository} className="aos-form-row">
                <input
                  className="aos-input"
                  type="text"
                  value={newRepoName}
                  placeholder="Repository name"
                  onChange={(event) => setNewRepoName(event.target.value)}
                  style={{ width: 'auto', flex: '1 1 180px' }}
                />
                <input
                  className="aos-input"
                  type="text"
                  value={newRepoPath}
                  placeholder="Local path"
                  onChange={(event) => setNewRepoPath(event.target.value)}
                  style={{ width: 'auto', flex: '1 1 180px' }}
                />
                <button type="submit" className="aos-btn aos-btn-sm" disabled={registeringRepo}>
                  {registeringRepo ? 'Registering...' : 'Register repository'}
                </button>
              </form>
            </div>

            {selectedRepositoryId ? (
              <div className="aos-hud glass aos-card">
                <span className="aos-eyebrow">Scan summary</span>
                {dnaError ? <p role="alert" className="aos-error">{dnaError}</p> : null}
                {dnaLoading ? <p className="aos-muted" style={{ margin: 0 }}>Loading scan summary…</p> : null}
                {!dnaLoading && !dnaError && dna === null ? (
                  <p className="aos-muted" style={{ margin: 0 }}>No scan recorded yet.</p>
                ) : null}
                {dna ? (
                  <>
                    <dl className="aos-kv">
                      <dt>Primary languages</dt>
                      <dd className="aos-mono">{primaryLanguages.length > 0 ? primaryLanguages.join(', ') : 'none'}</dd>
                      <dt>Package managers</dt>
                      <dd className="aos-mono">{dna.package_managers.length > 0 ? dna.package_managers.join(', ') : 'none'}</dd>
                      <dt>Confidence</dt>
                      <dd className="aos-mono">{dna.confidence}</dd>
                    </dl>
                    <h3>Signals</h3>
                    <div className="aos-pills">
                      <span className={`aos-pill ${summary?.has_docker ? 'good' : ''}`}>Docker: {summary?.has_docker ? 'yes' : 'no'}</span>
                      <span className={`aos-pill ${summary?.has_ci ? 'good' : ''}`}>CI: {summary?.has_ci ? 'yes' : 'no'}</span>
                      <span className={`aos-pill ${summary?.has_tests ? 'good' : ''}`}>Tests: {summary?.has_tests ? 'yes' : 'no'}</span>
                      <span className={`aos-pill ${summary?.has_env_example ? 'good' : ''}`}>Env example: {summary?.has_env_example ? 'yes' : 'no'}</span>
                    </div>
                    <h3>Risk flags</h3>
                    {dna.risk_flags.length > 0 ? (
                      <div className="aos-pills">
                        {dna.risk_flags.map((flag, index) => (
                          <span key={index} className="aos-pill risk">{flag}</span>
                        ))}
                      </div>
                    ) : (
                      <p className="aos-muted" style={{ margin: 0 }}>No risk flags.</p>
                    )}
                  </>
                ) : null}
              </div>
            ) : null}
          </div>
        );

      case 'architecture':
        if (!selectedProjectId) {
          return <SelectProjectNotice />;
        }
        if (!selectedRepositoryId) {
          return (
            <div className="aos-view">
              <div className="aos-view-head">
                <span className="aos-eyebrow">System map</span>
                <h2>Architecture</h2>
              </div>
              <div className="aos-hud glass aos-card">
                <p className="aos-muted" style={{ margin: 0 }}>
                  Select a repository in the Repositories view and run a scan to load its architecture.
                </p>
              </div>
            </div>
          );
        }
        return (
          <div className="aos-view">
            <div className="aos-view-head">
              <span className="aos-eyebrow">System map</span>
              <h2>Architecture</h2>
            </div>
            <div className="aos-hud glass aos-card">
              <span className="aos-eyebrow">Dependency graph</span>
              {architectureError ? (
                <p role="alert" className="aos-error">
                  {architectureError}
                </p>
              ) : null}
              {architecture ? (
                <>
                  <div className="aos-pills">
                    <span className="aos-pill good">Nodes: {architecture.nodes.length}</span>
                    <span className="aos-pill good">Edges: {architecture.edges.length}</span>
                  </div>
                  <ul className="aos-rows" style={{ marginTop: 12 }}>
                    {architecture.nodes.map((node) => (
                      <li key={node.id}>
                        <span className="aos-strong">{node.label}</span>{' '}
                        <span className="aos-rowmeta">
                          ({node.type}) — confidence {node.confidence}
                        </span>
                      </li>
                    ))}
                  </ul>
                </>
              ) : !architectureError ? (
                <p className="aos-muted" style={{ margin: 0 }}>Loading architecture...</p>
              ) : null}
            </div>
          </div>
        );

      case 'council':
        if (!selectedProjectId) {
          return <SelectProjectNotice />;
        }
        return (
          <section className="aos-view">
            <div className="aos-view-head">
              <span className="aos-eyebrow">Governance</span>
              <h2>Decisions &amp; Research</h2>
            </div>
            {artifactsError ? (
              <p role="alert" className="aos-error">
                {artifactsError}
              </p>
            ) : null}

            <div className="aos-hud glass aos-card">
              <h3 style={{ margin: '0 0 10px' }}>Decision Loop</h3>
              {councilError ? (
                <p role="alert" className="aos-error">
                  {councilError}
                </p>
              ) : null}
              <form onSubmit={handleEnqueueCouncilReview} className="aos-form-row" style={{ marginTop: 0 }}>
                <input
                  className="aos-input"
                  type="text"
                  value={councilQuestion}
                  placeholder="Council question"
                  onChange={(event) => setCouncilQuestion(event.target.value)}
                  style={{ width: 'auto', flex: '1 1 240px' }}
                />
                <button type="submit" className="aos-btn aos-btn-sm" disabled={councilBusy}>
                  {councilBusy ? 'Enqueuing...' : 'Enqueue council review'}
                </button>
                <button
                  type="button"
                  className="aos-btn-ghost aos-btn-sm"
                  onClick={() => void handleRefreshLoop()}
                >
                  Refresh reviews
                </button>
              </form>

              <h3>Council Reviews</h3>
              {councilReviews.length === 0 ? (
                <p className="aos-muted" style={{ margin: 0 }}>
                  No council reviews yet. Enqueue one — the worker produces it asynchronously, then
                  click Refresh reviews.
                </p>
              ) : (
                <ul className="aos-rows">
                  {councilReviews.map((review) => {
                    const drafting = loopBusyKey === `draft:${review.id}`;
                    return (
                      <li key={review.id}>
                        <span>
                          {review.verdict} — confidence {review.confidence}
                          {review.question ? ` · ${review.question}` : ''}
                        </span>
                        <button
                          type="button"
                          className="aos-btn-ghost aos-btn-sm"
                          disabled={drafting}
                          onClick={() => void handleDraftDecision(review.id)}
                        >
                          {drafting ? 'Drafting...' : 'Draft decision'}
                        </button>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>

            <div className="aos-hud glass aos-card">
              <span className="aos-eyebrow">Decisions</span>
              {decisions.length === 0 ? (
                <p className="aos-muted" style={{ margin: 0 }}>No decisions yet.</p>
              ) : (
                <ul className="aos-rows">
                  {decisions.map((decision) => {
                    const linkedResearch = decision.evidence.filter(
                      (entry) => entry.type === 'research_note',
                    ).length;
                    const governed =
                      decision.status === 'draft' || decision.status === 'needs_evidence';
                    const approveBusy = loopBusyKey === `approve:${decision.id}`;
                    const rejectBusy = loopBusyKey === `reject:${decision.id}`;
                    const adrBusy = loopBusyKey === `adr:${decision.id}`;
                    const inlineError = decisionErrors[decision.id];
                    const adrResult = adrResults[decision.id];
                    return (
                      <li key={decision.id} data-testid="decision-row">
                        <DecisionStatusBadge status={decision.status} />
                        <span>
                          {decision.title} — confidence {decision.confidence} · {linkedResearch} linked
                          research
                        </span>
                        {decision.approved_by ? (
                          <span className="aos-rowmeta"> · approved by {decision.approved_by}</span>
                        ) : null}
                        {governed ? (
                          <div className="aos-form-row" style={{ flexBasis: '100%', marginTop: 6 }}>
                            {decision.status === 'needs_evidence' ? (
                              <p className="aos-muted" style={{ flexBasis: '100%', margin: 0 }}>
                                Drafted from an abstained review — gather evidence and re-draft before
                                approval.
                              </p>
                            ) : null}
                            <input
                              className="aos-input"
                              type="text"
                              value={approverInputs[decision.id] ?? ''}
                              placeholder="Approver name"
                              onChange={(event) =>
                                setApproverInputs((prev) => ({
                                  ...prev,
                                  [decision.id]: event.target.value,
                                }))
                              }
                              style={{ width: 'auto', flex: '1 1 180px' }}
                            />
                            <button
                              type="button"
                              className="aos-btn aos-btn-sm"
                              disabled={approveBusy}
                              onClick={() => void handleApproveDecision(decision.id)}
                            >
                              {approveBusy ? 'Approving...' : 'Approve'}
                            </button>
                            <button
                              type="button"
                              className="aos-btn-ghost aos-btn-sm"
                              disabled={rejectBusy}
                              onClick={() => void handleRejectDecision(decision.id)}
                            >
                              {rejectBusy ? 'Rejecting...' : 'Reject'}
                            </button>
                          </div>
                        ) : null}
                        {decision.status === 'approved' ? (
                          <div className="aos-form-row" style={{ flexBasis: '100%', marginTop: 6 }}>
                            <button
                              type="button"
                              className="aos-btn aos-btn-sm"
                              disabled={adrBusy}
                              onClick={() => void handleExportAdr(decision.id)}
                            >
                              {adrBusy ? 'Exporting...' : 'Export ADR'}
                            </button>
                          </div>
                        ) : null}
                        {adrResult ? (
                          <p className="aos-mono aos-muted" style={{ flexBasis: '100%', margin: '4px 0 0' }}>
                            {adrResult}
                          </p>
                        ) : null}
                        {inlineError ? (
                          <p role="alert" className="aos-error" style={{ flexBasis: '100%', margin: '4px 0 0' }}>
                            {inlineError}
                          </p>
                        ) : null}
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>

            <div className="aos-hud glass aos-card">
              <span className="aos-eyebrow">Research &amp; recommendations</span>
              <h3 style={{ marginTop: 0 }}>Research Notes</h3>
              {researchNotes.length === 0 ? (
                <p className="aos-muted" style={{ margin: 0 }}>No research notes yet.</p>
              ) : (
                <ul className="aos-rows">
                  {researchNotes.map((note) => (
                    <li key={note.id}>
                      <span>{note.title}</span>{' '}
                      <span className="aos-rowmeta">{note.freshness ?? 'unset'}</span>
                    </li>
                  ))}
                </ul>
              )}

              <h3>Recommendations</h3>
              {recommendations.length === 0 ? (
                <p className="aos-muted" style={{ margin: 0 }}>No recommendations yet.</p>
              ) : (
                <ul className="aos-rows">
                  {recommendations.map((recommendation) => (
                    <li key={recommendation.id}>
                      <span>{recommendation.title}</span>{' '}
                      <span className="aos-rowmeta">{recommendation.evidence.length} evidence items</span>
                    </li>
                  ))}
                </ul>
              )}

              <form onSubmit={handleCreateResearchNote} className="aos-form-row">
                <input
                  className="aos-input"
                  type="text"
                  value={newNoteTitle}
                  placeholder="Research note title"
                  onChange={(event) => setNewNoteTitle(event.target.value)}
                  style={{ width: 'auto', flex: '1 1 200px' }}
                />
                <input
                  className="aos-input"
                  type="text"
                  value={newNoteSummary}
                  placeholder="Summary"
                  onChange={(event) => setNewNoteSummary(event.target.value)}
                  style={{ width: 'auto', flex: '1 1 200px' }}
                />
                <button type="submit" className="aos-btn aos-btn-sm" disabled={creatingNote}>
                  {creatingNote ? 'Adding...' : 'Add research note'}
                </button>
              </form>

              <form onSubmit={handleCreateDecision} className="aos-form-row">
                <input
                  className="aos-input"
                  type="text"
                  value={newDecisionTitle}
                  placeholder="Decision title"
                  onChange={(event) => setNewDecisionTitle(event.target.value)}
                  style={{ width: 'auto', flex: '1 1 200px' }}
                />
                <input
                  className="aos-input"
                  type="text"
                  value={newDecisionText}
                  placeholder="Decision text"
                  onChange={(event) => setNewDecisionText(event.target.value)}
                  style={{ width: 'auto', flex: '1 1 200px' }}
                />
                <select
                  className="aos-input"
                  value={newDecisionNoteId}
                  onChange={(event) => setNewDecisionNoteId(event.target.value)}
                  style={{ width: 'auto' }}
                >
                  <option value="">No linked research</option>
                  {researchNotes.map((note) => (
                    <option key={note.id} value={note.id}>
                      {note.title}
                    </option>
                  ))}
                </select>
                <button type="submit" className="aos-btn aos-btn-sm" disabled={creatingDecision}>
                  {creatingDecision ? 'Adding...' : 'Add decision'}
                </button>
              </form>
            </div>

            <div className="aos-view-head" style={{ marginTop: 8 }}>
              <span className="aos-eyebrow">Multi-agent review</span>
              <h2>Agent Council</h2>
            </div>
            <div className="aos-hud glass aos-card">
              <span className="aos-eyebrow">Council reviews</span>
              {councilSectionError ? (
                <p role="alert" className="aos-error">
                  {councilSectionError}
                </p>
              ) : null}
              <div className="aos-form-row" style={{ marginTop: 0 }}>
                <button
                  type="button"
                  className="aos-btn aos-btn-sm"
                  disabled={councilSectionLoading}
                  onClick={() => void handleRefreshCouncilSection()}
                >
                  {councilSectionLoading ? 'Loading...' : 'Refresh council'}
                </button>
              </div>
              {councilReviews.length === 0 ? (
                <p className="aos-muted" style={{ margin: '12px 0 0' }}>
                  No council reviews yet. Use the Decision Loop to enqueue one.
                </p>
              ) : (
                <ul className="aos-rows" style={{ marginTop: 12 }}>
                  {councilReviews.map((review) => {
                    const isExpanded = councilExpandedId === review.id;
                    const isDetailLoading = councilDetailLoading === review.id;
                    const detailErr = councilDetailError[review.id];
                    const detail = councilDetailMap[review.id];
                    return (
                      <li key={review.id} data-testid="council-review-row">
                        <VerdictBadge verdict={review.verdict} />
                        <span>confidence {review.confidence}</span>
                        {review.question ? (
                          <span className="aos-rowmeta">&middot; {review.question}</span>
                        ) : null}
                        {review.provider ? (
                          <span className="aos-rowmeta">&middot; {review.provider}</span>
                        ) : null}
                        <button
                          type="button"
                          className="aos-btn-ghost aos-btn-sm"
                          aria-expanded={isExpanded}
                          onClick={() => void handleExpandReview(review.id)}
                        >
                          {isExpanded ? 'Hide details' : 'Show details'}
                        </button>
                        {isExpanded ? (
                          <div
                            data-testid="council-detail-panel"
                            className="aos-subrows"
                            style={{
                              flexBasis: '100%',
                              paddingLeft: 14,
                              marginTop: 8,
                              borderLeft: '2px solid var(--frame)',
                            }}
                          >
                            {isDetailLoading ? (
                              <p className="aos-muted" style={{ margin: 0 }}>Loading details...</p>
                            ) : null}
                            {detailErr ? (
                              <p role="alert" className="aos-error">
                                {detailErr}
                              </p>
                            ) : null}
                            {detail ? (
                              <div>
                                <h3 style={{ marginTop: 0 }}>Final Judge</h3>
                                <p>
                                  <span className="aos-strong">Verdict:</span> {detail.verdict} &middot;{' '}
                                  <span className="aos-strong">Confidence:</span> {detail.confidence}
                                </p>
                                {(detail.agreements ?? []).length > 0 ? (
                                  <div>
                                    <span className="aos-strong">Agreements:</span>
                                    <ul className="aos-subrows">
                                      {(detail.agreements ?? []).map((item, i) => (
                                        <li key={i}>{renderListItem(item)}</li>
                                      ))}
                                    </ul>
                                  </div>
                                ) : null}
                                {(detail.disagreements ?? []).length > 0 ? (
                                  <div>
                                    <span className="aos-strong">Disagreements:</span>
                                    <ul className="aos-subrows">
                                      {(detail.disagreements ?? []).map((item, i) => (
                                        <li key={i}>{renderListItem(item)}</li>
                                      ))}
                                    </ul>
                                  </div>
                                ) : null}
                                {(detail.unsupported_claims ?? []).length > 0 ? (
                                  <div>
                                    <span className="aos-strong">Unsupported claims:</span>
                                    <ul className="aos-subrows">
                                      {(detail.unsupported_claims ?? []).map((item, i) => (
                                        <li key={i}>{renderListItem(item)}</li>
                                      ))}
                                    </ul>
                                  </div>
                                ) : null}
                                {(detail.follow_up ?? []).length > 0 ? (
                                  <div>
                                    <span className="aos-strong">Follow-up:</span>
                                    <ul className="aos-subrows">
                                      {(detail.follow_up ?? []).map((item, i) => (
                                        <li key={i}>{renderListItem(item)}</li>
                                      ))}
                                    </ul>
                                  </div>
                                ) : null}
                                {(detail.agent_outputs ?? []).length > 0 ? (
                                  <div style={{ marginTop: 8 }}>
                                    <h3>Agent Outputs</h3>
                                    {(detail.agent_outputs ?? []).map((output) => (
                                      <div
                                        key={output.id}
                                        data-testid="council-agent-card"
                                        className="aos-card"
                                        style={{
                                          marginBottom: 8,
                                          padding: 12,
                                          border: '1px solid var(--frame)',
                                          borderRadius: 6,
                                          background: 'var(--panel-2)',
                                        }}
                                      >
                                        <p style={{ margin: '0 0 6px' }}>
                                          <span className="aos-strong">{output.agent_name}</span>{' '}
                                          <span className="aos-rowmeta">({output.agent_type})</span>{' '}
                                          &middot; status: {output.status} &middot; confidence{' '}
                                          {output.confidence}
                                          {output.agent_model ? (
                                            <>
                                              {' '}
                                              <span
                                                className="aos-pill info"
                                                data-testid="council-agent-model"
                                                title="Model that produced this agent's output"
                                                style={{ marginLeft: 4 }}
                                              >
                                                {output.agent_model}
                                              </span>
                                            </>
                                          ) : null}
                                        </p>
                                        {output.summary ? (
                                          <p style={{ margin: '0 0 6px' }}>{output.summary}</p>
                                        ) : null}
                                        {output.findings.length > 0 ? (
                                          <div>
                                            <span className="aos-strong">Findings:</span>
                                            <ul className="aos-subrows" style={{ margin: '0 0 4px' }}>
                                              {output.findings.map((item, i) => (
                                                <li key={i}>{renderListItem(item)}</li>
                                              ))}
                                            </ul>
                                          </div>
                                        ) : null}
                                        {output.evidence.length > 0 ? (
                                          <div>
                                            <span className="aos-strong">Evidence:</span>
                                            <ul className="aos-subrows" style={{ margin: '0 0 4px' }}>
                                              {output.evidence.map((item, i) => (
                                                <li key={i}>{renderListItem(item)}</li>
                                              ))}
                                            </ul>
                                          </div>
                                        ) : null}
                                        {output.concerns.length > 0 ? (
                                          <div>
                                            <span className="aos-strong">Concerns:</span>
                                            <ul className="aos-subrows" style={{ margin: '0 0 4px' }}>
                                              {output.concerns.map((item, i) => (
                                                <li key={i}>{renderListItem(item)}</li>
                                              ))}
                                            </ul>
                                          </div>
                                        ) : null}
                                      </div>
                                    ))}
                                  </div>
                                ) : null}
                              </div>
                            ) : null}
                          </div>
                        ) : null}
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>
          </section>
        );

      case 'digest':
        if (!selectedProjectId) {
          return <SelectProjectNotice />;
        }
        return (
          <div className="aos-view">
            <div className="aos-view-head">
              <span className="aos-eyebrow">Automation</span>
              <h2>Nightly Digest</h2>
            </div>
            <div className="aos-hud glass aos-card">
              <span className="aos-eyebrow">Digest runs</span>
              {digestsError ? (
                <p role="alert" className="aos-error">
                  {digestsError}
                </p>
              ) : null}
              <div className="aos-form-row" style={{ marginTop: 0 }}>
                <button
                  type="button"
                  className="aos-btn aos-btn-sm"
                  disabled={runningDigest}
                  onClick={() => void handleRunDigest()}
                >
                  {runningDigest ? 'Running...' : 'Run digest'}
                </button>
              </div>
              {digests.length === 0 ? (
                <p className="aos-muted" style={{ margin: '12px 0 0' }}>No digests yet.</p>
              ) : (
                <ul className="aos-rows" style={{ marginTop: 12 }}>
                  {digests.map((digest, index) => (
                    <li key={digest.id}>
                      <span className="aos-rowmeta">
                        {new Date(digest.digest_date).toLocaleDateString()}
                      </span>{' '}
                      <span>{digest.summary ?? 'no summary'}</span>
                      {index === 0 && digest.recommendations.length > 0 ? (
                        <ul className="aos-subrows">
                          {digest.recommendations.map((recommendation, recIndex) => (
                            <li key={recIndex}>
                              <span className="aos-strong">{recommendation.title ?? 'Untitled'}</span> —{' '}
                              {recommendation.reason ?? ''}
                            </li>
                          ))}
                        </ul>
                      ) : null}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        );

      case 'scheduling':
        if (!selectedProjectId) {
          return <SelectProjectNotice />;
        }
        return (
          <div className="aos-view">
            <div className="aos-view-head">
              <span className="aos-eyebrow">Automation</span>
              <h2>Scheduling &amp; Jobs</h2>
            </div>

            <div className="aos-hud glass aos-card">
              <span className="aos-eyebrow">Schedules</span>
              {schedulingError ? (
                <p role="alert" className="aos-error">
                  {schedulingError}
                </p>
              ) : null}
              {schedules.length === 0 ? (
                <p className="aos-muted" style={{ margin: 0 }}>No schedules yet.</p>
              ) : (
                <ul className="aos-rows">
                  {schedules.map((schedule) => (
                    <li key={schedule.id}>
                      <span>
                        {schedule.name} — {schedule.job_type} — every {schedule.interval_seconds}s —{' '}
                        {schedule.enabled ? 'enabled' : 'disabled'} — next{' '}
                        {new Date(schedule.next_run_at).toLocaleString()}
                      </span>
                      <button
                        type="button"
                        className="aos-btn-ghost aos-btn-sm"
                        disabled={schedulingBusy}
                        onClick={() => void handleToggleSchedule(schedule)}
                      >
                        {schedule.enabled ? 'Disable' : 'Enable'}
                      </button>
                      <button
                        type="button"
                        className="aos-btn aos-btn-sm"
                        disabled={schedulingBusy}
                        onClick={() => void handleRunSchedule(schedule.id)}
                      >
                        Run now
                      </button>
                      <button
                        type="button"
                        className="aos-btn-ghost aos-btn-sm"
                        disabled={schedulingBusy}
                        onClick={() => void handleDeleteSchedule(schedule.id)}
                      >
                        Delete
                      </button>
                    </li>
                  ))}
                </ul>
              )}

              <form onSubmit={handleCreateSchedule} className="aos-form-row">
                <input
                  className="aos-input"
                  type="text"
                  value={newScheduleName}
                  placeholder="Schedule name"
                  onChange={(event) => setNewScheduleName(event.target.value)}
                  style={{ width: 'auto', flex: '1 1 180px' }}
                />
                <select
                  className="aos-input"
                  value={newScheduleJobType}
                  onChange={(event) => setNewScheduleJobType(event.target.value)}
                  style={{ width: 'auto' }}
                >
                  <option value="repository_scan">repository_scan</option>
                  <option value="project_digest">project_digest</option>
                </select>
                <input
                  className="aos-input"
                  type="number"
                  value={newScheduleInterval}
                  placeholder="Interval seconds"
                  onChange={(event) => setNewScheduleInterval(event.target.value)}
                  style={{ width: 140 }}
                />
                <button type="submit" className="aos-btn aos-btn-sm" disabled={creatingSchedule}>
                  {creatingSchedule ? 'Creating...' : 'Create schedule'}
                </button>
              </form>
            </div>

            <div className="aos-hud glass aos-card">
              <span className="aos-eyebrow">Enqueue now</span>
              <div className="aos-form-row" style={{ marginTop: 0 }}>
                <button
                  type="button"
                  className="aos-btn aos-btn-sm"
                  disabled={schedulingBusy}
                  onClick={() => void handleEnqueueDigest()}
                >
                  Enqueue digest job
                </button>
                <select
                  className="aos-input"
                  value={scanJobRepoId}
                  onChange={(event) => setScanJobRepoId(event.target.value)}
                  style={{ width: 'auto' }}
                >
                  <option value="">Select repository</option>
                  {repositories.map((repository) => (
                    <option key={repository.id} value={repository.id}>
                      {repository.name}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  className="aos-btn aos-btn-sm"
                  disabled={schedulingBusy || !scanJobRepoId}
                  onClick={() => void handleEnqueueScan()}
                >
                  Enqueue scan job
                </button>
              </div>
            </div>

            <div className="aos-hud glass aos-card">
              <span className="aos-eyebrow">Job history</span>
              <div className="aos-form-row" style={{ marginTop: 0 }}>
                <button
                  type="button"
                  className="aos-btn-ghost aos-btn-sm"
                  disabled={schedulingBusy}
                  onClick={() => selectedProjectId && void loadJobs(selectedProjectId)}
                >
                  Refresh jobs
                </button>
              </div>
              {jobs.length === 0 ? (
                <p className="aos-muted" style={{ margin: '12px 0 0' }}>No jobs yet.</p>
              ) : (
                <ul className="aos-rows" style={{ marginTop: 12 }}>
                  {jobs.map((job) => (
                    <li key={job.id}>
                      {job.job_type} — {job.status} — {new Date(job.queued_at).toLocaleString()} —
                      attempts {job.attempts}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <Shell
      activeView={activeView}
      onNav={setActiveView}
      modes={WORKSPACE_MODES}
      projectSelector={projectSelector}
      health={healthPip}
    >
      {renderView()}
    </Shell>
  );
}

createRoot(document.getElementById('root')!).render(<App />);
