import React, { useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { Clock, Eye, Save } from 'lucide-react';
import { useAuthStore } from '../../../store/authStore';
import { isSuperAdmin } from '../../../lib/rbac';
import {
  getTimesheetPolicy,
  updateTimesheetPolicy,
} from '../../../services/timesheetAdminService';
import type { TimesheetPolicy } from '../../../services/timesheetAdminService';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '../../../components/ui/Card';
import { Button } from '../../../components/ui/Button';
import { Skeleton } from '../../../components/ui/Skeleton';

interface FormErrors {
  standard_hours_per_day?: string;
  standard_hours_per_week?: string;
  max_hours_per_day?: string;
  submission_deadline_days?: string;
  allow_past_entry_days?: string;
}

export const TimesheetPolicyForm: React.FC = () => {
  const { user } = useAuthStore();
  const canEdit = isSuperAdmin(user);

  const [policy, setPolicy] = useState<TimesheetPolicy | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [saving, setSaving] = useState<boolean>(false);
  const [errors, setErrors] = useState<FormErrors>({});

  const fetchPolicy = async () => {
    try {
      setLoading(true);
      const data = await getTimesheetPolicy();
      setPolicy(data);
    } catch (err: any) {
      toast.error(err.message || 'Failed to load timesheet policy');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPolicy();
  }, []);

  const validate = (): boolean => {
    if (!policy) return false;
    const newErrors: FormErrors = {};

    if (policy.standard_hours_per_day < 0.5 || policy.standard_hours_per_day > 24) {
      newErrors.standard_hours_per_day = 'Must be between 0.5 and 24 hours';
    }
    if (policy.standard_hours_per_week < 1 || policy.standard_hours_per_week > 168) {
      newErrors.standard_hours_per_week = 'Must be between 1 and 168 hours';
    }
    if (policy.max_hours_per_day < 1 || policy.max_hours_per_day > 24) {
      newErrors.max_hours_per_day = 'Must be between 1 and 24 hours';
    }
    if (policy.submission_deadline_days < 0 || policy.submission_deadline_days > 30) {
      newErrors.submission_deadline_days = 'Must be between 0 and 30 days';
    }
    if (policy.allow_past_entry_days < 0 || policy.allow_past_entry_days > 365) {
      newErrors.allow_past_entry_days = 'Must be between 0 and 365 days';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canEdit || !policy) return;

    if (!validate()) {
      toast.error('Please fix validation errors before submitting');
      return;
    }

    try {
      setSaving(true);
      const updated = await updateTimesheetPolicy({
        week_start_day: policy.week_start_day,
        standard_hours_per_day: Number(policy.standard_hours_per_day),
        standard_hours_per_week: Number(policy.standard_hours_per_week),
        max_hours_per_day: Number(policy.max_hours_per_day),
        overtime_policy: policy.overtime_policy,
        submission_deadline_days: Number(policy.submission_deadline_days),
        allow_future_entry: policy.allow_future_entry,
        allow_past_entry_days: Number(policy.allow_past_entry_days),
        require_task_link: policy.require_task_link,
        allow_member_recall: policy.allow_member_recall,
      });
      setPolicy(updated);
      toast.success('Timesheet policy updated successfully');
    } catch (err: any) {
      toast.error(err.message || 'Failed to update timesheet policy');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <Card variant="glass" className="w-full shadow-lg border-brand-border/60">
        <CardHeader>
          <Skeleton variant="text" width="60%" height={24} />
          <Skeleton variant="text" width="40%" height={16} />
        </CardHeader>
        <CardContent className="space-y-6">
          {[1, 2, 3, 4, 5].map((i) => (
            <Skeleton key={i} variant="rectangular" height={48} className="w-full rounded-xl" />
          ))}
        </CardContent>
      </Card>
    );
  }

  if (!policy) {
    return (
      <Card variant="glass" className="w-full text-center py-8">
        <p className="text-brand-text-muted">Unable to load timesheet policy.</p>
        <Button variant="outline" size="sm" className="mt-4" onClick={fetchPolicy}>
          Retry
        </Button>
      </Card>
    );
  }

  return (
    <Card variant="glass" className="w-full shadow-xl border-brand-border/70 backdrop-blur-xl">
      <CardHeader className="flex flex-row items-center justify-between pb-4 border-b border-brand-border/40">
        <div>
          <CardTitle className="text-lg font-semibold text-brand-text flex items-center gap-2">
            <Clock size={20} className="text-brand-primary" />
            Timesheet Policy Settings
          </CardTitle>
          <CardDescription className="text-xs text-brand-text-muted mt-1">
            Configure organization-wide rules for hours, deadlines, and overtime tracking.
          </CardDescription>
        </div>
        {!canEdit && (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <Eye size={13} />
            View Only
          </span>
        )}
      </CardHeader>

      <form onSubmit={handleSubmit}>
        <CardContent className="space-y-6 pt-6">
          {/* Week Start Day */}
          <div>
            <label className="block text-xs font-medium text-brand-text-muted mb-1.5">
              Week Start Day
            </label>
            <select
              disabled={!canEdit}
              value={policy.week_start_day}
              onChange={(e) =>
                setPolicy({
                  ...policy,
                  week_start_day: e.target.value as TimesheetPolicy['week_start_day'],
                })
              }
              className="w-full bg-brand-surface-low border border-brand-border rounded-xl px-3.5 py-2 text-sm text-brand-text focus:ring-2 focus:ring-brand-primary/50 focus:border-brand-primary outline-none transition disabled:opacity-60 disabled:cursor-not-allowed"
            >
              <option value="monday">Monday</option>
              <option value="tuesday">Tuesday</option>
              <option value="wednesday">Wednesday</option>
              <option value="thursday">Thursday</option>
              <option value="friday">Friday</option>
              <option value="saturday">Saturday</option>
              <option value="sunday">Sunday</option>
            </select>
          </div>

          {/* Standard Hours/Day & Standard Hours/Week */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-brand-text-muted mb-1.5">
                Standard Hours / Day
              </label>
              <input
                type="number"
                step="0.5"
                min="0.5"
                max="24"
                disabled={!canEdit}
                value={policy.standard_hours_per_day}
                onChange={(e) =>
                  setPolicy({
                    ...policy,
                    standard_hours_per_day: parseFloat(e.target.value) || 0,
                  })
                }
                className="w-full bg-brand-surface-low border border-brand-border rounded-xl px-3.5 py-2 text-sm text-brand-text focus:ring-2 focus:ring-brand-primary/50 focus:border-brand-primary outline-none transition disabled:opacity-60 disabled:cursor-not-allowed"
              />
              {errors.standard_hours_per_day && (
                <p className="text-xs text-red-400 mt-1">{errors.standard_hours_per_day}</p>
              )}
            </div>

            <div>
              <label className="block text-xs font-medium text-brand-text-muted mb-1.5">
                Standard Hours / Week
              </label>
              <input
                type="number"
                min="1"
                max="168"
                disabled={!canEdit}
                value={policy.standard_hours_per_week}
                onChange={(e) =>
                  setPolicy({
                    ...policy,
                    standard_hours_per_week: parseFloat(e.target.value) || 0,
                  })
                }
                className="w-full bg-brand-surface-low border border-brand-border rounded-xl px-3.5 py-2 text-sm text-brand-text focus:ring-2 focus:ring-brand-primary/50 focus:border-brand-primary outline-none transition disabled:opacity-60 disabled:cursor-not-allowed"
              />
              {errors.standard_hours_per_week && (
                <p className="text-xs text-red-400 mt-1">{errors.standard_hours_per_week}</p>
              )}
            </div>
          </div>

          {/* Max Hours/Day & Submission Deadline */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-brand-text-muted mb-1.5">
                Max Hours / Day
              </label>
              <input
                type="number"
                min="1"
                max="24"
                disabled={!canEdit}
                value={policy.max_hours_per_day}
                onChange={(e) =>
                  setPolicy({
                    ...policy,
                    max_hours_per_day: parseFloat(e.target.value) || 0,
                  })
                }
                className="w-full bg-brand-surface-low border border-brand-border rounded-xl px-3.5 py-2 text-sm text-brand-text focus:ring-2 focus:ring-brand-primary/50 focus:border-brand-primary outline-none transition disabled:opacity-60 disabled:cursor-not-allowed"
              />
              {errors.max_hours_per_day && (
                <p className="text-xs text-red-400 mt-1">{errors.max_hours_per_day}</p>
              )}
            </div>

            <div>
              <label className="block text-xs font-medium text-brand-text-muted mb-1.5">
                Days after week end to submit
              </label>
              <input
                type="number"
                min="0"
                max="30"
                disabled={!canEdit}
                value={policy.submission_deadline_days}
                onChange={(e) =>
                  setPolicy({
                    ...policy,
                    submission_deadline_days: parseInt(e.target.value, 10) || 0,
                  })
                }
                className="w-full bg-brand-surface-low border border-brand-border rounded-xl px-3.5 py-2 text-sm text-brand-text focus:ring-2 focus:ring-brand-primary/50 focus:border-brand-primary outline-none transition disabled:opacity-60 disabled:cursor-not-allowed"
              />
              {errors.submission_deadline_days && (
                <p className="text-xs text-red-400 mt-1">{errors.submission_deadline_days}</p>
              )}
            </div>
          </div>

          {/* Overtime Policy Radio Group */}
          <div>
            <label className="block text-xs font-medium text-brand-text-muted mb-2">
              Overtime Policy
            </label>
            <div className="space-y-2">
              {[
                { value: 'none', label: 'No Overtime Tracking', desc: 'Ignore overtime thresholds' },
                { value: 'flag_only', label: 'Flag as Overtime', desc: 'Highlight excess hours without blocking submission' },
                { value: 'block_submission', label: 'Block Submission', desc: 'Prevent submitting timesheets exceeding daily/weekly limits' },
              ].map((opt) => (
                <label
                  key={opt.value}
                  className={`flex items-start gap-3 p-3 rounded-xl border transition-all cursor-pointer ${
                    policy.overtime_policy === opt.value
                      ? 'bg-brand-primary/10 border-brand-primary/50 text-brand-text'
                      : 'bg-brand-surface-low border-brand-border/60 text-brand-text-muted hover:border-brand-border'
                  } ${!canEdit ? 'cursor-not-allowed opacity-75' : ''}`}
                >
                  <input
                    type="radio"
                    name="overtime_policy"
                    disabled={!canEdit}
                    checked={policy.overtime_policy === opt.value}
                    onChange={() =>
                      setPolicy({
                        ...policy,
                        overtime_policy: opt.value as TimesheetPolicy['overtime_policy'],
                      })
                    }
                    className="mt-0.5 text-brand-primary focus:ring-brand-primary accent-brand-primary"
                  />
                  <div>
                    <div className="text-sm font-semibold text-brand-text">{opt.label}</div>
                    <div className="text-xs text-brand-text-muted">{opt.desc}</div>
                  </div>
                </label>
              ))}
            </div>
          </div>

          {/* Allow Past Entry (days back) */}
          <div>
            <label className="block text-xs font-medium text-brand-text-muted mb-1.5">
              Allow Past Entry (days back)
            </label>
            <input
              type="number"
              min="0"
              max="365"
              disabled={!canEdit}
              value={policy.allow_past_entry_days}
              onChange={(e) =>
                setPolicy({
                  ...policy,
                  allow_past_entry_days: parseInt(e.target.value, 10) || 0,
                })
              }
              className="w-full bg-brand-surface-low border border-brand-border rounded-xl px-3.5 py-2 text-sm text-brand-text focus:ring-2 focus:ring-brand-primary/50 focus:border-brand-primary outline-none transition disabled:opacity-60 disabled:cursor-not-allowed"
            />
            {errors.allow_past_entry_days && (
              <p className="text-xs text-red-400 mt-1">{errors.allow_past_entry_days}</p>
            )}
          </div>

          {/* Toggle Switches */}
          <div className="space-y-4 pt-2 border-t border-brand-border/40">
            {/* Allow Future Date Entries */}
            <div className="flex items-center justify-between">
              <div>
                <span className="text-sm font-medium text-brand-text">Allow Future Date Entries</span>
                <p className="text-xs text-brand-text-muted">Members can log hours for upcoming dates</p>
              </div>
              <button
                type="button"
                disabled={!canEdit}
                onClick={() => setPolicy({ ...policy, allow_future_entry: !policy.allow_future_entry })}
                className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                  policy.allow_future_entry ? 'bg-brand-primary' : 'bg-brand-surface-container'
                } ${!canEdit ? 'cursor-not-allowed opacity-60' : ''}`}
              >
                <span
                  className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow-lg ring-0 transition duration-200 ease-in-out ${
                    policy.allow_future_entry ? 'translate-x-5' : 'translate-x-0'
                  }`}
                />
              </button>
            </div>

            {/* Require Task Link */}
            <div className="flex items-center justify-between">
              <div>
                <span className="text-sm font-medium text-brand-text">Require Task Link</span>
                <p className="text-xs text-brand-text-muted">Every time entry must be linked to a Kanban task</p>
              </div>
              <button
                type="button"
                disabled={!canEdit}
                onClick={() => setPolicy({ ...policy, require_task_link: !policy.require_task_link })}
                className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                  policy.require_task_link ? 'bg-brand-primary' : 'bg-brand-surface-container'
                } ${!canEdit ? 'cursor-not-allowed opacity-60' : ''}`}
              >
                <span
                  className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow-lg ring-0 transition duration-200 ease-in-out ${
                    policy.require_task_link ? 'translate-x-5' : 'translate-x-0'
                  }`}
                />
              </button>
            </div>

            {/* Allow Member Recall */}
            <div className="flex items-center justify-between">
              <div>
                <span className="text-sm font-medium text-brand-text">Allow Member Recall</span>
                <p className="text-xs text-brand-text-muted">
                  Members can recall a submitted timesheet before it is approved
                </p>
              </div>
              <button
                type="button"
                disabled={!canEdit}
                onClick={() => setPolicy({ ...policy, allow_member_recall: !policy.allow_member_recall })}
                className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                  policy.allow_member_recall ? 'bg-brand-primary' : 'bg-brand-surface-container'
                } ${!canEdit ? 'cursor-not-allowed opacity-60' : ''}`}
              >
                <span
                  className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow-lg ring-0 transition duration-200 ease-in-out ${
                    policy.allow_member_recall ? 'translate-x-5' : 'translate-x-0'
                  }`}
                />
              </button>
            </div>
          </div>
        </CardContent>

        {canEdit && (
          <CardFooter className="flex justify-end pt-4 border-t border-brand-border/40">
            <Button variant="primary" type="submit" disabled={saving} className="flex items-center gap-2">
              <Save size={16} />
              {saving ? 'Saving Changes...' : 'Save Policy'}
            </Button>
          </CardFooter>
        )}
      </form>
    </Card>
  );
};

export default TimesheetPolicyForm;
