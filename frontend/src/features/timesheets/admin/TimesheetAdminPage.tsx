import React, { useState } from 'react';
import { Navigate } from 'react-router-dom';
import { Settings, Sliders, Users, BarChart3, Clock, Eye } from 'lucide-react';
import { useAuthStore } from '../../../store/authStore';
import { isManagerOrAdmin, isSuperAdmin } from '../../../lib/rbac';
import TimesheetPolicyForm from './TimesheetPolicyForm';
import ApproverAssignmentManager from './ApproverAssignmentManager';
import { Card, CardTitle, CardDescription, CardContent } from '../../../components/ui/Card';

type TabType = 'all' | 'policy' | 'approvers' | 'reports';

export const TimesheetAdminPage: React.FC = () => {
  const { user } = useAuthStore();
  const [activeTab, setActiveTab] = useState<TabType>('all');

  // Route guard: Only Superadmin can access Timesheet Policy
  if (!user || !isSuperAdmin(user)) {
    return <Navigate to="/dashboard" replace />;
  }

  const superAdmin = isSuperAdmin(user);

  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-16">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-brand-border/60 pb-6">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-2xl bg-brand-primary/10 text-brand-primary border border-brand-primary/20">
              <Settings size={24} />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-brand-text flex items-center gap-3">
                Timesheet Configuration
                {!superAdmin && (
                  <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
                    <Eye size={12} /> Read-Only
                  </span>
                )}
              </h1>
              <p className="text-sm text-brand-text-muted mt-0.5">
                Manage organization-wide timesheet policy rules and project approval chains.
              </p>
            </div>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex items-center bg-brand-surface-low border border-brand-border/60 p-1 rounded-xl">
          <button
            onClick={() => setActiveTab('all')}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'all'
                ? 'bg-brand-primary text-white shadow-xs'
                : 'text-brand-text-muted hover:text-brand-text'
            }`}
          >
            <Sliders size={14} />
            Overview
          </button>
          <button
            onClick={() => setActiveTab('policy')}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'policy'
                ? 'bg-brand-primary text-white shadow-xs'
                : 'text-brand-text-muted hover:text-brand-text'
            }`}
          >
            <Clock size={14} />
            Policy
          </button>
          <button
            onClick={() => setActiveTab('approvers')}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'approvers'
                ? 'bg-brand-primary text-white shadow-xs'
                : 'text-brand-text-muted hover:text-brand-text'
            }`}
          >
            <Users size={14} />
            Approvers
          </button>
          <button
            onClick={() => setActiveTab('reports')}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'reports'
                ? 'bg-brand-primary text-white shadow-xs'
                : 'text-brand-text-muted hover:text-brand-text'
            }`}
          >
            <BarChart3 size={14} />
            Reports
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      {activeTab === 'reports' ? (
        <Card variant="glass" className="py-16 text-center shadow-lg border-brand-border/60">
          <CardContent className="space-y-3">
            <div className="mx-auto w-12 h-12 rounded-2xl bg-brand-primary/10 text-brand-primary border border-brand-primary/20 flex items-center justify-center">
              <BarChart3 size={24} />
            </div>
            <CardTitle className="text-xl font-bold text-brand-text">Timesheet Reports</CardTitle>
            <CardDescription className="text-sm text-brand-text-muted max-w-md mx-auto">
              Advanced analytics, audit logs, and compliance report exports are coming soon.
            </CardDescription>
          </CardContent>
        </Card>
      ) : activeTab === 'policy' ? (
        <div className="max-w-3xl mx-auto">
          <TimesheetPolicyForm />
        </div>
      ) : activeTab === 'approvers' ? (
        <div className="max-w-3xl mx-auto">
          <ApproverAssignmentManager />
        </div>
      ) : (
        /* Overview layout: Two-column on desktop, single column on mobile */
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-start">
          <TimesheetPolicyForm />
          <ApproverAssignmentManager />
        </div>
      )}
    </div>
  );
};

export default TimesheetAdminPage;
