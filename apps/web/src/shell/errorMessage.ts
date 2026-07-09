// Shared error-to-string helper used by the shell and its context providers.
// Kept tiny and dependency-free so any layer (App, ProjectProvider, feature
// views) can normalize a thrown value into a user-facing message identically.
export const errorMessage = (err: unknown): string =>
  err instanceof Error ? err.message : 'Request failed';
