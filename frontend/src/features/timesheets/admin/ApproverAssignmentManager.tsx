import React, { useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { Users, ShieldCheck, UserCheck, UserX, CheckCircle2, Loader2 } from 'lucide-react';
import { useAuthStore } from '../../../store/authStore';
import { isSuperAdmin } from '../../../lib/rbac';
import {
  getApproverAssignments,
  getAllManagersWithApproverStatus,
  assignApprover,
  removeApprover,
  type ApproverAssignment,
  type EligibleApprover,
} from '../../../services/timesheetAdminService';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../../../components/ui/Card';
import { Button } from '../../../components/ui/Button';
import { Skeleton } from '../../../components/ui/Skeleton';

export const ApproverAssignmentManager: React.FC = () => {
  const { user } = useAuthStore();
  const canEdit = isSuperAdmin(user);

  const [assignments, setAssignments] = useState<ApproverAssignment[]>([]);
  const [managers, setManagers] = useState<EligibleApprover[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [actionUserId, setActionUserId] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      const assignmentsRes = await getApproverAssignments();
      setAssignments(assignmentsRes);

      if (canEdit) {
        const managersRes = await getAllManagersWithApproverStatus();
        setManagers(managersRes);
      }
    } catch (err: any) {
      toast.error(err.message || 'Failed to load approver configuration');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [canEdit]);

  const handleToggleApprover = async (manager: EligibleApprover) => {
    if (!canEdit) return;

    setActionUserId(manager.user_id);
    try {
      if (manager.is_approver) {
        // Remove approver status
        const assignment = assignments.find(
          (a) => a.approver_user_id.toLowerCase() === manager.user_id.toLowerCase()
        );
        if (assignment) {
          await removeApprover(assignment.id);
          toast.success(`Removed ${manager.display_name} from organization approvers`);
        }
      } else {
        // Designate as approver
        await assignApprover({ approver_user_id: manager.user_id });
        toast.success(`Designated ${manager.display_name} as an organization approver`);
      }
      await loadData();
    } catch (err: any) {
      toast.error(err.message || 'Failed to update approver assignment');
    } finally {
      setActionUserId(null);
    }
  };

  if (loading) {
    return (
      <Card variant="glass" className="w-full shadow-lg border-brand-border/60">
        <CardHeader>
          <Skeleton variant="text" width="50%" height={24} />
          <Skeleton variant="text" width="70%" height={16} />
        </CardHeader>
        <CardContent className="space-y-4">
          <Skeleton variant="rectangular" height={160} className="w-full" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card variant="glass" className="w-full shadow-xl border-brand-border/70 backdrop-blur-xl">
      <CardHeader className="pb-4 border-b border-brand-border/40">
        <CardTitle className="text-lg font-semibold text-brand-text flex items-center gap-2">
          <ShieldCheck size={20} className="text-brand-primary" />
          Global Organization Approvers
        </CardTitle>
        <CardDescription className="text-xs text-brand-text-muted mt-1">
          Superadmins can designate Managers as valid approvers across the organization. Designated approvers can review and approve any timesheet assigned to them upon submission.
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-6 pt-6">
        {/* Managers Approver Configuration List */}
        <div className="overflow-x-auto rounded-xl border border-brand-border/60">
          <table className="w-full text-left text-xs text-brand-text">
            <thead className="bg-brand-surface-low border-b border-brand-border/60 uppercase tracking-wider text-[11px] text-brand-text-muted">
              <tr>
                <th className="px-4 py-3 font-semibold">Manager / User</th>
                <th className="px-4 py-3 font-semibold">Role</th>
                <th className="px-4 py-3 font-semibold">Approver Permission</th>
                {canEdit && <th className="px-4 py-3 font-semibold text-right">Actions</th>}
              </tr>
            </thead>

            <tbody className="divide-y divide-brand-border/40">
              {managers.length === 0 ? (
                <tr>
                  <td colSpan={canEdit ? 4 : 3} className="px-4 py-6 text-center text-xs text-brand-text-muted italic">
                    No managers found in the organization.
                  </td>
                </tr>
              ) : (
                managers.map((m) => {
                  const isPending = actionUserId === m.user_id;
                  return (
                    <tr key={m.user_id} className="hover:bg-brand-surface/50 transition-colors">
                      <td className="px-4 py-3 font-medium">
                        <div className="flex items-center gap-2">
                          <Users size={16} className="text-brand-text-muted shrink-0" />
                          <div>
                            <span className="font-semibold text-brand-text block">{m.display_name}</span>
                            <span className="text-[11px] text-brand-text-muted">{m.email}</span>
                          </div>
                        </div>
                      </td>

                      <td className="px-4 py-3 text-brand-text-muted">
                        <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-brand-surface border border-brand-border uppercase">
                          {m.role}
                        </span>
                      </td>

                      <td className="px-4 py-3">
                        {m.is_approver ? (
                          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                            <CheckCircle2 size={13} />
                            Active Approver
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-zinc-500/10 text-brand-text-muted/70 border border-zinc-500/20">
                            Standard Role Only
                          </span>
                        )}
                      </td>

                      {canEdit && (
                        <td className="px-4 py-3 text-right">
                          <Button
                            variant={m.is_approver ? 'danger' : 'primary'}
                            size="sm"
                            disabled={isPending}
                            onClick={() => handleToggleApprover(m)}
                            className="flex items-center gap-1.5 ml-auto"
                          >
                            {isPending ? (
                              <Loader2 size={13} className="animate-spin" />
                            ) : m.is_approver ? (
                              <>
                                <UserX size={13} />
                                Revoke Approver
                              </>
                            ) : (
                              <>
                                <UserCheck size={13} />
                                Designate as Approver
                              </>
                            )}
                          </Button>
                        </td>
                      )}
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
};

export default ApproverAssignmentManager;
