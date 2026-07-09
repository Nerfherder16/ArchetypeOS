import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type Dispatch,
  type ReactNode,
  type SetStateAction,
} from 'react';
import {
  fetchArchitecture,
  fetchDna,
  type ArchitectureGraph,
  type RepositoryDna,
} from '../api';
import { errorMessage } from './errorMessage';
import { useProjectContext } from './ProjectContext';

// AOS-WEB-SPINE-001 (slice 3a) — Repository data provider.
//
// The selected repository's DNA (scan summary) and architecture graph are async
// data keyed on `selectedRepositoryId` (owned by ProjectContext, slice 2). They
// were loaded by an effect buried in the ~1900-line App, which coupled the
// Repositories and Architecture views to App's local scope and blocked splitting
// either into its own module. This provider owns that repository-scoped data and
// its co-load lifecycle; it consumes `useProjectContext()` for the current
// selection, so it must be mounted inside `ProjectProvider`.
export type RepositoryDataContextValue = {
  dna: RepositoryDna | null;
  dnaError: string | null;
  setDnaError: Dispatch<SetStateAction<string | null>>;
  dnaLoading: boolean;
  loadDna: (repositoryId: string) => Promise<void>;
  architecture: ArchitectureGraph | null;
  architectureError: string | null;
  loadArchitecture: (projectId: string, repositoryId: string) => Promise<void>;
};

const RepositoryDataContext = createContext<RepositoryDataContextValue | null>(null);

export function RepositoryDataProvider({ children }: { children: ReactNode }) {
  const { selectedProjectId, selectedRepositoryId } = useProjectContext();

  const [dna, setDna] = useState<RepositoryDna | null>(null);
  const [dnaError, setDnaError] = useState<string | null>(null);
  const [dnaLoading, setDnaLoading] = useState(false);

  const [architecture, setArchitecture] = useState<ArchitectureGraph | null>(null);
  const [architectureError, setArchitectureError] = useState<string | null>(null);

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

  // Co-load the selected repository's DNA + architecture; clear both when no
  // repository is selected (e.g. after switching projects, which nulls
  // selectedRepositoryId in ProjectContext).
  useEffect(() => {
    if (selectedProjectId && selectedRepositoryId) {
      void loadDna(selectedRepositoryId);
      void loadArchitecture(selectedProjectId, selectedRepositoryId);
    } else {
      setDna(null);
      setArchitecture(null);
    }
  }, [selectedProjectId, selectedRepositoryId, loadDna, loadArchitecture]);

  const value = useMemo<RepositoryDataContextValue>(
    () => ({
      dna,
      dnaError,
      setDnaError,
      dnaLoading,
      loadDna,
      architecture,
      architectureError,
      loadArchitecture,
    }),
    [dna, dnaError, dnaLoading, loadDna, architecture, architectureError, loadArchitecture],
  );

  return <RepositoryDataContext.Provider value={value}>{children}</RepositoryDataContext.Provider>;
}

export function useRepositoryData(): RepositoryDataContextValue {
  const ctx = useContext(RepositoryDataContext);
  if (ctx === null) {
    throw new Error('useRepositoryData must be used within a RepositoryDataProvider');
  }
  return ctx;
}
