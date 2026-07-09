import { DecisionStatusBadge } from './badges';
import { useCouncil } from './CouncilContext';

// AOS-WEB-SPINE-001 (slice 3f) — the Decision Loop section (council reviews +
// enqueue form) and the Decisions card (approve/reject/export-ADR), moved
// verbatim from App's `case 'council'`. Reads everything from useCouncil().
export function DecisionLoopSection() {
  const {
    councilError,
    councilQuestion,
    setCouncilQuestion,
    councilBusy,
    handleEnqueueCouncilReview,
    handleRefreshLoop,
    councilReviews,
    loopBusyKey,
    handleDraftDecision,
    decisions,
    decisionErrors,
    adrResults,
    approverInputs,
    setApproverInputs,
    handleApproveDecision,
    handleRejectDecision,
    handleExportAdr,
  } = useCouncil();

  return (
    <>
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
    </>
  );
}
