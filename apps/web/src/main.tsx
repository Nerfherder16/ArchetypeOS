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

const errorMessage = (err: unknown): string =>
  err instanceof Error ? err.message : 'Request failed';

const sectionStyle: React.CSSProperties = {
  marginTop: 24,
  paddingTop: 16,
  borderTop: '1px solid #ddd',
};

const errorStyle: React.CSSProperties = { color: '#b00020' };

// Palette for the decision-loop status badge; unknown statuses fall back to grey.
const DECISION_STATUS_COLORS: Record<string, { color: string; background: string; border: string }> = {
  draft: { color: '#1d4ed8', background: '#dbeafe', border: '#3b82f6' },
  needs_evidence: { color: '#b45309', background: '#fef3c7', border: '#f59e0b' },
  approved: { color: '#166534', background: '#dcfce7', border: '#22c55e' },
  rejected: { color: '#b91c1c', background: '#fee2e2', border: '#ef4444' },
  active: { color: '#4b5563', background: '#f3f4f6', border: '#9ca3af' },
};

function DecisionStatusBadge({ status }: { status: string }) {
  const palette = DECISION_STATUS_COLORS[status] ?? DECISION_STATUS_COLORS.active;
  return (
    <span
      style={{
        display: 'inline-block',
        marginRight: 8,
        padding: '1px 8px',
        borderRadius: 10,
        fontSize: 12,
        fontWeight: 600,
        color: palette.color,
        background: palette.background,
        border: `1px solid ${palette.border}`,
      }}
    >
      {status}
    </span>
  );
}

function App() {
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

  return (
    <main style={{ fontFamily: 'system-ui, sans-serif', padding: 24, maxWidth: 900 }}>
      <header>
        <h1 style={{ marginBottom: 4 }}>ArchetypeOS</h1>
        <p style={{ margin: 0, color: '#555' }}>Engineering Control Tower</p>
      </header>

      <section style={sectionStyle}>
        <h2>Runtime Health</h2>
        {healthError ? (
          <p role="alert" style={errorStyle}>
            Health unavailable: {healthError}
          </p>
        ) : health ? (
          <ul>
            <li>API: {health.api ? 'ok' : 'down'}</li>
            <li>Postgres: {health.database ? 'ok' : 'down'}</li>
            <li>Redis: {health.redis ? 'ok' : 'down'}</li>
          </ul>
        ) : (
          <p>Loading health...</p>
        )}
      </section>

      <section style={sectionStyle}>
        <h2>Knowledge</h2>
        {knowledgeError ? (
          <p role="alert" style={errorStyle}>
            Knowledge unavailable: {knowledgeError}
          </p>
        ) : null}
        <div>
          <button
            type="button"
            disabled={knowledgeSyncing}
            onClick={() => void handleSyncKnowledge()}
          >
            {knowledgeSyncing ? 'Syncing...' : 'Sync from vault'}
          </button>
          {knowledgeSyncSummary ? (
            <span style={{ marginLeft: 8, color: '#555' }}>{knowledgeSyncSummary}</span>
          ) : null}
        </div>
        <div style={{ marginTop: 8 }}>
          <button
            type="button"
            onClick={() => setKnowledgeFilter('all')}
            style={{
              cursor: 'pointer',
              padding: '4px 10px',
              border: knowledgeFilter === 'all' ? '2px solid #0b57d0' : '1px solid #ccc',
              background: knowledgeFilter === 'all' ? '#e8f0fe' : '#fff',
              fontWeight: knowledgeFilter === 'all' ? 600 : 400,
            }}
          >
            All
          </button>
          <button
            type="button"
            onClick={() => setKnowledgeFilter('open')}
            style={{
              cursor: 'pointer',
              marginLeft: 8,
              padding: '4px 10px',
              border: knowledgeFilter === 'open' ? '2px solid #0b57d0' : '1px solid #ccc',
              background: knowledgeFilter === 'open' ? '#e8f0fe' : '#fff',
              fontWeight: knowledgeFilter === 'open' ? 600 : 400,
            }}
          >
            Open
          </button>
        </div>
        {knowledgePages.length === 0 ? (
          <p>No knowledge pages yet. Sync from the vault to load lessons.</p>
        ) : (
          <ul style={{ listStyle: 'none', padding: 0, marginTop: 8 }}>
            {knowledgePages.map((page) => {
              const isOpen = page.validation_state === 'open';
              return (
                <li key={page.id} style={{ marginBottom: 6 }}>
                  {isOpen ? (
                    <span
                      style={{
                        display: 'inline-block',
                        marginRight: 8,
                        padding: '1px 8px',
                        borderRadius: 10,
                        fontSize: 12,
                        fontWeight: 600,
                        color: '#b45309',
                        background: '#fef3c7',
                        border: '1px solid #f59e0b',
                      }}
                    >
                      open
                    </span>
                  ) : null}
                  <span style={{ fontWeight: isOpen ? 600 : 400 }}>{page.title}</span>{' '}
                  <span style={{ color: '#777' }}>
                    ({page.page_type} · {page.validation_state})
                  </span>
                </li>
              );
            })}
          </ul>
        )}
      </section>

      <section style={sectionStyle}>
        <h2>Projects</h2>
        {projectsError ? (
          <p role="alert" style={errorStyle}>
            {projectsError}
          </p>
        ) : null}
        {projects.length === 0 ? <p>No projects registered yet.</p> : null}
        <ul style={{ listStyle: 'none', padding: 0 }}>
          {projects.map((project) => {
            const selected = project.id === selectedProjectId;
            return (
              <li key={project.id} style={{ marginBottom: 4 }}>
                <button
                  type="button"
                  onClick={() => setSelectedProjectId(project.id)}
                  style={{
                    cursor: 'pointer',
                    padding: '6px 10px',
                    border: selected ? '2px solid #0b57d0' : '1px solid #ccc',
                    background: selected ? '#e8f0fe' : '#fff',
                    fontWeight: selected ? 600 : 400,
                  }}
                >
                  {project.name} — {project.status}
                </button>
              </li>
            );
          })}
        </ul>
        <form onSubmit={handleCreateProject} style={{ marginTop: 8 }}>
          <input
            type="text"
            value={newProjectName}
            placeholder="New project name"
            onChange={(event) => setNewProjectName(event.target.value)}
          />
          <button type="submit" disabled={creatingProject} style={{ marginLeft: 8 }}>
            {creatingProject ? 'Creating...' : 'Create project'}
          </button>
        </form>
      </section>

      {selectedProjectId ? (
        <section style={sectionStyle}>
          <h2>Repositories</h2>
          {repositoriesError ? (
            <p role="alert" style={errorStyle}>
              {repositoriesError}
            </p>
          ) : null}
          {repositories.length === 0 ? <p>No repositories registered yet.</p> : null}
          {repositories.length > 0 ? (
            <table style={{ borderCollapse: 'collapse', width: '100%' }}>
              <thead>
                <tr style={{ textAlign: 'left' }}>
                  <th style={{ padding: 4 }}>Name</th>
                  <th style={{ padding: 4 }}>Local path</th>
                  <th style={{ padding: 4 }}>Last scanned</th>
                  <th style={{ padding: 4 }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {repositories.map((repository) => {
                  const selected = repository.id === selectedRepositoryId;
                  return (
                    <tr
                      key={repository.id}
                      style={{ background: selected ? '#e8f0fe' : 'transparent' }}
                    >
                      <td style={{ padding: 4 }}>
                        <button
                          type="button"
                          onClick={() => setSelectedRepositoryId(repository.id)}
                          style={{
                            cursor: 'pointer',
                            border: 'none',
                            background: 'none',
                            padding: 0,
                            fontWeight: selected ? 600 : 400,
                            textDecoration: 'underline',
                            color: '#0b57d0',
                          }}
                        >
                          {repository.name}
                        </button>
                      </td>
                      <td style={{ padding: 4 }}>{repository.local_path}</td>
                      <td style={{ padding: 4 }}>{repository.last_scanned_at ?? 'never'}</td>
                      <td style={{ padding: 4 }}>
                        <button
                          type="button"
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
          ) : null}
          <form onSubmit={handleRegisterRepository} style={{ marginTop: 8 }}>
            <input
              type="text"
              value={newRepoName}
              placeholder="Repository name"
              onChange={(event) => setNewRepoName(event.target.value)}
            />
            <input
              type="text"
              value={newRepoPath}
              placeholder="Local path"
              onChange={(event) => setNewRepoPath(event.target.value)}
              style={{ marginLeft: 8 }}
            />
            <button type="submit" disabled={registeringRepo} style={{ marginLeft: 8 }}>
              {registeringRepo ? 'Registering...' : 'Register repository'}
            </button>
          </form>
        </section>
      ) : null}

      {selectedRepositoryId ? (
        <section style={sectionStyle}>
          <h2>Scan Summary</h2>
          {dnaError ? (
            <p role="alert" style={errorStyle}>
              {dnaError}
            </p>
          ) : null}
          {dnaLoading ? <p>Loading scan summary...</p> : null}
          {!dnaLoading && !dnaError && dna === null ? <p>No scan recorded yet.</p> : null}
          {dna ? (
            <div>
              <p>
                <strong>Primary languages:</strong>{' '}
                {primaryLanguages.length > 0 ? primaryLanguages.join(', ') : 'none'}
              </p>
              <p>
                <strong>Package managers:</strong>{' '}
                {dna.package_managers.length > 0 ? dna.package_managers.join(', ') : 'none'}
              </p>
              <ul>
                <li>Has Docker: {summary?.has_docker ? 'yes' : 'no'}</li>
                <li>Has CI: {summary?.has_ci ? 'yes' : 'no'}</li>
                <li>Has tests: {summary?.has_tests ? 'yes' : 'no'}</li>
                <li>Has env example: {summary?.has_env_example ? 'yes' : 'no'}</li>
              </ul>
              <p>
                <strong>Risk flags:</strong>
              </p>
              {dna.risk_flags.length > 0 ? (
                <ul>
                  {dna.risk_flags.map((flag, index) => (
                    <li key={index}>{flag}</li>
                  ))}
                </ul>
              ) : (
                <p>No risk flags.</p>
              )}
              <p>
                <strong>Confidence:</strong> {dna.confidence}
              </p>
            </div>
          ) : null}
        </section>
      ) : null}

      {selectedRepositoryId ? (
        <section style={sectionStyle}>
          <h2>Architecture</h2>
          {architectureError ? (
            <p role="alert" style={errorStyle}>
              {architectureError}
            </p>
          ) : null}
          {architecture ? (
            <div>
              <p>
                Nodes: {architecture.nodes.length} · Edges: {architecture.edges.length}
              </p>
              <ul>
                {architecture.nodes.map((node) => (
                  <li key={node.id}>
                    {node.label} ({node.type}) — confidence {node.confidence}
                  </li>
                ))}
              </ul>
            </div>
          ) : !architectureError ? (
            <p>Loading architecture...</p>
          ) : null}
        </section>
      ) : null}

      {selectedProjectId ? (
        <section style={sectionStyle}>
          <h2>Decisions &amp; Research</h2>
          {artifactsError ? (
            <p role="alert" style={errorStyle}>
              {artifactsError}
            </p>
          ) : null}

          <h3 style={{ marginBottom: 4 }}>Decision Loop</h3>
          {councilError ? (
            <p role="alert" style={errorStyle}>
              {councilError}
            </p>
          ) : null}
          <form onSubmit={handleEnqueueCouncilReview}>
            <input
              type="text"
              value={councilQuestion}
              placeholder="Council question"
              onChange={(event) => setCouncilQuestion(event.target.value)}
            />
            <button type="submit" disabled={councilBusy} style={{ marginLeft: 8 }}>
              {councilBusy ? 'Enqueuing...' : 'Enqueue council review'}
            </button>
            <button
              type="button"
              onClick={() => void handleRefreshLoop()}
              style={{ marginLeft: 8 }}
            >
              Refresh reviews
            </button>
          </form>

          <h4 style={{ marginBottom: 4 }}>Council Reviews</h4>
          {councilReviews.length === 0 ? (
            <p>
              No council reviews yet. Enqueue one — the worker produces it asynchronously, then
              click Refresh reviews.
            </p>
          ) : (
            <ul>
              {councilReviews.map((review) => {
                const drafting = loopBusyKey === `draft:${review.id}`;
                return (
                  <li key={review.id} style={{ marginBottom: 4 }}>
                    {review.verdict} — confidence {review.confidence}
                    {review.question ? ` · ${review.question}` : ''}
                    <button
                      type="button"
                      disabled={drafting}
                      onClick={() => void handleDraftDecision(review.id)}
                      style={{ marginLeft: 8 }}
                    >
                      {drafting ? 'Drafting...' : 'Draft decision'}
                    </button>
                  </li>
                );
              })}
            </ul>
          )}

          <h3 style={{ marginBottom: 4 }}>Decisions</h3>
          {decisions.length === 0 ? (
            <p>No decisions yet.</p>
          ) : (
            <ul>
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
                  <li key={decision.id} style={{ marginBottom: 8 }}>
                    <DecisionStatusBadge status={decision.status} />
                    <span>
                      {decision.title} — confidence {decision.confidence} · {linkedResearch} linked
                      research
                    </span>
                    {decision.approved_by ? (
                      <span style={{ color: '#166534' }}> · approved by {decision.approved_by}</span>
                    ) : null}
                    {governed ? (
                      <div style={{ marginTop: 4 }}>
                        {decision.status === 'needs_evidence' ? (
                          <p style={{ margin: '0 0 4px', color: '#777' }}>
                            Drafted from an abstained review — gather evidence and re-draft before
                            approval.
                          </p>
                        ) : null}
                        <input
                          type="text"
                          value={approverInputs[decision.id] ?? ''}
                          placeholder="Approver name"
                          onChange={(event) =>
                            setApproverInputs((prev) => ({
                              ...prev,
                              [decision.id]: event.target.value,
                            }))
                          }
                        />
                        <button
                          type="button"
                          disabled={approveBusy}
                          onClick={() => void handleApproveDecision(decision.id)}
                          style={{ marginLeft: 8 }}
                        >
                          {approveBusy ? 'Approving...' : 'Approve'}
                        </button>
                        <button
                          type="button"
                          disabled={rejectBusy}
                          onClick={() => void handleRejectDecision(decision.id)}
                          style={{ marginLeft: 8 }}
                        >
                          {rejectBusy ? 'Rejecting...' : 'Reject'}
                        </button>
                      </div>
                    ) : null}
                    {decision.status === 'approved' ? (
                      <div style={{ marginTop: 4 }}>
                        <button
                          type="button"
                          disabled={adrBusy}
                          onClick={() => void handleExportAdr(decision.id)}
                        >
                          {adrBusy ? 'Exporting...' : 'Export ADR'}
                        </button>
                      </div>
                    ) : null}
                    {adrResult ? (
                      <p style={{ margin: '4px 0 0', color: '#166534' }}>{adrResult}</p>
                    ) : null}
                    {inlineError ? (
                      <p role="alert" style={{ ...errorStyle, margin: '4px 0 0' }}>
                        {inlineError}
                      </p>
                    ) : null}
                  </li>
                );
              })}
            </ul>
          )}

          <h3 style={{ marginBottom: 4 }}>Research Notes</h3>
          {researchNotes.length === 0 ? (
            <p>No research notes yet.</p>
          ) : (
            <ul>
              {researchNotes.map((note) => (
                <li key={note.id}>
                  {note.title} — {note.freshness ?? 'unset'}
                </li>
              ))}
            </ul>
          )}

          <h3 style={{ marginBottom: 4 }}>Recommendations</h3>
          {recommendations.length === 0 ? (
            <p>No recommendations yet.</p>
          ) : (
            <ul>
              {recommendations.map((recommendation) => (
                <li key={recommendation.id}>
                  {recommendation.title} — {recommendation.evidence.length} evidence items
                </li>
              ))}
            </ul>
          )}

          <form onSubmit={handleCreateResearchNote} style={{ marginTop: 8 }}>
            <input
              type="text"
              value={newNoteTitle}
              placeholder="Research note title"
              onChange={(event) => setNewNoteTitle(event.target.value)}
            />
            <input
              type="text"
              value={newNoteSummary}
              placeholder="Summary"
              onChange={(event) => setNewNoteSummary(event.target.value)}
              style={{ marginLeft: 8 }}
            />
            <button type="submit" disabled={creatingNote} style={{ marginLeft: 8 }}>
              {creatingNote ? 'Adding...' : 'Add research note'}
            </button>
          </form>

          <form onSubmit={handleCreateDecision} style={{ marginTop: 8 }}>
            <input
              type="text"
              value={newDecisionTitle}
              placeholder="Decision title"
              onChange={(event) => setNewDecisionTitle(event.target.value)}
            />
            <input
              type="text"
              value={newDecisionText}
              placeholder="Decision text"
              onChange={(event) => setNewDecisionText(event.target.value)}
              style={{ marginLeft: 8 }}
            />
            <select
              value={newDecisionNoteId}
              onChange={(event) => setNewDecisionNoteId(event.target.value)}
              style={{ marginLeft: 8 }}
            >
              <option value="">No linked research</option>
              {researchNotes.map((note) => (
                <option key={note.id} value={note.id}>
                  {note.title}
                </option>
              ))}
            </select>
            <button type="submit" disabled={creatingDecision} style={{ marginLeft: 8 }}>
              {creatingDecision ? 'Adding...' : 'Add decision'}
            </button>
          </form>
        </section>
      ) : null}

      {selectedProjectId ? (
        <section style={sectionStyle}>
          <h2>Nightly Digest</h2>
          {digestsError ? (
            <p role="alert" style={errorStyle}>
              {digestsError}
            </p>
          ) : null}
          <button type="button" disabled={runningDigest} onClick={() => void handleRunDigest()}>
            {runningDigest ? 'Running...' : 'Run digest'}
          </button>
          {digests.length === 0 ? (
            <p>No digests yet.</p>
          ) : (
            <ul>
              {digests.map((digest, index) => (
                <li key={digest.id}>
                  {new Date(digest.digest_date).toLocaleDateString()} — {digest.summary ?? 'no summary'}
                  {index === 0 && digest.recommendations.length > 0 ? (
                    <ul>
                      {digest.recommendations.map((recommendation, recIndex) => (
                        <li key={recIndex}>
                          {recommendation.title ?? 'Untitled'} — {recommendation.reason ?? ''}
                        </li>
                      ))}
                    </ul>
                  ) : null}
                </li>
              ))}
            </ul>
          )}
        </section>
      ) : null}

      {selectedProjectId ? (
        <section style={sectionStyle}>
          <h2>Scheduling &amp; Jobs</h2>
          {schedulingError ? (
            <p role="alert" style={errorStyle}>
              {schedulingError}
            </p>
          ) : null}

          <h3 style={{ marginBottom: 4 }}>Schedules</h3>
          {schedules.length === 0 ? (
            <p>No schedules yet.</p>
          ) : (
            <ul>
              {schedules.map((schedule) => (
                <li key={schedule.id} style={{ marginBottom: 4 }}>
                  {schedule.name} — {schedule.job_type} — every {schedule.interval_seconds}s —{' '}
                  {schedule.enabled ? 'enabled' : 'disabled'} — next{' '}
                  {new Date(schedule.next_run_at).toLocaleString()}
                  <button
                    type="button"
                    disabled={schedulingBusy}
                    onClick={() => void handleToggleSchedule(schedule)}
                    style={{ marginLeft: 8 }}
                  >
                    {schedule.enabled ? 'Disable' : 'Enable'}
                  </button>
                  <button
                    type="button"
                    disabled={schedulingBusy}
                    onClick={() => void handleRunSchedule(schedule.id)}
                    style={{ marginLeft: 8 }}
                  >
                    Run now
                  </button>
                  <button
                    type="button"
                    disabled={schedulingBusy}
                    onClick={() => void handleDeleteSchedule(schedule.id)}
                    style={{ marginLeft: 8 }}
                  >
                    Delete
                  </button>
                </li>
              ))}
            </ul>
          )}

          <form onSubmit={handleCreateSchedule} style={{ marginTop: 8 }}>
            <input
              type="text"
              value={newScheduleName}
              placeholder="Schedule name"
              onChange={(event) => setNewScheduleName(event.target.value)}
            />
            <select
              value={newScheduleJobType}
              onChange={(event) => setNewScheduleJobType(event.target.value)}
              style={{ marginLeft: 8 }}
            >
              <option value="repository_scan">repository_scan</option>
              <option value="project_digest">project_digest</option>
            </select>
            <input
              type="number"
              value={newScheduleInterval}
              placeholder="Interval seconds"
              onChange={(event) => setNewScheduleInterval(event.target.value)}
              style={{ marginLeft: 8, width: 140 }}
            />
            <button type="submit" disabled={creatingSchedule} style={{ marginLeft: 8 }}>
              {creatingSchedule ? 'Creating...' : 'Create schedule'}
            </button>
          </form>

          <h3 style={{ marginTop: 12, marginBottom: 4 }}>Enqueue now</h3>
          <div>
            <button
              type="button"
              disabled={schedulingBusy}
              onClick={() => void handleEnqueueDigest()}
            >
              Enqueue digest job
            </button>
            <select
              value={scanJobRepoId}
              onChange={(event) => setScanJobRepoId(event.target.value)}
              style={{ marginLeft: 8 }}
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
              disabled={schedulingBusy || !scanJobRepoId}
              onClick={() => void handleEnqueueScan()}
              style={{ marginLeft: 8 }}
            >
              Enqueue scan job
            </button>
          </div>

          <h3 style={{ marginTop: 12, marginBottom: 4 }}>Job history</h3>
          <button
            type="button"
            disabled={schedulingBusy}
            onClick={() => selectedProjectId && void loadJobs(selectedProjectId)}
          >
            Refresh jobs
          </button>
          {jobs.length === 0 ? (
            <p>No jobs yet.</p>
          ) : (
            <ul>
              {jobs.map((job) => (
                <li key={job.id}>
                  {job.job_type} — {job.status} — {new Date(job.queued_at).toLocaleString()} —
                  attempts {job.attempts}
                </li>
              ))}
            </ul>
          )}
        </section>
      ) : null}

      <section style={sectionStyle}>
        <h2>v0.1 Placeholders</h2>
        <ul>
          <li>Voice inbox text capture</li>
        </ul>
      </section>
    </main>
  );
}

createRoot(document.getElementById('root')!).render(<App />);
