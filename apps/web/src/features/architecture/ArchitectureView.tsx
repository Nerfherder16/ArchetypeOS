import { useProjectContext } from '../../shell/ProjectContext';
import { useRepositoryData } from '../../shell/RepositoryDataContext';
import { SelectProjectNotice } from '../../shell/SelectProjectNotice';
import { ArchitectureStudio } from './ArchitectureStudio';

// AOS-WEB-SPINE-001 (slice 3c) — the Architecture surface, extracted verbatim
// from App's `case 'architecture'`. The graph rendering + operator corrections
// already lived in <ArchitectureStudio>; this moves the thin case wrapper (the
// project/repository guards and the onCorrected reload) out of App, reading
// selection from useProjectContext and the graph from useRepositoryData.
export function ArchitectureView() {
  const { selectedProjectId, selectedRepositoryId } = useProjectContext();
  const { architecture, architectureError, loadArchitecture } = useRepositoryData();

  if (!selectedProjectId) {
    return <SelectProjectNotice />;
  }

  if (!selectedRepositoryId) {
    return (
      <div className="aos-view">
        <div className="aos-view-head">
          <span className="aos-eyebrow">System map</span>
          <h2>Architecture</h2>
        </div>
        <div className="aos-hud glass aos-card">
          <p className="aos-muted" style={{ margin: 0 }}>
            Select a repository in the Repositories view and run a scan to load its architecture.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="aos-view">
      <div className="aos-view-head">
        <span className="aos-eyebrow">System map</span>
        <h2>Architecture</h2>
      </div>
      <ArchitectureStudio
        graph={architecture}
        error={architectureError}
        onCorrected={() => {
          if (selectedProjectId && selectedRepositoryId) {
            void loadArchitecture(selectedProjectId, selectedRepositoryId);
          }
        }}
      />
    </div>
  );
}
