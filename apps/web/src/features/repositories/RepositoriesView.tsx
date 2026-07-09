import React, { useCallback, useState } from 'react';
import { registerRepository, scanRepository } from '../../api';
import { errorMessage } from '../../shell/errorMessage';
import { useProjectContext } from '../../shell/ProjectContext';
import { useRepositoryData } from '../../shell/RepositoryDataContext';
import { SelectProjectNotice } from '../../shell/SelectProjectNotice';

// AOS-WEB-SPINE-001 (slice 3b) — the Repositories surface, extracted verbatim
// from App's `case 'repositories'`. It owns only its own form/scan UI state and
// its two handlers; the project selection comes from useProjectContext (slice 2)
// and the selected repo's DNA from useRepositoryData (slice 3a). Behavior is
// identical to the inline version — this is a move, not a rewrite.
export function RepositoriesView() {
  const {
    selectedProjectId,
    selectedRepositoryId,
    setSelectedRepositoryId,
    repositories,
    repositoriesError,
    setRepositoriesError,
    loadRepositories,
  } = useProjectContext();
  const { dna, dnaError, setDnaError, dnaLoading, loadDna, loadArchitecture } = useRepositoryData();

  const [newRepoName, setNewRepoName] = useState('');
  const [newRepoPath, setNewRepoPath] = useState('');
  const [registeringRepo, setRegisteringRepo] = useState(false);
  const [scanningRepoId, setScanningRepoId] = useState<string | null>(null);

  const handleRegisterRepository = useCallback(
    async (event: React.FormEvent) => {
      event.preventDefault();
      if (!selectedProjectId) {
        return;
      }
      const name = newRepoName.trim();
      const localPath = newRepoPath.trim();
      if (!name || !localPath) {
        return;
      }
      setRegisteringRepo(true);
      setRepositoriesError(null);
      try {
        await registerRepository(selectedProjectId, name, localPath);
        setNewRepoName('');
        setNewRepoPath('');
        await loadRepositories(selectedProjectId);
      } catch (err) {
        setRepositoriesError(errorMessage(err));
      } finally {
        setRegisteringRepo(false);
      }
    },
    [selectedProjectId, newRepoName, newRepoPath, loadRepositories, setRepositoriesError],
  );

  const handleScan = useCallback(
    async (repositoryId: string) => {
      if (!selectedProjectId) {
        return;
      }
      setScanningRepoId(repositoryId);
      setDnaError(null);
      try {
        await scanRepository(repositoryId);
        setSelectedRepositoryId(repositoryId);
        await Promise.all([
          loadDna(repositoryId),
          loadArchitecture(selectedProjectId, repositoryId),
          loadRepositories(selectedProjectId),
        ]);
      } catch (err) {
        setDnaError(errorMessage(err));
      } finally {
        setScanningRepoId(null);
      }
    },
    [
      selectedProjectId,
      loadDna,
      loadArchitecture,
      loadRepositories,
      setDnaError,
      setSelectedRepositoryId,
    ],
  );

  if (!selectedProjectId) {
    return <SelectProjectNotice />;
  }

  const summary = dna?.scan_summary.summary;
  const primaryLanguages =
    summary?.primary_language_hints && summary.primary_language_hints.length > 0
      ? summary.primary_language_hints
      : dna
        ? Object.keys(dna.language_mix)
        : [];

  return (
    <div className="aos-view">
      <div className="aos-view-head">
        <span className="aos-eyebrow">Portfolio</span>
        <h2>Repositories</h2>
      </div>
      <div className="aos-hud glass aos-card">
        <span className="aos-eyebrow">Registered repositories</span>
        {repositoriesError ? <p role="alert" className="aos-error">{repositoriesError}</p> : null}
        {repositories.length === 0 ? (
          <p className="aos-muted" style={{ margin: 0 }}>No repositories registered yet.</p>
        ) : (
          <table className="aos-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Local path</th>
                <th>Last scanned</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {repositories.map((repository) => {
                const selected = repository.id === selectedRepositoryId;
                return (
                  <tr key={repository.id} className={selected ? 'sel' : undefined}>
                    <td>
                      <button
                        type="button"
                        className={`aos-linkbtn${selected ? ' sel' : ''}`}
                        onClick={() => setSelectedRepositoryId(repository.id)}
                      >
                        {repository.name}
                      </button>
                    </td>
                    <td>{repository.local_path}</td>
                    <td>{repository.last_scanned_at ?? 'never'}</td>
                    <td>
                      <button
                        type="button"
                        className="aos-btn aos-btn-sm"
                        disabled={scanningRepoId === repository.id}
                        onClick={() => void handleScan(repository.id)}
                      >
                        {scanningRepoId === repository.id ? 'Scanning...' : 'Run scan'}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
        <form onSubmit={handleRegisterRepository} className="aos-form-row">
          <input
            className="aos-input"
            type="text"
            value={newRepoName}
            placeholder="Repository name"
            onChange={(event) => setNewRepoName(event.target.value)}
            style={{ width: 'auto', flex: '1 1 180px' }}
          />
          <input
            className="aos-input"
            type="text"
            value={newRepoPath}
            placeholder="Local path"
            onChange={(event) => setNewRepoPath(event.target.value)}
            style={{ width: 'auto', flex: '1 1 180px' }}
          />
          <button type="submit" className="aos-btn aos-btn-sm" disabled={registeringRepo}>
            {registeringRepo ? 'Registering...' : 'Register repository'}
          </button>
        </form>
      </div>

      {selectedRepositoryId ? (
        <div className="aos-hud glass aos-card">
          <span className="aos-eyebrow">Scan summary</span>
          {dnaError ? <p role="alert" className="aos-error">{dnaError}</p> : null}
          {dnaLoading ? <p className="aos-muted" style={{ margin: 0 }}>Loading scan summary…</p> : null}
          {!dnaLoading && !dnaError && dna === null ? (
            <p className="aos-muted" style={{ margin: 0 }}>No scan recorded yet.</p>
          ) : null}
          {dna ? (
            <>
              <dl className="aos-kv">
                {/* AOS-CONTRACT-001: surface the reasoned DNA evidence the backend computes. */}
                {dna.purpose ? (
                  <>
                    <dt>Purpose</dt>
                    <dd>{dna.purpose}</dd>
                  </>
                ) : null}
                {dna.maturity ? (
                  <>
                    <dt>Maturity</dt>
                    <dd className="aos-mono">{dna.maturity}</dd>
                  </>
                ) : null}
                <dt>Primary languages</dt>
                <dd className="aos-mono">{primaryLanguages.length > 0 ? primaryLanguages.join(', ') : 'none'}</dd>
                <dt>Frameworks</dt>
                <dd className="aos-mono" data-testid="dna-frameworks">{dna.frameworks.length > 0 ? dna.frameworks.join(', ') : 'none'}</dd>
                <dt>Runtime services</dt>
                <dd className="aos-mono" data-testid="dna-runtime-services">{dna.runtime_services.length > 0 ? dna.runtime_services.join(', ') : 'none'}</dd>
                <dt>Package managers</dt>
                <dd className="aos-mono">{dna.package_managers.length > 0 ? dna.package_managers.join(', ') : 'none'}</dd>
                <dt>Confidence</dt>
                <dd className="aos-mono">{dna.confidence}</dd>
              </dl>
              <h3>Signals</h3>
              <div className="aos-pills">
                <span className={`aos-pill ${summary?.has_docker ? 'good' : ''}`}>Docker: {summary?.has_docker ? 'yes' : 'no'}</span>
                <span className={`aos-pill ${summary?.has_ci ? 'good' : ''}`}>CI: {summary?.has_ci ? 'yes' : 'no'}</span>
                <span className={`aos-pill ${summary?.has_tests ? 'good' : ''}`}>Tests: {summary?.has_tests ? 'yes' : 'no'}</span>
                <span className={`aos-pill ${summary?.has_env_example ? 'good' : ''}`}>Env example: {summary?.has_env_example ? 'yes' : 'no'}</span>
              </div>
              <h3>Risk flags</h3>
              {dna.risk_flags.length > 0 ? (
                <div className="aos-pills">
                  {dna.risk_flags.map((flag, index) => (
                    <span key={index} className="aos-pill risk">{flag}</span>
                  ))}
                </div>
              ) : (
                <p className="aos-muted" style={{ margin: 0 }}>No risk flags.</p>
              )}
            </>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
