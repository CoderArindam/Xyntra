import React from 'react';
import { Link } from 'react-router-dom';
import {
  Zap,
  Video,
  Play,
  Sparkles,
  Plus,
  Users,
  Building2,
  ChevronRight,
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription } from '../../../components/ui/Card';

interface QuickActionsWidgetProps {
  userRole: string;
  pendingPropsCount: number;
  onOpenJoinModal: () => void;
  onOpenProposalsModal: () => void;
  onOpenCreateProjectModal: () => void;
}

export const QuickActionsWidget: React.FC<QuickActionsWidgetProps> = ({
  userRole,
  pendingPropsCount,
  onOpenJoinModal,
  onOpenProposalsModal,
  onOpenCreateProjectModal,
}) => {
  const isSuperAdmin = userRole.toUpperCase() === 'SUPER_ADMIN';

  return (
    <Card variant="default" padding="md" className="space-y-4">
      <CardHeader className="mb-0">
        <CardTitle>
          <Zap className="w-4 h-4 text-amber-400" /> Manager Quick Actions
        </CardTitle>
        <CardDescription>Shortcuts to key workflows and administration</CardDescription>
      </CardHeader>

      <div className="space-y-2.5">
        {/* Action 1: Start / Join Meeting */}
        <button
          onClick={onOpenJoinModal}
          className="w-full py-2.5 px-3.5 text-xs font-semibold bg-brand-primary hover:bg-brand-primary-hover text-white rounded-xl flex items-center justify-between transition-colors cursor-pointer shadow-xs"
        >
          <span className="flex items-center gap-2">
            <Video className="w-4 h-4" /> Start / Join Meeting
          </span>
          <Play className="w-3.5 h-3.5 fill-current" />
        </button>

        {/* Action 2: Review AI Task Proposals */}
        <button
          onClick={onOpenProposalsModal}
          className="w-full py-2.5 px-3.5 text-xs font-semibold bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/30 text-emerald-400 rounded-xl flex items-center justify-between transition-colors cursor-pointer"
        >
          <span className="flex items-center gap-2">
            <Sparkles className="w-4 h-4" /> Review AI Task Proposals
          </span>
          <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-emerald-500/20 border border-emerald-500/30">
            {pendingPropsCount}
          </span>
        </button>

        {/* Action 3: Create New Project */}
        <button
          onClick={onOpenCreateProjectModal}
          className="w-full py-2.5 px-3.5 text-xs font-semibold bg-brand-surface-low border border-brand-border hover:bg-brand-surface-container text-brand-text rounded-xl flex items-center justify-between transition-colors cursor-pointer"
        >
          <span className="flex items-center gap-2">
            <Plus className="w-4 h-4 text-brand-primary" /> Create New Project
          </span>
          <ChevronRight className="w-3.5 h-3.5 text-brand-text-muted" />
        </button>

        {/* Action 4: Superadmin Shortcut to User & Role Management */}
        {isSuperAdmin && (
          <Link
            to="/admin/users"
            className="w-full py-2.5 px-3.5 text-xs font-semibold bg-indigo-500/10 hover:bg-indigo-500/20 border border-indigo-500/30 text-indigo-400 rounded-xl flex items-center justify-between transition-colors cursor-pointer"
          >
            <span className="flex items-center gap-2">
              <Users className="w-4 h-4" /> User & Role Management
            </span>
            <ChevronRight className="w-3.5 h-3.5 text-indigo-400" />
          </Link>
        )}

        {/* Action 5: Organization Settings */}
        <Link
          to="/settings/organization"
          className="w-full py-2.5 px-3.5 text-xs font-semibold bg-brand-surface-low border border-brand-border hover:bg-brand-surface-container text-brand-text rounded-xl flex items-center justify-between transition-colors cursor-pointer"
        >
          <span className="flex items-center gap-2">
            <Building2 className="w-4 h-4 text-brand-text-muted" /> Workspace Settings
          </span>
          <ChevronRight className="w-3.5 h-3.5 text-brand-text-muted" />
        </Link>
      </div>
    </Card>
  );
};
