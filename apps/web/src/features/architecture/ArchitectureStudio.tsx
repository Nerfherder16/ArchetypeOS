import React, { useMemo, useState } from 'react';
import {
  correctArchitectureEdge,
  correctArchitectureNode,
  type ArchitectureEdge,
  type ArchitectureGraph,
  type ArchitectureNode,
} from '../../api';

// AOS-ARCH-STUDIO-001 (UI) — the Architecture view becomes an editable model, not
// just a read surface (eval Finding 7). Clicking a node or edge opens a detail
// drawer showing its evidence, confidence, risks, and correction state, with an
// input to set or clear a manual correction. Corrections PATCH the backend and
// then refresh; the corrected graph feeds Council context (backend, #132).

const errorMessage = (err: unknown): string =>
  err instanceof Error ? err.message : 'Request failed';

type Selection =
  | { kind: 'node'; item: ArchitectureNode }
  | { kind: 'edge'; item: ArchitectureEdge };

function evidenceList(evidence: unknown[]): string[] {
  return evidence.map((e) => (typeof e === 'string' ? e : JSON.stringify(e)));
}

export function ArchitectureStudio({
  graph,
  error,
  onCorrected,
}: {
  graph: ArchitectureGraph | null;
  error: string | null;
  onCorrected: () => void;
}) {
  const [selection, setSelection] = useState<Selection | null>(null);
  const [draft, setDraft] = useState('');
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const labelById = useMemo(() => {
    const map = new Map<string, string>();
    for (const node of graph?.nodes ?? []) map.set(node.id, node.label);
    return map;
  }, [graph]);

  const select = (sel: Selection) => {
    setSelection(sel);
    setDraft(sel.item.manual_correction ?? '');
    setSaveError(null);
  };

  const save = async (override?: string) => {
    if (!selection) return;
    setSaving(true);
    setSaveError(null);
    try {
      const raw = override !== undefined ? override : draft;
      const next = raw.trim() ? raw.trim() : null;
      if (selection.kind === 'node') {
        await correctArchitectureNode(selection.item.id, next);
      } else {
        await correctArchitectureEdge(selection.item.id, next);
      }
      setSelection(null);
      onCorrected();
    } catch (err) {
      setSaveError(errorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  if (error) {
    return (
      <div className="aos-hud glass aos-card">
        <span className="aos-eyebrow">Dependency graph</span>
        <p role="alert" className="aos-error" data-testid="architecture-error">
          {error}
        </p>
      </div>
    );
  }

  if (!graph) {
    return (
      <div className="aos-hud glass aos-card">
        <p className="aos-muted" data-testid="architecture-loading" style={{ margin: 0 }}>
          Loading architecture...
        </p>
      </div>
    );
  }

  return (
    <div className="aos-hud glass aos-card" data-testid="architecture-studio">
      <span className="aos-eyebrow">Dependency graph</span>
      <div className="aos-pills" style={{ marginTop: 8 }}>
        <span className="aos-pill good">Nodes: {graph.nodes.length}</span>
        <span className="aos-pill good">Edges: {graph.edges.length}</span>
      </div>

      <h3 style={{ margin: '16px 0 6px', fontSize: 13 }}>Nodes</h3>
      <ul className="aos-rows" data-testid="architecture-nodes">
        {graph.nodes.map((node) => (
          <li key={node.id}>
            <button
              type="button"
              className="aos-nav-item"
              data-testid="architecture-node"
              data-node-id={node.id}
              onClick={() => select({ kind: 'node', item: node })}
              style={{ width: '100%', textAlign: 'left', cursor: 'pointer' }}
            >
              <span className="aos-strong">{node.label}</span>{' '}
              <span className="aos-rowmeta">({node.type}) · confidence {node.confidence}</span>
              {node.manual_correction ? (
                <span className="aos-pill warn" style={{ marginLeft: 8 }} data-testid="architecture-node-corrected">
                  corrected
                </span>
              ) : null}
            </button>
          </li>
        ))}
      </ul>

      <h3 style={{ margin: '16px 0 6px', fontSize: 13 }}>Edges</h3>
      {graph.edges.length === 0 ? (
        <p className="aos-muted" style={{ margin: 0, fontSize: 13 }}>No edges in this graph.</p>
      ) : (
        <ul className="aos-rows" data-testid="architecture-edges">
          {graph.edges.map((edge) => (
            <li key={edge.id}>
              <button
                type="button"
                className="aos-nav-item"
                data-testid="architecture-edge"
                data-edge-id={edge.id}
                onClick={() => select({ kind: 'edge', item: edge })}
                style={{ width: '100%', textAlign: 'left', cursor: 'pointer' }}
              >
                <span className="aos-mono">
                  {labelById.get(edge.from_node_id) ?? edge.from_node_id} → {labelById.get(edge.to_node_id) ?? edge.to_node_id}
                </span>{' '}
                <span className="aos-rowmeta">({edge.type}) · confidence {edge.confidence}</span>
                {edge.manual_correction ? (
                  <span className="aos-pill warn" style={{ marginLeft: 8 }}>corrected</span>
                ) : null}
              </button>
            </li>
          ))}
        </ul>
      )}

      {selection ? (
        <div
          className="aos-hud glass aos-card"
          data-testid="architecture-drawer"
          style={{ marginTop: 16, borderColor: 'var(--signal)' }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
            <span className="aos-eyebrow">{selection.kind === 'node' ? 'Node' : 'Edge'} detail</span>
            <button
              type="button"
              className="aos-btn-ghost aos-btn-sm"
              data-testid="architecture-drawer-close"
              onClick={() => setSelection(null)}
            >
              Close
            </button>
          </div>

          <h3 style={{ margin: '8px 0 4px' }} data-testid="architecture-drawer-title">
            {selection.kind === 'node'
              ? selection.item.label
              : `${labelById.get(selection.item.from_node_id) ?? selection.item.from_node_id} → ${labelById.get(selection.item.to_node_id) ?? selection.item.to_node_id}`}
          </h3>
          <div className="aos-rowmeta aos-mono">
            {selection.item.type} · confidence {selection.item.confidence}
          </div>

          <div style={{ marginTop: 10 }}>
            <span className="aos-eyebrow">Evidence</span>
            {evidenceList(selection.item.evidence).length > 0 ? (
              <ul className="aos-muted" data-testid="architecture-drawer-evidence" style={{ margin: '4px 0 0', paddingLeft: 18, fontSize: 12.5 }}>
                {evidenceList(selection.item.evidence).map((line, i) => (
                  <li key={i}>{line}</li>
                ))}
              </ul>
            ) : (
              <p className="aos-muted" style={{ margin: '4px 0 0', fontSize: 12.5 }}>No recorded evidence.</p>
            )}
          </div>

          {selection.kind === 'node' && selection.item.risks.length > 0 ? (
            <div style={{ marginTop: 10 }}>
              <span className="aos-eyebrow">Risks</span>
              <ul className="aos-muted" data-testid="architecture-drawer-risks" style={{ margin: '4px 0 0', paddingLeft: 18, fontSize: 12.5 }}>
                {evidenceList(selection.item.risks).map((line, i) => (
                  <li key={i}>{line}</li>
                ))}
              </ul>
            </div>
          ) : null}

          <div style={{ marginTop: 12 }}>
            <label className="aos-eyebrow" htmlFor="architecture-correction">
              Operator correction
            </label>
            <textarea
              id="architecture-correction"
              className="aos-input"
              data-testid="architecture-correction-input"
              value={draft}
              placeholder="Correct a wrong label or note what the scanner got wrong…"
              onChange={(event) => setDraft(event.target.value)}
              rows={2}
              style={{ width: '100%', marginTop: 4, resize: 'vertical' }}
            />
            {saveError ? (
              <p role="alert" className="aos-error" data-testid="architecture-correction-error" style={{ margin: '6px 0 0' }}>
                {saveError}
              </p>
            ) : null}
            <div className="aos-form-row" style={{ marginTop: 8 }}>
              <button
                type="button"
                className="aos-btn aos-btn-sm"
                data-testid="architecture-correction-save"
                disabled={saving}
                onClick={() => void save()}
              >
                {saving ? 'Saving…' : 'Save correction'}
              </button>
              {selection.item.manual_correction ? (
                <button
                  type="button"
                  className="aos-btn-ghost aos-btn-sm"
                  data-testid="architecture-correction-clear"
                  disabled={saving}
                  onClick={() => {
                    setDraft('');
                    void save('');
                  }}
                >
                  Clear correction
                </button>
              ) : null}
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
