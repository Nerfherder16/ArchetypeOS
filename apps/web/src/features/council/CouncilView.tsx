import { useProjectContext } from '../../shell/ProjectContext';
import { SelectProjectNotice } from '../../shell/SelectProjectNotice';
import { AgentCouncilSection } from './AgentCouncilSection';
import { CouncilProvider, useCouncil } from './CouncilContext';
import { DecisionLoopSection } from './DecisionLoopSection';
import { ResearchSection } from './ResearchSection';

// AOS-WEB-SPINE-001 (slice 3f) — the Governance (Council) surface, extracted
// from App's `case 'council'`. CouncilProvider owns the shared artifacts +
// council state and loads on project change; the three sections are
// presentational. The provider mounts only when a project is selected.
function CouncilContent() {
  const { artifactsError } = useCouncil();
  return (
    <section className="aos-view">
      <div className="aos-view-head">
        <span className="aos-eyebrow">Governance</span>
        <h2>Decisions &amp; Research</h2>
      </div>
      {artifactsError ? (
        <p role="alert" className="aos-error">
          {artifactsError}
        </p>
      ) : null}
      <DecisionLoopSection />
      <ResearchSection />
      <AgentCouncilSection />
    </section>
  );
}

export function CouncilView() {
  const { selectedProjectId } = useProjectContext();
  if (!selectedProjectId) {
    return <SelectProjectNotice />;
  }
  return (
    <CouncilProvider>
      <CouncilContent />
    </CouncilProvider>
  );
}
