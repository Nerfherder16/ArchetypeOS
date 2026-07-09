import { useCallback, useEffect, useState } from 'react';
import { fetchDigests, runDigest, type NightlyDigest } from '../../api';
import { errorMessage } from '../../shell/errorMessage';
import { useProjectContext } from '../../shell/ProjectContext';
import { SelectProjectNotice } from '../../shell/SelectProjectNotice';

// AOS-WEB-SPINE-001 (slice 3d) — the Nightly Digest surface, extracted from
// App's `case 'digest'`. Digest data is used by no other view, so this is a
// fully self-contained module: it owns its own state, its loader, and its
// run handler, and loads on selected-project change via useProjectContext.
// (Previously App eager-loaded digests in its project-change effect; the view
// now loads its own data when mounted for the selected project — same data,
// same result, only the surface owning it changed.)
export function DigestView() {
  const { selectedProjectId } = useProjectContext();

  const [digests, setDigests] = useState<NightlyDigest[]>([]);
  const [digestsError, setDigestsError] = useState<string | null>(null);
  const [runningDigest, setRunningDigest] = useState(false);

  const loadDigests = useCallback(async (projectId: string) => {
    setDigestsError(null);
    try {
      setDigests(await fetchDigests(projectId));
    } catch (err) {
      setDigests([]);
      setDigestsError(errorMessage(err));
    }
  }, []);

  useEffect(() => {
    if (selectedProjectId) {
      void loadDigests(selectedProjectId);
    } else {
      setDigests([]);
    }
  }, [selectedProjectId, loadDigests]);

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
}
