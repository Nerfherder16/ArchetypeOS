import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type Dispatch,
  type ReactNode,
  type SetStateAction,
} from 'react';
import { fetchProjects, fetchRepositories, type Project, type Repository } from '../api';
import { errorMessage } from './errorMessage';

// AOS-WEB-SPINE-001 (slice 2) — Project context provider.
//
// The active project/repository selection and the two catalogs it drives
// (projects, repositories) were held in bare component state inside the
// ~1900-line App. That coupled every project-scoped callback to App's local
// scope and made the file impossible to split by view. This provider owns
// exactly that slice of state (the selection + its two self-contained loaders)
// and exposes it via `useProjectContext()`. App destructures it at the top, so
// the ~90 downstream `selectedProjectId` / `setSelectedProjectId` / ... call
// sites are unchanged — this is a behavior-preserving extraction, not a rewrite.
export type ProjectContextValue = {
  projects: Project[];
  setProjects: Dispatch<SetStateAction<Project[]>>;
  projectsError: string | null;
  setProjectsError: Dispatch<SetStateAction<string | null>>;
  selectedProjectId: string | null;
  setSelectedProjectId: Dispatch<SetStateAction<string | null>>;
  repositories: Repository[];
  setRepositories: Dispatch<SetStateAction<Repository[]>>;
  repositoriesError: string | null;
  setRepositoriesError: Dispatch<SetStateAction<string | null>>;
  selectedRepositoryId: string | null;
  setSelectedRepositoryId: Dispatch<SetStateAction<string | null>>;
  loadProjects: () => Promise<void>;
  loadRepositories: (projectId: string) => Promise<void>;
};

const ProjectContext = createContext<ProjectContextValue | null>(null);

export function ProjectProvider({ children }: { children: ReactNode }) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectsError, setProjectsError] = useState<string | null>(null);
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);

  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [repositoriesError, setRepositoriesError] = useState<string | null>(null);
  const [selectedRepositoryId, setSelectedRepositoryId] = useState<string | null>(null);

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

  const value = useMemo<ProjectContextValue>(
    () => ({
      projects,
      setProjects,
      projectsError,
      setProjectsError,
      selectedProjectId,
      setSelectedProjectId,
      repositories,
      setRepositories,
      repositoriesError,
      setRepositoriesError,
      selectedRepositoryId,
      setSelectedRepositoryId,
      loadProjects,
      loadRepositories,
    }),
    [
      projects,
      projectsError,
      selectedProjectId,
      repositories,
      repositoriesError,
      selectedRepositoryId,
      loadProjects,
      loadRepositories,
    ],
  );

  return <ProjectContext.Provider value={value}>{children}</ProjectContext.Provider>;
}

export function useProjectContext(): ProjectContextValue {
  const ctx = useContext(ProjectContext);
  if (ctx === null) {
    throw new Error('useProjectContext must be used within a ProjectProvider');
  }
  return ctx;
}
