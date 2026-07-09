import React, { useCallback, useEffect, useState } from 'react';
import {
  createSchedule,
  deleteSchedule,
  enqueueJob,
  fetchJobs,
  fetchSchedules,
  runSchedule,
  setScheduleEnabled,
  type Job,
  type Schedule,
} from '../../api';
import { errorMessage } from '../../shell/errorMessage';
import { useProjectContext } from '../../shell/ProjectContext';
import { SelectProjectNotice } from '../../shell/SelectProjectNotice';

// AOS-WEB-SPINE-001 (slice 3e) — the Scheduling & Jobs surface, extracted from
// App's `case 'scheduling'`. Schedules and jobs are used by no other view, so
// this is a fully self-contained module: it owns its state, its two loaders,
// and its handlers, and loads on selected-project change via useProjectContext.
// The scan-job dropdown reads the shared `repositories` from ProjectContext.
export function SchedulingView() {
  const { selectedProjectId, repositories } = useProjectContext();

  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [schedulingError, setSchedulingError] = useState<string | null>(null);
  const [newScheduleName, setNewScheduleName] = useState('');
  const [newScheduleJobType, setNewScheduleJobType] = useState('repository_scan');
  const [newScheduleInterval, setNewScheduleInterval] = useState('3600');
  const [creatingSchedule, setCreatingSchedule] = useState(false);
  const [scanJobRepoId, setScanJobRepoId] = useState('');
  const [schedulingBusy, setSchedulingBusy] = useState(false);

  const loadScheduling = useCallback(async (projectId: string) => {
    setSchedulingError(null);
    try {
      const [nextSchedules, nextJobs] = await Promise.all([
        fetchSchedules(projectId),
        fetchJobs(projectId),
      ]);
      setSchedules(nextSchedules);
      setJobs(nextJobs);
    } catch (err) {
      setSchedules([]);
      setJobs([]);
      setSchedulingError(errorMessage(err));
    }
  }, []);

  const loadJobs = useCallback(async (projectId: string) => {
    setSchedulingError(null);
    try {
      setJobs(await fetchJobs(projectId));
    } catch (err) {
      setJobs([]);
      setSchedulingError(errorMessage(err));
    }
  }, []);

  useEffect(() => {
    if (selectedProjectId) {
      void loadScheduling(selectedProjectId);
    } else {
      setSchedules([]);
      setJobs([]);
    }
  }, [selectedProjectId, loadScheduling]);

  const handleCreateSchedule = useCallback(
    async (event: React.FormEvent) => {
      event.preventDefault();
      if (!selectedProjectId) {
        return;
      }
      const name = newScheduleName.trim();
      const intervalSeconds = Number.parseInt(newScheduleInterval, 10);
      if (!name || !Number.isFinite(intervalSeconds) || intervalSeconds <= 0) {
        return;
      }
      setCreatingSchedule(true);
      setSchedulingError(null);
      try {
        await createSchedule(selectedProjectId, {
          name,
          job_type: newScheduleJobType,
          interval_seconds: intervalSeconds,
        });
        setNewScheduleName('');
        setNewScheduleInterval('3600');
        await loadScheduling(selectedProjectId);
      } catch (err) {
        setSchedulingError(errorMessage(err));
      } finally {
        setCreatingSchedule(false);
      }
    },
    [selectedProjectId, newScheduleName, newScheduleJobType, newScheduleInterval, loadScheduling],
  );

  const handleRunSchedule = useCallback(
    async (scheduleId: string) => {
      if (!selectedProjectId) {
        return;
      }
      setSchedulingBusy(true);
      setSchedulingError(null);
      try {
        await runSchedule(scheduleId);
        await loadScheduling(selectedProjectId);
      } catch (err) {
        setSchedulingError(errorMessage(err));
      } finally {
        setSchedulingBusy(false);
      }
    },
    [selectedProjectId, loadScheduling],
  );

  const handleToggleSchedule = useCallback(
    async (schedule: Schedule) => {
      if (!selectedProjectId) {
        return;
      }
      setSchedulingBusy(true);
      setSchedulingError(null);
      try {
        await setScheduleEnabled(schedule.id, !schedule.enabled);
        await loadScheduling(selectedProjectId);
      } catch (err) {
        setSchedulingError(errorMessage(err));
      } finally {
        setSchedulingBusy(false);
      }
    },
    [selectedProjectId, loadScheduling],
  );

  const handleDeleteSchedule = useCallback(
    async (scheduleId: string) => {
      if (!selectedProjectId) {
        return;
      }
      setSchedulingBusy(true);
      setSchedulingError(null);
      try {
        await deleteSchedule(scheduleId);
        await loadScheduling(selectedProjectId);
      } catch (err) {
        setSchedulingError(errorMessage(err));
      } finally {
        setSchedulingBusy(false);
      }
    },
    [selectedProjectId, loadScheduling],
  );

  const handleEnqueueDigest = useCallback(async () => {
    if (!selectedProjectId) {
      return;
    }
    setSchedulingBusy(true);
    setSchedulingError(null);
    try {
      await enqueueJob({ project_id: selectedProjectId, job_type: 'project_digest' });
      await loadJobs(selectedProjectId);
    } catch (err) {
      setSchedulingError(errorMessage(err));
    } finally {
      setSchedulingBusy(false);
    }
  }, [selectedProjectId, loadJobs]);

  const handleEnqueueScan = useCallback(async () => {
    if (!selectedProjectId || !scanJobRepoId) {
      return;
    }
    setSchedulingBusy(true);
    setSchedulingError(null);
    try {
      await enqueueJob({
        project_id: selectedProjectId,
        repository_id: scanJobRepoId,
        job_type: 'repository_scan',
      });
      await loadJobs(selectedProjectId);
    } catch (err) {
      setSchedulingError(errorMessage(err));
    } finally {
      setSchedulingBusy(false);
    }
  }, [selectedProjectId, scanJobRepoId, loadJobs]);

  if (!selectedProjectId) {
    return <SelectProjectNotice />;
  }

  return (
    <div className="aos-view">
      <div className="aos-view-head">
        <span className="aos-eyebrow">Automation</span>
        <h2>Scheduling &amp; Jobs</h2>
      </div>

      <div className="aos-hud glass aos-card">
        <span className="aos-eyebrow">Schedules</span>
        {schedulingError ? (
          <p role="alert" className="aos-error">
            {schedulingError}
          </p>
        ) : null}
        {schedules.length === 0 ? (
          <p className="aos-muted" style={{ margin: 0 }}>No schedules yet.</p>
        ) : (
          <ul className="aos-rows">
            {schedules.map((schedule) => (
              <li key={schedule.id}>
                <span>
                  {schedule.name} — {schedule.job_type} — every {schedule.interval_seconds}s —{' '}
                  {schedule.enabled ? 'enabled' : 'disabled'} — next{' '}
                  {new Date(schedule.next_run_at).toLocaleString()}
                </span>
                <button
                  type="button"
                  className="aos-btn-ghost aos-btn-sm"
                  disabled={schedulingBusy}
                  onClick={() => void handleToggleSchedule(schedule)}
                >
                  {schedule.enabled ? 'Disable' : 'Enable'}
                </button>
                <button
                  type="button"
                  className="aos-btn aos-btn-sm"
                  disabled={schedulingBusy}
                  onClick={() => void handleRunSchedule(schedule.id)}
                >
                  Run now
                </button>
                <button
                  type="button"
                  className="aos-btn-ghost aos-btn-sm"
                  disabled={schedulingBusy}
                  onClick={() => void handleDeleteSchedule(schedule.id)}
                >
                  Delete
                </button>
              </li>
            ))}
          </ul>
        )}

        <form onSubmit={handleCreateSchedule} className="aos-form-row">
          <input
            className="aos-input"
            type="text"
            value={newScheduleName}
            placeholder="Schedule name"
            onChange={(event) => setNewScheduleName(event.target.value)}
            style={{ width: 'auto', flex: '1 1 180px' }}
          />
          <select
            className="aos-input"
            value={newScheduleJobType}
            onChange={(event) => setNewScheduleJobType(event.target.value)}
            style={{ width: 'auto' }}
          >
            <option value="repository_scan">repository_scan</option>
            <option value="project_digest">project_digest</option>
          </select>
          <input
            className="aos-input"
            type="number"
            value={newScheduleInterval}
            placeholder="Interval seconds"
            onChange={(event) => setNewScheduleInterval(event.target.value)}
            style={{ width: 140 }}
          />
          <button type="submit" className="aos-btn aos-btn-sm" disabled={creatingSchedule}>
            {creatingSchedule ? 'Creating...' : 'Create schedule'}
          </button>
        </form>
      </div>

      <div className="aos-hud glass aos-card">
        <span className="aos-eyebrow">Enqueue now</span>
        <div className="aos-form-row" style={{ marginTop: 0 }}>
          <button
            type="button"
            className="aos-btn aos-btn-sm"
            disabled={schedulingBusy}
            onClick={() => void handleEnqueueDigest()}
          >
            Enqueue digest job
          </button>
          <select
            className="aos-input"
            value={scanJobRepoId}
            onChange={(event) => setScanJobRepoId(event.target.value)}
            style={{ width: 'auto' }}
          >
            <option value="">Select repository</option>
            {repositories.map((repository) => (
              <option key={repository.id} value={repository.id}>
                {repository.name}
              </option>
            ))}
          </select>
          <button
            type="button"
            className="aos-btn aos-btn-sm"
            disabled={schedulingBusy || !scanJobRepoId}
            onClick={() => void handleEnqueueScan()}
          >
            Enqueue scan job
          </button>
        </div>
      </div>

      <div className="aos-hud glass aos-card">
        <span className="aos-eyebrow">Job history</span>
        <div className="aos-form-row" style={{ marginTop: 0 }}>
          <button
            type="button"
            className="aos-btn-ghost aos-btn-sm"
            disabled={schedulingBusy}
            onClick={() => selectedProjectId && void loadJobs(selectedProjectId)}
          >
            Refresh jobs
          </button>
        </div>
        {jobs.length === 0 ? (
          <p className="aos-muted" style={{ margin: '12px 0 0' }}>No jobs yet.</p>
        ) : (
          <ul className="aos-rows" style={{ marginTop: 12 }}>
            {jobs.map((job) => (
              <li key={job.id}>
                {job.job_type} — {job.status} — {new Date(job.queued_at).toLocaleString()} —
                attempts {job.attempts}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
