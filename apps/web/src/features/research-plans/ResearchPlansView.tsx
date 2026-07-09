import { useCallback, useEffect, useState } from 'react';
import {
  createResearchPlan,
  decideSource,
  fetchResearchPlans,
  fetchResearchRuns,
  runResearchPlan,
  type ResearchPlan,
  type ResearchRun,
} from '../../api';
import { errorMessage } from '../../shell/errorMessage';
import { useProjectContext } from '../../shell/ProjectContext';
import { SelectProjectNotice } from '../../shell/SelectProjectNotice';

// AOS-RESEARCH-003 (UI) — the Research Plans surface. Create a multi-phase plan
// from a question, run it, and inspect the run: the phases it went through, the
// sources it accepted/rejected (with reasons + operator override), the conflicts
// it kept visible, the findings that cite sources, and the open questions it
// spun off as follow-up plans. Data comes from the AOS-RESEARCH-003 endpoints.
export function ResearchPlansView() {
  const { selectedProjectId } = useProjectContext();

  const [plans, setPlans] = useState<ResearchPlan[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [question, setQuestion] = useState('');
  const [creating, setCreating] = useState(false);

  const [selectedPlanId, setSelectedPlanId] = useState<string | null>(null);
  const [runs, setRuns] = useState<ResearchRun[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [running, setRunning] = useState(false);

  const loadPlans = useCallback(async (projectId: string) => {
    setError(null);
    try {
      setPlans(await fetchResearchPlans(projectId));
    } catch (err) {
      setPlans([]);
      setError(errorMessage(err));
    }
  }, []);

  const loadRuns = useCallback(async (planId: string) => {
    try {
      setRuns(await fetchResearchRuns(planId));
    } catch (err) {
      setRuns([]);
      setError(errorMessage(err));
    }
  }, []);

  useEffect(() => {
    if (selectedProjectId) {
      void loadPlans(selectedProjectId);
    } else {
      setPlans([]);
    }
    setSelectedPlanId(null);
    setRuns([]);
    setSelectedRunId(null);
  }, [selectedProjectId, loadPlans]);

  useEffect(() => {
    if (selectedPlanId) {
      void loadRuns(selectedPlanId);
    } else {
      setRuns([]);
    }
    setSelectedRunId(null);
  }, [selectedPlanId, loadRuns]);

  const handleCreate = useCallback(
    async (event: React.FormEvent) => {
      event.preventDefault();
      if (!selectedProjectId) {
        return;
      }
      const q = question.trim();
      if (!q) {
        return;
      }
      setCreating(true);
      setError(null);
      try {
        const plan = await createResearchPlan(selectedProjectId, q);
        setQuestion('');
        await loadPlans(selectedProjectId);
        setSelectedPlanId(plan.id);
      } catch (err) {
        setError(errorMessage(err));
      } finally {
        setCreating(false);
      }
    },
    [selectedProjectId, question, loadPlans],
  );

  const handleRun = useCallback(
    async (planId: string) => {
      setRunning(true);
      setError(null);
      try {
        await runResearchPlan(planId);
        // The worker produces the run asynchronously; refetch until it appears
        // (in e2e the mocked endpoint returns it immediately).
        await loadRuns(planId);
      } catch (err) {
        setError(errorMessage(err));
      } finally {
        setRunning(false);
      }
    },
    [loadRuns],
  );

  const handleDecision = useCallback(
    async (runId: string, sourceRef: string, accepted: boolean) => {
      const reason = accepted ? 'operator accepted' : 'operator rejected';
      setError(null);
      try {
        const updated = await decideSource(runId, sourceRef, accepted, reason);
        setRuns((prev) => prev.map((run) => (run.id === updated.id ? updated : run)));
      } catch (err) {
        setError(errorMessage(err));
      }
    },
    [],
  );

  if (!selectedProjectId) {
    return <SelectProjectNotice />;
  }

  const selectedPlan = plans.find((plan) => plan.id === selectedPlanId) ?? null;
  const selectedRun = runs.find((run) => run.id === selectedRunId) ?? null;

  return (
    <div className="aos-view" data-testid="research-plans-view">
      <div className="aos-view-head">
        <span className="aos-eyebrow">Evidence &amp; knowledge</span>
        <h2>Research Plans</h2>
      </div>

      {error ? <p role="alert" className="aos-error">{error}</p> : null}

      <div className="aos-hud glass aos-card">
        <span className="aos-eyebrow">New plan</span>
        <form onSubmit={handleCreate} className="aos-form-row">
          <input
            className="aos-input"
            type="text"
            value={question}
            placeholder="Research question"
            data-testid="research-plan-question"
            onChange={(event) => setQuestion(event.target.value)}
            style={{ width: 'auto', flex: '1 1 260px' }}
          />
          <button type="submit" className="aos-btn aos-btn-sm" disabled={creating} data-testid="research-plan-create">
            {creating ? 'Planning...' : 'Create plan'}
          </button>
        </form>

        <h3>Plans</h3>
        {plans.length === 0 ? (
          <p className="aos-muted" style={{ margin: 0 }}>No research plans yet.</p>
        ) : (
          <ul className="aos-rows">
            {plans.map((plan) => (
              <li key={plan.id} data-testid="research-plan-row">
                <button
                  type="button"
                  className={`aos-linkbtn${plan.id === selectedPlanId ? ' sel' : ''}`}
                  onClick={() => setSelectedPlanId(plan.id)}
                >
                  {plan.question}
                </button>{' '}
                <span className="aos-rowmeta">{plan.plan_status}</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      {selectedPlan ? (
        <div className="aos-hud glass aos-card">
          <span className="aos-eyebrow">Plan</span>
          <h3 style={{ marginTop: 0 }} data-testid="research-plan-detail-question">{selectedPlan.question}</h3>
          <dl className="aos-kv">
            <dt>Search queries</dt>
            <dd data-testid="research-plan-queries">{selectedPlan.search_queries.join(' · ')}</dd>
            <dt>Verification</dt>
            <dd>{selectedPlan.verification_steps.join('; ')}</dd>
          </dl>
          <button
            type="button"
            className="aos-btn aos-btn-sm"
            disabled={running}
            data-testid="research-plan-run"
            onClick={() => void handleRun(selectedPlan.id)}
          >
            {running ? 'Running...' : 'Run plan'}
          </button>

          <h3>Runs</h3>
          {runs.length === 0 ? (
            <p className="aos-muted" style={{ margin: 0 }}>No runs yet — run the plan.</p>
          ) : (
            <ul className="aos-rows">
              {runs.map((run) => (
                <li key={run.id} data-testid="research-run-row">
                  <button
                    type="button"
                    className={`aos-linkbtn${run.id === selectedRunId ? ' sel' : ''}`}
                    onClick={() => setSelectedRunId(run.id)}
                  >
                    {run.run_status} — confidence {run.confidence}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : null}

      {selectedRun ? (
        <div className="aos-hud glass aos-card" data-testid="research-run-detail">
          <span className="aos-eyebrow">Run</span>

          <h3>Phases</h3>
          <ol className="aos-rows" data-testid="research-run-phases">
            {selectedRun.phases.map((phase) => (
              <li key={phase.phase}>
                <span className="aos-strong">{phase.phase}</span> — {phase.detail}
              </li>
            ))}
          </ol>

          <h3>Sources</h3>
          {selectedRun.sources.length === 0 ? (
            <p className="aos-muted" style={{ margin: 0 }}>No sources considered.</p>
          ) : (
            <ul className="aos-rows">
              {selectedRun.sources.map((source) => (
                <li key={source.ref} data-testid="research-run-source">
                  <span className={`aos-pill ${source.accepted ? 'good' : 'risk'}`}>
                    {source.accepted ? 'accepted' : 'rejected'}
                  </span>{' '}
                  <span>{source.title}</span>
                  {source.reason ? <span className="aos-rowmeta"> · {source.reason}</span> : null}
                  <button
                    type="button"
                    className="aos-btn-ghost aos-btn-sm"
                    data-testid="research-source-accept"
                    onClick={() => void handleDecision(selectedRun.id, source.ref, true)}
                  >
                    Accept
                  </button>
                  <button
                    type="button"
                    className="aos-btn-ghost aos-btn-sm"
                    data-testid="research-source-reject"
                    onClick={() => void handleDecision(selectedRun.id, source.ref, false)}
                  >
                    Reject
                  </button>
                </li>
              ))}
            </ul>
          )}

          <h3>Conflicts</h3>
          {selectedRun.conflicts.length === 0 ? (
            <p className="aos-muted" style={{ margin: 0 }}>No conflicting evidence detected.</p>
          ) : (
            <ul className="aos-rows" data-testid="research-run-conflicts">
              {selectedRun.conflicts.map((conflict, index) => (
                <li key={index}>{typeof conflict === 'string' ? conflict : JSON.stringify(conflict)}</li>
              ))}
            </ul>
          )}

          <h3>Findings</h3>
          {selectedRun.findings.length === 0 ? (
            <p className="aos-muted" style={{ margin: 0 }}>No findings.</p>
          ) : (
            <ul className="aos-rows">
              {selectedRun.findings.map((finding, index) => (
                <li key={index} data-testid="research-run-finding">
                  {finding.claim} <span className="aos-rowmeta">[{finding.source_ref}]</span>
                </li>
              ))}
            </ul>
          )}

          <h3>Open questions</h3>
          {selectedRun.open_questions.length === 0 ? (
            <p className="aos-muted" style={{ margin: 0 }}>None — coverage was sufficient.</p>
          ) : (
            <ul className="aos-rows" data-testid="research-run-open-questions">
              {selectedRun.open_questions.map((oq, index) => (
                <li key={index}>{oq}</li>
              ))}
            </ul>
          )}
        </div>
      ) : null}
    </div>
  );
}
