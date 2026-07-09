import { renderListItem, VerdictBadge } from './badges';
import { useCouncil } from './CouncilContext';

// AOS-WEB-SPINE-001 (slice 3f) — the Agent Council section (independent refresh
// + expandable per-review Final Judge / agent-outputs detail), moved verbatim
// from App's `case 'council'`. Reads from useCouncil().
export function AgentCouncilSection() {
  const {
    councilSectionError,
    councilSectionLoading,
    handleRefreshCouncilSection,
    councilReviews,
    councilExpandedId,
    councilDetailLoading,
    councilDetailError,
    councilDetailMap,
    handleExpandReview,
  } = useCouncil();

  return (
    <>
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
    </>
  );
}
