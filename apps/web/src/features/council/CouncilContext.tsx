import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type Dispatch,
  type ReactNode,
  type SetStateAction,
} from 'react';
import {
  approveDecision,
  createDecision,
  createResearchNote,
  draftDecisionFromReview,
  enqueueCouncilReview,
  exportDecisionAdr,
  fetchCouncilReview,
  fetchCouncilReviews,
  fetchDecisions,
  fetchRecommendations,
  fetchResearchNotes,
  rejectDecision,
  type CouncilReview,
  type Decision,
  type Recommendation,
  type ResearchNote,
} from '../../api';
import { errorMessage } from '../../shell/errorMessage';
import { useProjectContext } from '../../shell/ProjectContext';

// AOS-WEB-SPINE-001 (slice 3f) — Council/Governance state provider.
//
// The Decision Loop, Research, and Agent Council sections share one cluster of
// artifacts (decisions/notes/recommendations), council reviews, and the loaders
// + handlers that mutate them. This provider owns all of it (moved verbatim from
// App), loads on selected-project change, and exposes it via useCouncil() so the
// three section components stay presentational. Mounted inside CouncilView, which
// only renders when a project is selected.
export type CouncilContextValue = {
  // artifacts
  decisions: Decision[];
  researchNotes: ResearchNote[];
  recommendations: Recommendation[];
  artifactsError: string | null;
  newNoteTitle: string;
  setNewNoteTitle: Dispatch<SetStateAction<string>>;
  newNoteSummary: string;
  setNewNoteSummary: Dispatch<SetStateAction<string>>;
  creatingNote: boolean;
  newDecisionTitle: string;
  setNewDecisionTitle: Dispatch<SetStateAction<string>>;
  newDecisionText: string;
  setNewDecisionText: Dispatch<SetStateAction<string>>;
  newDecisionNoteId: string;
  setNewDecisionNoteId: Dispatch<SetStateAction<string>>;
  creatingDecision: boolean;
  handleCreateResearchNote: (event: React.FormEvent) => Promise<void>;
  handleCreateDecision: (event: React.FormEvent) => Promise<void>;
  // decision loop
  councilReviews: CouncilReview[];
  councilError: string | null;
  councilQuestion: string;
  setCouncilQuestion: Dispatch<SetStateAction<string>>;
  councilBusy: boolean;
  loopBusyKey: string | null;
  approverInputs: Record<string, string>;
  setApproverInputs: Dispatch<SetStateAction<Record<string, string>>>;
  decisionErrors: Record<string, string>;
  adrResults: Record<string, string>;
  handleEnqueueCouncilReview: (event: React.FormEvent) => Promise<void>;
  handleRefreshLoop: () => Promise<void>;
  handleDraftDecision: (reviewId: string) => Promise<void>;
  handleApproveDecision: (decisionId: string) => Promise<void>;
  handleRejectDecision: (decisionId: string) => Promise<void>;
  handleExportAdr: (decisionId: string) => Promise<void>;
  // agent council section
  councilSectionLoading: boolean;
  councilSectionError: string | null;
  councilExpandedId: string | null;
  councilDetailMap: Record<string, CouncilReview>;
  councilDetailLoading: string | null;
  councilDetailError: Record<string, string>;
  handleRefreshCouncilSection: () => Promise<void>;
  handleExpandReview: (reviewId: string) => Promise<void>;
};

const CouncilContext = createContext<CouncilContextValue | null>(null);

export function CouncilProvider({ children }: { children: ReactNode }) {
  const { selectedProjectId } = useProjectContext();

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

  // Agent Council section state (separate from Decision Loop).
  const [councilSectionLoading, setCouncilSectionLoading] = useState(false);
  const [councilSectionError, setCouncilSectionError] = useState<string | null>(null);
  const [councilExpandedId, setCouncilExpandedId] = useState<string | null>(null);
  const [councilDetailMap, setCouncilDetailMap] = useState<Record<string, CouncilReview>>({});
  const [councilDetailLoading, setCouncilDetailLoading] = useState<string | null>(null);
  const [councilDetailError, setCouncilDetailError] = useState<Record<string, string>>({});

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

  // Load the cluster on selected-project change; clear all transient sub-state
  // (mirrors the reset App previously performed in its project-change effect).
  useEffect(() => {
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
    setCouncilSectionLoading(false);
    setCouncilSectionError(null);
    setCouncilExpandedId(null);
    setCouncilDetailMap({});
    setCouncilDetailLoading(null);
    setCouncilDetailError({});
    if (selectedProjectId) {
      void loadArtifacts(selectedProjectId);
      void loadCouncilReviews(selectedProjectId);
    }
  }, [selectedProjectId, loadArtifacts, loadCouncilReviews]);

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

  const value = useMemo<CouncilContextValue>(
    () => ({
      decisions,
      researchNotes,
      recommendations,
      artifactsError,
      newNoteTitle,
      setNewNoteTitle,
      newNoteSummary,
      setNewNoteSummary,
      creatingNote,
      newDecisionTitle,
      setNewDecisionTitle,
      newDecisionText,
      setNewDecisionText,
      newDecisionNoteId,
      setNewDecisionNoteId,
      creatingDecision,
      handleCreateResearchNote,
      handleCreateDecision,
      councilReviews,
      councilError,
      councilQuestion,
      setCouncilQuestion,
      councilBusy,
      loopBusyKey,
      approverInputs,
      setApproverInputs,
      decisionErrors,
      adrResults,
      handleEnqueueCouncilReview,
      handleRefreshLoop,
      handleDraftDecision,
      handleApproveDecision,
      handleRejectDecision,
      handleExportAdr,
      councilSectionLoading,
      councilSectionError,
      councilExpandedId,
      councilDetailMap,
      councilDetailLoading,
      councilDetailError,
      handleRefreshCouncilSection,
      handleExpandReview,
    }),
    [
      decisions,
      researchNotes,
      recommendations,
      artifactsError,
      newNoteTitle,
      newNoteSummary,
      creatingNote,
      newDecisionTitle,
      newDecisionText,
      newDecisionNoteId,
      creatingDecision,
      handleCreateResearchNote,
      handleCreateDecision,
      councilReviews,
      councilError,
      councilQuestion,
      councilBusy,
      loopBusyKey,
      approverInputs,
      decisionErrors,
      adrResults,
      handleEnqueueCouncilReview,
      handleRefreshLoop,
      handleDraftDecision,
      handleApproveDecision,
      handleRejectDecision,
      handleExportAdr,
      councilSectionLoading,
      councilSectionError,
      councilExpandedId,
      councilDetailMap,
      councilDetailLoading,
      councilDetailError,
      handleRefreshCouncilSection,
      handleExpandReview,
    ],
  );

  return <CouncilContext.Provider value={value}>{children}</CouncilContext.Provider>;
}

export function useCouncil(): CouncilContextValue {
  const ctx = useContext(CouncilContext);
  if (ctx === null) {
    throw new Error('useCouncil must be used within a CouncilProvider');
  }
  return ctx;
}
