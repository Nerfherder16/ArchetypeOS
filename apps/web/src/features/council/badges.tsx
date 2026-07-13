// AOS-WEB-SPINE-001 (slice 3f) — badge + list helpers for the Governance
// (Council) cluster, moved verbatim from main.tsx. Used only by the council
// sections.

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

export function VerdictBadge({ verdict }: { verdict: string }) {
  const isAbstention = verdict === 'Insufficient evidence';
  const tier = VERDICT_PILL_TIER[verdict] ?? 'neutral';
  return <span className={`aos-pill ${tier}${isAbstention ? ' abstain' : ''}`}>{verdict}</span>;
}

// Defensive renderer for list items whose shape may be a plain string or a
// small object (e.g. { text: '...' } or { summary: '...' }).  Never crashes.
export function renderListItem(item: unknown): string {
  if (typeof item === 'string') {
    return item;
  }
  if (item !== null && typeof item === 'object') {
    const obj = item as Record<string, unknown>;
    const field = obj.detail ?? obj.text ?? obj.summary ?? obj.description ?? obj.message ?? obj.content;
    if (typeof field === 'string') {
      return field;
    }
    return JSON.stringify(item);
  }
  return String(item ?? '');
}

export function DecisionStatusBadge({ status }: { status: string }) {
  const tier = DECISION_STATUS_PILL_TIER[status] ?? 'neutral';
  return <span className={`aos-pill ${tier}`}>{status}</span>;
}
