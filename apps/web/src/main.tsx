import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';

type Health = { status: string; api: boolean; database: boolean; redis: boolean };
type Project = { id: string; name: string; slug: string; description?: string; status: string };

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

function App() {
  const [health, setHealth] = useState<Health | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const healthResponse = await fetch(`${API_BASE_URL}/health`);
        setHealth(await healthResponse.json());
        const projectResponse = await fetch(`${API_BASE_URL}/projects`);
        setProjects(await projectResponse.json());
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load dashboard data');
      }
    }
    load();
  }, []);

  return (
    <main style={{ fontFamily: 'system-ui, sans-serif', padding: 24 }}>
      <h1>ArchetypeOS</h1>
      <p>Engineering Intelligence Platform runtime shell.</p>

      <section>
        <h2>Runtime Health</h2>
        {health ? (
          <ul>
            <li>API: {health.api ? 'ok' : 'down'}</li>
            <li>Postgres: {health.database ? 'ok' : 'down'}</li>
            <li>Redis: {health.redis ? 'ok' : 'down'}</li>
          </ul>
        ) : (
          <p>Loading health...</p>
        )}
      </section>

      <section>
        <h2>Projects</h2>
        {projects.length === 0 ? <p>No projects registered yet.</p> : null}
        <ul>
          {projects.map((project) => (
            <li key={project.id}>{project.name} — {project.status}</li>
          ))}
        </ul>
      </section>

      <section>
        <h2>v0.1 Placeholders</h2>
        <ul>
          <li>Repository scan results</li>
          <li>Architecture graph draft</li>
          <li>Nightly digest view</li>
          <li>Voice inbox text capture</li>
        </ul>
      </section>

      {error ? <p role="alert">{error}</p> : null}
    </main>
  );
}

createRoot(document.getElementById('root')!).render(<App />);
