import { useCallback, useEffect, useState } from 'react';
import { fetchAuditHeartbeats, type AuditHeartbeat } from '../../api';
import { errorMessage } from '../../shell/errorMessage';

// AOS-SELFHEAL observability (UI) — the Nightly Audits board. One row per known
// self-learn routine showing its latest heartbeat: clean / findings / failed,
// the day it last reported, a link to any PR it opened, and — the whole point of
// the board — a "missed" flag when a routine has not checked in within a day, so
// a silently-skipped nightly is VISIBLE instead of invisible. Data comes from
// GET /audits/heartbeats (a global surface, not project-scoped).

// The self-learn routines expected to report every night. A routine with no
// fresh heartbeat is surfaced as missed / never-reported rather than simply
// absent from the list.
const KNOWN_ROUTINES: { routine: string; label: string }[] = [
  { routine: 'conflict', label: 'Merge conflict' },
  { routine: 'toil', label: 'Git toil' },
  { routine: 'coherence', label: 'Contract coherence' },
  { routine: 'session-pain', label: 'Session pain' },
];

// A nightly heartbeat older than this is treated as a missed run.
const STALE_MS = 26 * 60 * 60 * 1000;

type RowState = 'clean' | 'findings' | 'failed' | 'missed' | 'never';

// Pill class per resolved row state — clean is healthy, findings is a PR to look
// at, failed/missed demand attention, never means the routine has not run yet.
const PILL: Record<RowState, string> = {
  clean: 'good',
  findings: 'info',
  failed: 'risk',
  missed: 'warn',
  never: 'neutral',
};

const PILL_LABEL: Record<RowState, string> = {
  clean: 'clean',
  findings: 'findings',
  failed: 'failed',
  missed: 'missed',
  never: 'no report',
};

// Resolve a routine's heartbeat (or its absence) into a single row state. A
// heartbeat is "missed" when it exists but is older than a day — the run has not
// checked in on schedule.
function rowState(hb: AuditHeartbeat | undefined, now: number): RowState {
  if (!hb) {
    return 'never';
  }
  const age = now - Date.parse(hb.updated_at);
  if (Number.isFinite(age) && age > STALE_MS) {
    return 'missed';
  }
  if (hb.heartbeat_status === 'clean' || hb.heartbeat_status === 'findings' || hb.heartbeat_status === 'failed') {
    return hb.heartbeat_status;
  }
  return 'never';
}

type Row = {
  routine: string;
  label: string;
  state: RowState;
  heartbeat: AuditHeartbeat | undefined;
};

// Merge the known routines with whatever the API returned: every known routine
// gets a row (so a never-run routine is visible), and any extra routine that has
// reported but is not in the known set is appended so nothing is hidden.
function buildRows(heartbeats: AuditHeartbeat[], now: number): Row[] {
  const byRoutine = new Map(heartbeats.map((hb) => [hb.routine, hb]));
  const rows: Row[] = KNOWN_ROUTINES.map(({ routine, label }) => {
    const heartbeat = byRoutine.get(routine);
    return { routine, label, state: rowState(heartbeat, now), heartbeat };
  });
  const known = new Set(KNOWN_ROUTINES.map((entry) => entry.routine));
  for (const hb of heartbeats) {
    if (!known.has(hb.routine)) {
      rows.push({ routine: hb.routine, label: hb.routine, state: rowState(hb, now), heartbeat: hb });
    }
  }
  return rows;
}

export function AuditsView() {
  const [heartbeats, setHeartbeats] = useState<AuditHeartbeat[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setError(null);
    try {
      setHeartbeats(await fetchAuditHeartbeats());
    } catch (err) {
      setHeartbeats([]);
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const rows = buildRows(heartbeats, Date.now());
  const attention = rows.filter((row) => row.state === 'missed' || row.state === 'failed').length;

  return (
    <section className="aos-view" data-testid="audits-view">
      <div className="aos-view-head">
        <span className="aos-eyebrow">Operations</span>
        <h2>Nightly Audits</h2>
      </div>

      {error ? <p role="alert" className="aos-error">Heartbeats unavailable: {error}</p> : null}

      <div className="aos-hud glass aos-card">
        <div className="aos-form-row" style={{ marginTop: 0, justifyContent: 'space-between' }}>
          <span className="aos-eyebrow">Self-learn routines</span>
          <button type="button" className="aos-btn aos-btn-sm" onClick={() => void load()} data-testid="audits-refresh">
            Refresh
          </button>
        </div>

        <p className="aos-mono aos-muted" style={{ margin: '4px 0 0', fontSize: 12 }} data-testid="audits-summary">
          {attention === 0
            ? 'All routines reporting on schedule.'
            : `${attention} ${attention === 1 ? 'routine needs' : 'routines need'} attention (missed or failed).`}
        </p>

        {loading ? (
          <p className="aos-muted" style={{ margin: '12px 0 0' }}>Loading heartbeats…</p>
        ) : (
          <ul className="aos-rows" style={{ marginTop: 12 }}>
            {rows.map((row) => (
              <li key={row.routine} data-testid="audit-row" data-routine={row.routine} data-state={row.state}>
                <span className={`aos-pill ${PILL[row.state]}`}>{PILL_LABEL[row.state]}</span>{' '}
                <span className="aos-strong">{row.label}</span>
                {row.heartbeat ? (
                  <span className="aos-rowmeta">
                    {' '}· last {row.heartbeat.day}
                    {row.heartbeat.detail ? ` · ${row.heartbeat.detail}` : ''}
                  </span>
                ) : (
                  <span className="aos-rowmeta"> · never reported</span>
                )}
                {row.heartbeat?.pr_url ? (
                  <>
                    {' '}
                    <a
                      className="aos-linkbtn"
                      href={row.heartbeat.pr_url}
                      target="_blank"
                      rel="noreferrer"
                      data-testid="audit-pr-link"
                    >
                      PR
                    </a>
                  </>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
