// Shared empty-state shown by any project-scoped view when no project is
// selected. Extracted from main.tsx (AOS-WEB-SPINE-001 slice 3b) so feature
// views split out of App can render the same notice.
export function SelectProjectNotice() {
  return (
    <div className="aos-legacy">
      <p style={{ margin: 0 }}>
        Select or create a project in the rail to load this view.
      </p>
    </div>
  );
}
