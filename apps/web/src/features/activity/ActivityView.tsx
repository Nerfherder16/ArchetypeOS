import React, { useCallback, useEffect, useState } from 'react';
import { fetchJobs, fetchProjects, type Job } from '../../api';

const errorMessage = (err: unknown): string =>
  err instanceof Error ? err.message : 'Request failed';

// Cap the rendered feed so a busy portfolio never floods the DOM. When the
// merged stream exceeds this, we render the newest MAX_ROWS and state the cap in
// the UI (no silent truncation — AOS-OPS-002).
const MAX_ROWS = 50;

// A job tagged with the human-readable name of the project it belongs to, so the
// aggregated feed can show provenance (which project each event came from).
type ActivityItem = Job & { projectName: string };

// Defensive status → `.aos-pill` tier map. Job status strings are not a closed
// enum on the frontend, so we normalise (lowercase) and match known families;
// anything unrecognised falls back to `neutral` rather than crashing or blanking.
//   done/complete/succeeded → good  (cyan `--signal`)
//   running/started         → info
//   queued/pending          → neutral
//   failed/error            → risk  (red `--red`)
const STATUS_PILL_TIER: Record<string, string> = {
  done: 'good',
  complete: 'good',
  completed: 'good',
  succeeded: 'good',
  success: 'good',
  running: 'info',
  started: 'info',
  in_progress: 'info',
  queued: 'neutral',
  pending: 'neutral',
  failed: 'risk',
  error: 'risk',
};

function pillTier(status: string): string {
  return STATUS_PILL_TIER[status.trim().toLowerCase()] ?? 'neutral';
}

const FAILED_STATUSES = new Set(['failed', 'error']);

function isFailed(status: string): boolean {
  return FAILED_STATUSES.has(status.trim().toLowerCase());
}

// Human-readable job_type label: `council_review` → "Council review",
// `repository_scan` → "Repository scan". Falls back to a title-cased,
// underscore-split form for any job_type we do not name explicitly.
const JOB_TYPE_LABELS: Record<string, string> = {
  scan: 'Scan',
  repository_scan: 'Repository scan',
  council_review: 'Council review',
  digest: 'Digest',
  project_digest: 'Project digest',
  nightly_digest: 'Nightly digest',
};

function jobTypeLabel(jobType: string): string {
  const known = JOB_TYPE_LABELS[jobType.trim().toLowerCase()];
  if (known) {
    return known;
  }
  const words = jobType.replace(/[_-]+/g, ' ').trim();
  if (!words) {
    return jobType;
  }
  return words.charAt(0).toUpperCase() + words.slice(1);
}

// The timestamp that orders the feed: the most-recent lifecycle event for a job.
// A finished job sorts by when it finished; a running one by when it started; a
// still-queued one by when it was queued. Newest first.
function activityTime(job: Job): string {
  return job.finished_at ?? job.started_at ?? job.queued_at;
}

// HH:MM:SS render of the ordering timestamp. Defensive: an unparseable value
// falls back to the raw string rather than "Invalid Date".
function formatTime(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return iso;
  }
  return date.toLocaleTimeString([], { hour12: false });
}

type LoadResult = {
  items: ActivityItem[];
  projectCount: number;
};

// Aggregate every job across the operator's projects into one time-ordered feed.
// N+1 by design (small portfolio; a `GET /activity` endpoint is the noted future
// optimization). A per-project jobs fetch that fails is SKIPPED via
// Promise.allSettled — one bad project never fails the whole feed. Throws only
// if the top-level `fetchProjects()` itself fails (surfaced as the error state).
async function loadActivity(): Promise<LoadResult> {
  const projects = await fetchProjects();
  const settled = await Promise.allSettled(projects.map((p) => fetchJobs(p.id)));
  const items: ActivityItem[] = [];
  settled.forEach((result, index) => {
    if (result.status !== 'fulfilled') {
      return; // skip a project whose jobs could not be loaded
    }
    const project = projects[index];
    for (const job of result.value) {
      items.push({ ...job, projectName: project.name });
    }
  });
  // Newest first by the job's most-recent lifecycle timestamp.
  items.sort((a, b) => activityTime(b).localeCompare(activityTime(a)));
  return { items, projectCount: projects.length };
}

function StatusPill({ status }: { status: string }) {
  return <span className={`aos-pill ${pillTier(status)}`}>{status}</span>;
}

function ActivityRow({ item }: { item: ActivityItem }) {
  const failed = isFailed(item.status);
  return (
    <li className="aos-activity-row" data-testid="activity-row" data-status={item.status}>
      <span className="aos-mono aos-rowmeta aos-activity-time">{formatTime(activityTime(item))}</span>
      <StatusPill status={item.status} />
      <span className="aos-strong">{jobTypeLabel(item.job_type)}</span>
      <span className="aos-rowmeta">· {item.projectName}</span>
      {failed && item.error ? (
        <span className="aos-mono aos-activity-error" title={item.error}>
          {item.error}
        </span>
      ) : null}
    </li>
  );
}

export function ActivityView() {
  const [items, setItems] = useState<ActivityItem[] | null>(null);
  const [projectCount, setProjectCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await loadActivity();
      setItems(result.items);
      setProjectCount(result.projectCount);
    } catch (err) {
      // Graceful degradation: a missing/absent API (static preview, backend
      // down) must never throw or blank the screen — surface a readable notice.
      setItems(null);
      setProjectCount(0);
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const total = items?.length ?? 0;
  const isEmpty = items !== null && items.length === 0;
  const capped = total > MAX_ROWS;
  const visible = items ? items.slice(0, MAX_ROWS) : [];

  return (
    <section className="aos-view" data-testid="activity-view">
      <div className="aos-view-head">
        <span className="aos-eyebrow" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ color: 'var(--signal)' }} aria-hidden="true">
            &#9672;
          </span>
          Operations · Live Activity
        </span>
        <h2 style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          System activity feed
          {items !== null && total > 0 ? (
            <span className="aos-pill info" data-testid="activity-count">
              {total} event{total === 1 ? '' : 's'} across {projectCount} project
              {projectCount === 1 ? '' : 's'}
            </span>
          ) : null}
        </h2>
      </div>

      {error ? (
        <div className="aos-hud glass aos-card">
          <span className="aos-eyebrow">Activity stream</span>
          <p role="alert" className="aos-error" data-testid="activity-error" style={{ marginTop: 8 }}>
            Activity unavailable: {error}
          </p>
          <p className="aos-muted" style={{ margin: '8px 0 0', fontSize: 13 }}>
            The feed aggregates <span className="aos-mono">GET /projects</span> and each project&apos;s{' '}
            <span className="aos-mono">/jobs</span>. Once the API is reachable, scans, digests, and
            council runs stream here.
          </p>
        </div>
      ) : loading && items === null ? (
        <div className="aos-hud glass aos-card">
          <p className="aos-muted" data-testid="activity-loading" style={{ margin: 0 }}>
            Loading the activity feed…
          </p>
        </div>
      ) : isEmpty ? (
        <div className="aos-hud glass aos-card">
          <span className="aos-eyebrow">Activity stream</span>
          <p className="aos-muted" data-testid="activity-empty" style={{ margin: '8px 0 0' }}>
            No activity yet — scans, digests, and council runs will stream here.
          </p>
        </div>
      ) : items !== null ? (
        <div className="aos-hud glass aos-card">
          <ul className="aos-rows aos-activity-feed">
            {visible.map((item) => (
              <ActivityRow key={item.id} item={item} />
            ))}
          </ul>
          {capped ? (
            <p className="aos-mono aos-muted" data-testid="activity-truncation" style={{ margin: '10px 0 0', fontSize: 12 }}>
              Showing the {MAX_ROWS} most recent of {total} events.
            </p>
          ) : null}
        </div>
      ) : null}

      {/* Non-goal footnote (AOS-OPS-002): the feed is jobs-based. Council-verdict,
          decision-status, lesson, and scan-detail events need `created_at` on
          their Read schemas (or a dedicated GET /activity endpoint) and are a
          future enrichment. Real-time streaming is likewise deferred. */}
      <p className="aos-mono aos-muted" style={{ margin: '16px 0 0', fontSize: 11.5 }}>
        This feed streams platform <span className="aos-mono">jobs</span> (scans, digests, scheduled
        runs, council reviews). Council-verdict and decision-status events are a future enrichment —
        they need a timestamp on their read schemas or a dedicated activity endpoint.
      </p>
    </section>
  );
}
