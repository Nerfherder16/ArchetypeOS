import { useCouncil } from './CouncilContext';

// AOS-WEB-SPINE-001 (slice 3f) — the Research & recommendations section (notes
// + recommendations lists, plus the create-note and create-decision forms),
// moved verbatim from App's `case 'council'`. Reads from useCouncil().
export function ResearchSection() {
  const {
    researchNotes,
    recommendations,
    newNoteTitle,
    setNewNoteTitle,
    newNoteSummary,
    setNewNoteSummary,
    creatingNote,
    handleCreateResearchNote,
    newDecisionTitle,
    setNewDecisionTitle,
    newDecisionText,
    setNewDecisionText,
    newDecisionNoteId,
    setNewDecisionNoteId,
    creatingDecision,
    handleCreateDecision,
  } = useCouncil();

  return (
    <div className="aos-hud glass aos-card">
      <span className="aos-eyebrow">Research &amp; recommendations</span>
      <h3 style={{ marginTop: 0 }}>Research Notes</h3>
      {researchNotes.length === 0 ? (
        <p className="aos-muted" style={{ margin: 0 }}>No research notes yet.</p>
      ) : (
        <ul className="aos-rows">
          {researchNotes.map((note) => (
            <li key={note.id}>
              <span>{note.title}</span>{' '}
              <span className="aos-rowmeta">{note.freshness ?? 'unset'}</span>
            </li>
          ))}
        </ul>
      )}

      <h3>Recommendations</h3>
      {recommendations.length === 0 ? (
        <p className="aos-muted" style={{ margin: 0 }}>No recommendations yet.</p>
      ) : (
        <ul className="aos-rows">
          {recommendations.map((recommendation) => (
            <li key={recommendation.id}>
              <span>{recommendation.title}</span>{' '}
              <span className="aos-rowmeta">{recommendation.evidence.length} evidence items</span>
            </li>
          ))}
        </ul>
      )}

      <form onSubmit={handleCreateResearchNote} className="aos-form-row">
        <input
          className="aos-input"
          type="text"
          value={newNoteTitle}
          placeholder="Research note title"
          onChange={(event) => setNewNoteTitle(event.target.value)}
          style={{ width: 'auto', flex: '1 1 200px' }}
        />
        <input
          className="aos-input"
          type="text"
          value={newNoteSummary}
          placeholder="Summary"
          onChange={(event) => setNewNoteSummary(event.target.value)}
          style={{ width: 'auto', flex: '1 1 200px' }}
        />
        <button type="submit" className="aos-btn aos-btn-sm" disabled={creatingNote}>
          {creatingNote ? 'Adding...' : 'Add research note'}
        </button>
      </form>

      <form onSubmit={handleCreateDecision} className="aos-form-row">
        <input
          className="aos-input"
          type="text"
          value={newDecisionTitle}
          placeholder="Decision title"
          onChange={(event) => setNewDecisionTitle(event.target.value)}
          style={{ width: 'auto', flex: '1 1 200px' }}
        />
        <input
          className="aos-input"
          type="text"
          value={newDecisionText}
          placeholder="Decision text"
          onChange={(event) => setNewDecisionText(event.target.value)}
          style={{ width: 'auto', flex: '1 1 200px' }}
        />
        <select
          className="aos-input"
          value={newDecisionNoteId}
          onChange={(event) => setNewDecisionNoteId(event.target.value)}
          style={{ width: 'auto' }}
        >
          <option value="">No linked research</option>
          {researchNotes.map((note) => (
            <option key={note.id} value={note.id}>
              {note.title}
            </option>
          ))}
        </select>
        <button type="submit" className="aos-btn aos-btn-sm" disabled={creatingDecision}>
          {creatingDecision ? 'Adding...' : 'Add decision'}
        </button>
      </form>
    </div>
  );
}
