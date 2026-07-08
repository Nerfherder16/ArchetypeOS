import React, { useCallback, useEffect, useState } from 'react';
import {
  fetchVoiceInbox,
  updateVoiceInboxItem,
  type VoiceInboxItem,
  type VoiceReviewState,
} from '../../api';

// AOS-VOICE-003 — the Voice Inbox review queue. Every CommandDeck turn (typed or
// Sotto-spoken) lands here as a review-first draft; the operator approves or
// dismisses it. Review-first: approving records intent only — promoting a draft
// into its concrete action (research task, decision, guardian review) is a later
// slice (AOS-VOICE-005). Degrades gracefully when the API is unreachable.

const errorMessage = (err: unknown): string =>
  err instanceof Error ? err.message : 'Request failed';

// Pending first, then approved, then dismissed — the queue is actioned top-down.
const STATE_RANK: Record<string, number> = { pending: 0, approved: 1, dismissed: 2 };

function IntentChip({ intent }: { intent: string }) {
  return <span className="aos-pill info">{intent.replace(/_/g, ' ')}</span>;
}

type InboxCardProps = {
  item: VoiceInboxItem;
  onResolved: (id: string, state: VoiceReviewState) => void;
};

function InboxCard({ item, onResolved }: InboxCardProps) {
  const [busy, setBusy] = useState<VoiceReviewState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const pending = item.review_state === 'pending';

  const resolve = useCallback(
    async (state: VoiceReviewState) => {
      setBusy(state);
      setError(null);
      try {
        await updateVoiceInboxItem(item.id, state);
        onResolved(item.id, state);
      } catch (err) {
        setError(errorMessage(err));
        setBusy(null);
      }
    },
    [item.id, onResolved],
  );

  return (
    <li className="aos-hud glass aos-card" data-testid="voice-inbox-card" data-state={item.review_state}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
        <IntentChip intent={item.detected_intent} />
        {item.required_review ? <span className="aos-pill warn">review</span> : null}
        <span className="aos-eyebrow" style={{ letterSpacing: '0.12em' }}>
          {item.source_device}
        </span>
        {!pending ? (
          <span className="aos-pill" data-testid="voice-inbox-state">
            {item.review_state}
          </span>
        ) : null}
      </div>

      <h3 style={{ margin: '8px 0 4px', fontSize: 15 }}>{item.transcript}</h3>
      <div className="aos-rowmeta aos-mono">
        confidence {item.confidence.toFixed(2)}
        {item.detected_project ? ` · ${item.detected_project}` : ''}
      </div>

      {item.suggested_action ? (
        <p className="aos-muted" style={{ margin: '8px 0 0', fontSize: 13 }}>
          &rarr; {item.suggested_action}
        </p>
      ) : null}
      {item.reply_text ? (
        <p className="aos-mono aos-muted" style={{ margin: '6px 0 0', fontSize: 12 }}>
          &#9702; {item.reply_text}
        </p>
      ) : null}

      {pending ? (
        <div className="aos-form-row" style={{ marginTop: 10 }}>
          <button
            type="button"
            className="aos-btn aos-btn-sm"
            data-testid="voice-inbox-approve"
            disabled={busy !== null}
            onClick={() => void resolve('approved')}
          >
            {busy === 'approved' ? 'Approving…' : 'Approve'}
          </button>
          <button
            type="button"
            className="aos-btn-ghost aos-btn-sm"
            data-testid="voice-inbox-dismiss"
            disabled={busy !== null}
            onClick={() => void resolve('dismissed')}
          >
            {busy === 'dismissed' ? 'Dismissing…' : 'Dismiss'}
          </button>
        </div>
      ) : null}

      {error ? (
        <p role="alert" className="aos-error" style={{ margin: '8px 0 0' }}>
          {error}
        </p>
      ) : null}
    </li>
  );
}

export function VoiceInboxView() {
  const [items, setItems] = useState<VoiceInboxItem[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setItems(await fetchVoiceInbox());
    } catch (err) {
      // Graceful degradation: a missing/absent API must never blank the screen.
      setItems(null);
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const handleResolved = useCallback((id: string, state: VoiceReviewState) => {
    setItems((prev) => (prev ? prev.map((it) => (it.id === id ? { ...it, review_state: state } : it)) : prev));
  }, []);

  const sorted = items
    ? [...items].sort((a, b) => (STATE_RANK[a.review_state] ?? 9) - (STATE_RANK[b.review_state] ?? 9))
    : null;
  const pendingCount = items ? items.filter((it) => it.review_state === 'pending').length : 0;
  const isEmpty = items !== null && items.length === 0;

  return (
    <section className="aos-view" data-testid="voice-inbox-view">
      <div className="aos-view-head">
        <span className="aos-eyebrow" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ color: 'var(--signal)' }} aria-hidden="true">
            &#9672;
          </span>
          Operations · Voice Inbox
        </span>
        <h2 style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          Voice-captured work awaiting review
          {items !== null && pendingCount > 0 ? (
            <span className="aos-pill info" data-testid="voice-inbox-count">
              {pendingCount} pending
            </span>
          ) : null}
        </h2>
      </div>

      {error ? (
        <div className="aos-hud glass aos-card">
          <span className="aos-eyebrow">Voice Inbox</span>
          <p role="alert" className="aos-error" data-testid="voice-inbox-error" style={{ marginTop: 8 }}>
            Inbox unavailable: {error}
          </p>
          <p className="aos-muted" style={{ margin: '8px 0 0', fontSize: 13 }}>
            The queue reads <span className="aos-mono">GET /voice/inbox</span>. Once the API is reachable,
            captured commands appear here for review.
          </p>
        </div>
      ) : loading && items === null ? (
        <div className="aos-hud glass aos-card">
          <p className="aos-muted" data-testid="voice-inbox-loading" style={{ margin: 0 }}>
            Loading the voice inbox…
          </p>
        </div>
      ) : isEmpty ? (
        <div className="aos-hud glass aos-card">
          <span className="aos-eyebrow">Voice Inbox</span>
          <p className="aos-muted" data-testid="voice-inbox-empty" style={{ margin: '8px 0 0' }}>
            Nothing captured yet. Speak or type a command in the Command deck and it lands here for review.
          </p>
        </div>
      ) : sorted !== null ? (
        <ul className="aos-rows" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {sorted.map((item) => (
            <InboxCard key={item.id} item={item} onResolved={handleResolved} />
          ))}
        </ul>
      ) : null}

      <p className="aos-mono aos-muted" style={{ margin: '16px 0 0', fontSize: 11.5 }}>
        Review-first: approving records intent only. Promoting an approved draft into its concrete action
        (research task, decision, guardian review) is coming soon.
      </p>
    </section>
  );
}
