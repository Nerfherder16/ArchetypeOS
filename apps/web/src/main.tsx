import React, { useCallback, useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import {
  createProject,
  fetchArchitecture,
  fetchDna,
  fetchHealth,
  fetchProjects,
  fetchRepositories,
  registerRepository,
  scanRepository,
  type ArchitectureGraph,
  type Health,
  type Project,
  type Repository,
  type RepositoryDna,
} from './api';

const errorMessage = (err: unknown): string =>
  err instanceof Error ? err.message : 'Request failed';

const sectionStyle: React.CSSProperties = {
  marginTop: 24,
  paddingTop: 16,
  borderTop: '1px solid #ddd',
};

const errorStyle: React.CSSProperties = { color: '#b00020' };

function App() {
  const [health, setHealth] = useState<Health | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);

  const [projects, setProjects] = useState<Project[]>([]);
  const [projectsError, setProjectsError] = useState<string | null>(null);
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [newProjectName, setNewProjectName] = useState('');
  const [creatingProject, setCreatingProject] = useState(false);

  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [repositoriesError, setRepositoriesError] = useState<string | null>(null);
  const [selectedRepositoryId, setSelectedRepositoryId] = useState<string | null>(null);
  const [newRepoName, setNewRepoName] = useState('');
  const [newRepoPath, setNewRepoPath] = useState('');
  const [registeringRepo, setRegisteringRepo] = useState(false);
  const [scanningRepoId, setScanningRepoId] = useState<string | null>(null);

  const [dna, setDna] = useState<RepositoryDna | null>(null);
  const [dnaError, setDnaError] = useState<string | null>(null);
  const [dnaLoading, setDnaLoading] = useState(false);

  const [architecture, setArchitecture] = useState<ArchitectureGraph | null>(null);
  const [architectureError, setArchitectureError] = useState<string | null>(null);

  const loadHealth = useCallback(async () => {
    setHealthError(null);
    try {
      setHealth(await fetchHealth());
    } catch (err) {
      setHealth(null);
      setHealthError(errorMessage(err));
    }
  }, []);

  const loadProjects = useCallback(async () => {
    setProjectsError(null);
    try {
      setProjects(await fetchProjects());
    } catch (err) {
      setProjectsError(errorMessage(err));
    }
  }, []);

  const loadRepositories = useCallback(async (projectId: string) => {
    setRepositoriesError(null);
    try {
      setRepositories(await fetchRepositories(projectId));
    } catch (err) {
      setRepositories([]);
      setRepositoriesError(errorMessage(err));
    }
  }, []);

  const loadDna = useCallback(async (repositoryId: string) => {
    setDnaError(null);
    setDnaLoading(true);
    try {
      setDna(await fetchDna(repositoryId));
    } catch (err) {
      setDna(null);
      setDnaError(errorMessage(err));
    } finally {
      setDnaLoading(false);
    }
  }, []);

  const loadArchitecture = useCallback(async (projectId: string, repositoryId: string) => {
    setArchitectureError(null);
    try {
      setArchitecture(await fetchArchitecture(projectId, repositoryId));
    } catch (err) {
      setArchitecture(null);
      setArchitectureError(errorMessage(err));
    }
  }, []);

  useEffect(() => {
    void loadHealth();
    void loadProjects();
  }, [loadHealth, loadProjects]);

  useEffect(() => {
    setSelectedRepositoryId(null);
    setRepositories([]);
    setDna(null);
    setArchitecture(null);
    if (selectedProjectId) {
      void loadRepositories(selectedProjectId);
    }
  }, [selectedProjectId, loadRepositories]);

  useEffect(() => {
    if (selectedProjectId && selectedRepositoryId) {
      void loadDna(selectedRepositoryId);
      void loadArchitecture(selectedProjectId, selectedRepositoryId);
    } else {
      setDna(null);
      setArchitecture(null);
    }
  }, [selectedProjectId, selectedRepositoryId, loadDna, loadArchitecture]);

  const handleCreateProject = useCallback(
    async (event: React.FormEvent) => {
      event.preventDefault();
      const name = newProjectName.trim();
      if (!name) {
        return;
      }
      setCreatingProject(true);
      setProjectsError(null);
      try {
        const created = await createProject(name);
        setNewProjectName('');
        await loadProjects();
        setSelectedProjectId(created.id);
      } catch (err) {
        setProjectsError(errorMessage(err));
      } finally {
        setCreatingProject(false);
      }
    },
    [newProjectName, loadProjects],
  );

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
    [selectedProjectId, newRepoName, newRepoPath, loadRepositories],
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
    [selectedProjectId, loadDna, loadArchitecture, loadRepositories],
  );

  const summary = dna?.scan_summary.summary;
  const primaryLanguages =
    summary?.primary_language_hints && summary.primary_language_hints.length > 0
      ? summary.primary_language_hints
      : dna
        ? Object.keys(dna.language_mix)
        : [];

  return (
    <main style={{ fontFamily: 'system-ui, sans-serif', padding: 24, maxWidth: 900 }}>
      <header>
        <h1 style={{ marginBottom: 4 }}>ArchetypeOS</h1>
        <p style={{ margin: 0, color: '#555' }}>Engineering Control Tower</p>
      </header>

      <section style={sectionStyle}>
        <h2>Runtime Health</h2>
        {healthError ? (
          <p role="alert" style={errorStyle}>
            Health unavailable: {healthError}
          </p>
        ) : health ? (
          <ul>
            <li>API: {health.api ? 'ok' : 'down'}</li>
            <li>Postgres: {health.database ? 'ok' : 'down'}</li>
            <li>Redis: {health.redis ? 'ok' : 'down'}</li>
          </ul>
        ) : (
          <p>Loading health...</p>
        )}
      </section>

      <section style={sectionStyle}>
        <h2>Projects</h2>
        {projectsError ? (
          <p role="alert" style={errorStyle}>
            {projectsError}
          </p>
        ) : null}
        {projects.length === 0 ? <p>No projects registered yet.</p> : null}
        <ul style={{ listStyle: 'none', padding: 0 }}>
          {projects.map((project) => {
            const selected = project.id === selectedProjectId;
            return (
              <li key={project.id} style={{ marginBottom: 4 }}>
                <button
                  type="button"
                  onClick={() => setSelectedProjectId(project.id)}
                  style={{
                    cursor: 'pointer',
                    padding: '6px 10px',
                    border: selected ? '2px solid #0b57d0' : '1px solid #ccc',
                    background: selected ? '#e8f0fe' : '#fff',
                    fontWeight: selected ? 600 : 400,
                  }}
                >
                  {project.name} — {project.status}
                </button>
              </li>
            );
          })}
        </ul>
        <form onSubmit={handleCreateProject} style={{ marginTop: 8 }}>
          <input
            type="text"
            value={newProjectName}
            placeholder="New project name"
            onChange={(event) => setNewProjectName(event.target.value)}
          />
          <button type="submit" disabled={creatingProject} style={{ marginLeft: 8 }}>
            {creatingProject ? 'Creating...' : 'Create project'}
          </button>
        </form>
      </section>

      {selectedProjectId ? (
        <section style={sectionStyle}>
          <h2>Repositories</h2>
          {repositoriesError ? (
            <p role="alert" style={errorStyle}>
              {repositoriesError}
            </p>
          ) : null}
          {repositories.length === 0 ? <p>No repositories registered yet.</p> : null}
          {repositories.length > 0 ? (
            <table style={{ borderCollapse: 'collapse', width: '100%' }}>
              <thead>
                <tr style={{ textAlign: 'left' }}>
                  <th style={{ padding: 4 }}>Name</th>
                  <th style={{ padding: 4 }}>Local path</th>
                  <th style={{ padding: 4 }}>Last scanned</th>
                  <th style={{ padding: 4 }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {repositories.map((repository) => {
                  const selected = repository.id === selectedRepositoryId;
                  return (
                    <tr
                      key={repository.id}
                      style={{ background: selected ? '#e8f0fe' : 'transparent' }}
                    >
                      <td style={{ padding: 4 }}>
                        <button
                          type="button"
                          onClick={() => setSelectedRepositoryId(repository.id)}
                          style={{
                            cursor: 'pointer',
                            border: 'none',
                            background: 'none',
                            padding: 0,
                            fontWeight: selected ? 600 : 400,
                            textDecoration: 'underline',
                            color: '#0b57d0',
                          }}
                        >
                          {repository.name}
                        </button>
                      </td>
                      <td style={{ padding: 4 }}>{repository.local_path}</td>
                      <td style={{ padding: 4 }}>{repository.last_scanned_at ?? 'never'}</td>
                      <td style={{ padding: 4 }}>
                        <button
                          type="button"
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
          ) : null}
          <form onSubmit={handleRegisterRepository} style={{ marginTop: 8 }}>
            <input
              type="text"
              value={newRepoName}
              placeholder="Repository name"
              onChange={(event) => setNewRepoName(event.target.value)}
            />
            <input
              type="text"
              value={newRepoPath}
              placeholder="Local path"
              onChange={(event) => setNewRepoPath(event.target.value)}
              style={{ marginLeft: 8 }}
            />
            <button type="submit" disabled={registeringRepo} style={{ marginLeft: 8 }}>
              {registeringRepo ? 'Registering...' : 'Register repository'}
            </button>
          </form>
        </section>
      ) : null}

      {selectedRepositoryId ? (
        <section style={sectionStyle}>
          <h2>Scan Summary</h2>
          {dnaError ? (
            <p role="alert" style={errorStyle}>
              {dnaError}
            </p>
          ) : null}
          {dnaLoading ? <p>Loading scan summary...</p> : null}
          {!dnaLoading && !dnaError && dna === null ? <p>No scan recorded yet.</p> : null}
          {dna ? (
            <div>
              <p>
                <strong>Primary languages:</strong>{' '}
                {primaryLanguages.length > 0 ? primaryLanguages.join(', ') : 'none'}
              </p>
              <p>
                <strong>Package managers:</strong>{' '}
                {dna.package_managers.length > 0 ? dna.package_managers.join(', ') : 'none'}
              </p>
              <ul>
                <li>Has Docker: {summary?.has_docker ? 'yes' : 'no'}</li>
                <li>Has CI: {summary?.has_ci ? 'yes' : 'no'}</li>
                <li>Has tests: {summary?.has_tests ? 'yes' : 'no'}</li>
                <li>Has env example: {summary?.has_env_example ? 'yes' : 'no'}</li>
              </ul>
              <p>
                <strong>Risk flags:</strong>
              </p>
              {dna.risk_flags.length > 0 ? (
                <ul>
                  {dna.risk_flags.map((flag, index) => (
                    <li key={index}>{flag}</li>
                  ))}
                </ul>
              ) : (
                <p>No risk flags.</p>
              )}
              <p>
                <strong>Confidence:</strong> {dna.confidence}
              </p>
            </div>
          ) : null}
        </section>
      ) : null}

      {selectedRepositoryId ? (
        <section style={sectionStyle}>
          <h2>Architecture</h2>
          {architectureError ? (
            <p role="alert" style={errorStyle}>
              {architectureError}
            </p>
          ) : null}
          {architecture ? (
            <div>
              <p>
                Nodes: {architecture.nodes.length} · Edges: {architecture.edges.length}
              </p>
              <ul>
                {architecture.nodes.map((node) => (
                  <li key={node.id}>
                    {node.label} ({node.type}) — confidence {node.confidence}
                  </li>
                ))}
              </ul>
            </div>
          ) : !architectureError ? (
            <p>Loading architecture...</p>
          ) : null}
        </section>
      ) : null}

      <section style={sectionStyle}>
        <h2>v0.1 Placeholders</h2>
        <ul>
          <li>Nightly digest view</li>
          <li>Voice inbox text capture</li>
        </ul>
      </section>
    </main>
  );
}

createRoot(document.getElementById('root')!).render(<App />);
