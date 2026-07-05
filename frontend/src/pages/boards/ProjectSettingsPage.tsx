import React, { useState, useEffect } from "react";
import {
  Save,
  AlertTriangle,
  Archive,
  Trash2,
  ListTodo,
  CheckSquare,
  Clock,
  Users as UsersIcon,
  LayoutPanelLeft,
  Activity,
} from "lucide-react";
import { useProjectSettingsStore } from "../../store/projectSettingsStore";
import { ProjectIconPicker } from "../../components/projects/ProjectIconPicker";
import { ProjectColorPicker } from "../../components/projects/ProjectColorPicker";
import { ProjectCoverPicker } from "../../components/projects/ProjectCoverPicker";
import { ProjectStatisticsCard } from "../../components/projects/ProjectStatisticsCard";
import { ProjectLeadSelector } from "../../components/projects/ProjectLeadSelector";
import { ArchiveProjectDialog } from "../../components/projects/ArchiveProjectDialog";
import ConfirmDialog from "../../components/common/ConfirmDialog/ConfirmDialog";
import { useParams, useNavigate } from "react-router-dom";
import { useBoardStore } from "../../store/boardStore";

export const ProjectSettingsPage: React.FC = () => {
  const { boardId } = useParams<{ boardId: string }>();
  const navigate = useNavigate();
  const { currentSettings, updateSettings, isSaving } =
    useProjectSettingsStore();
  const { removeBoard } = useBoardStore();
  const [isArchiveDialogOpen, setIsArchiveDialogOpen] = useState(false);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const [formData, setFormData] = useState({
    name: "",
    description: "",
    icon: "",
    color: "",
    cover_gradient: "",
    default_assignee_id: null as number | null,
    project_lead_id: null as number | null,
  });

  useEffect(() => {
    if (currentSettings?.settings) {
      setFormData({
        name: currentSettings.settings.name || "",
        description: currentSettings.settings.description || "",
        icon: currentSettings.settings.icon || "",
        color: currentSettings.settings.color || "",
        cover_gradient: currentSettings.settings.cover_gradient || "",
        default_assignee_id:
          currentSettings.settings.default_assignee_id ?? null,
        project_lead_id: currentSettings.settings.project_lead_id ?? null,
      });
    }
  }, [currentSettings]);

  if (!currentSettings) return null;

  const hasChanges =
    formData.name !== (currentSettings.settings.name || "") ||
    formData.description !== (currentSettings.settings.description || "") ||
    formData.icon !== (currentSettings.settings.icon || "") ||
    formData.color !== (currentSettings.settings.color || "") ||
    formData.cover_gradient !==
      (currentSettings.settings.cover_gradient || "") ||
    formData.default_assignee_id !==
      (currentSettings.settings.default_assignee_id ?? null) ||
    formData.project_lead_id !==
      (currentSettings.settings.project_lead_id ?? null);

  const handleSave = async () => {
    if (!boardId) return;
    await updateSettings(parseInt(boardId, 10), formData);
  };

  const handleDiscard = () => {
    if (currentSettings?.settings) {
      setFormData({
        name: currentSettings.settings.name || "",
        description: currentSettings.settings.description || "",
        icon: currentSettings.settings.icon || "",
        color: currentSettings.settings.color || "",
        cover_gradient: currentSettings.settings.cover_gradient || "",
        default_assignee_id:
          currentSettings.settings.default_assignee_id ?? null,
        project_lead_id: currentSettings.settings.project_lead_id ?? null,
      });
    }
  };

  const handleDelete = async () => {
    if (!boardId) return;
    setIsDeleting(true);
    await removeBoard(parseInt(boardId, 10));
    setIsDeleting(false);
    setIsDeleteDialogOpen(false);
    navigate("/dashboard");
  };

  return (
    <div className="max-w-4xl space-y-8 animate-in fade-in duration-300 pb-20">
      {/* General Settings */}
      <section className="bg-brand-surface border border-brand-border rounded-xl shadow-sm overflow-hidden">
        <div className="px-6 py-5 border-b border-brand-border">
          <h3 className="text-lg font-semibold text-brand-text">
            General Details
          </h3>
          <p className="text-sm text-brand-text-muted mt-1">
            Manage project metadata and identity.
          </p>
        </div>
        <div className="p-6 space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-1">
              <label className="text-sm font-medium text-brand-text block">
                Project Name
              </label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) =>
                  setFormData((prev) => ({ ...prev, name: e.target.value }))
                }
                className="w-full px-3 py-2 bg-brand-bg border border-brand-border rounded-md text-sm text-brand-text outline-none focus:border-brand-primary focus:ring-1 focus:ring-brand-primary"
              />
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium text-brand-text block text-brand-text-muted">
                Project Key (Read-only)
              </label>
              <input
                type="text"
                value={currentSettings.settings.project_key}
                disabled
                className="w-full px-3 py-2 bg-brand-surface-low border border-brand-border rounded-md text-sm text-brand-text-muted cursor-not-allowed font-mono"
              />
            </div>

            <div className="md:col-span-2 space-y-1">
              <label className="text-sm font-medium text-brand-text block">
                Description
              </label>
              <textarea
                value={formData.description}
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    description: e.target.value,
                  }))
                }
                rows={3}
                className="w-full px-3 py-2 bg-brand-bg border border-brand-border rounded-md text-sm text-brand-text outline-none focus:border-brand-primary focus:ring-1 focus:ring-brand-primary resize-y"
              />
            </div>
          </div>
        </div>
      </section>

      {/* Identity & Branding */}
      <section className="bg-brand-surface border border-brand-border rounded-xl shadow-sm overflow-hidden">
        <div className="px-6 py-5 border-b border-brand-border">
          <h3 className="text-lg font-semibold text-brand-text">
            Identity & Branding
          </h3>
          <p className="text-sm text-brand-text-muted mt-1">
            Customize how this project looks across the workspace.
          </p>
        </div>
        <div className="p-6 space-y-8">
          <ProjectIconPicker
            value={formData.icon}
            onChange={(icon) => setFormData((prev) => ({ ...prev, icon }))}
          />

          <div>
            <label className="text-sm font-medium text-brand-text block mb-3">
              Project Color
            </label>
            <ProjectColorPicker
              value={formData.color}
              onChange={(color) => setFormData((prev) => ({ ...prev, color }))}
            />
          </div>

          <div>
            <label className="text-sm font-medium text-brand-text block mb-3">
              Cover Gradient
            </label>
            <ProjectCoverPicker
              value={formData.cover_gradient}
              onChange={(gradient) =>
                setFormData((prev) => ({ ...prev, cover_gradient: gradient }))
              }
            />
          </div>
        </div>
      </section>

      {/* Leadership & Assignments */}
      <section className="bg-brand-surface border border-brand-border rounded-xl shadow-sm overflow-hidden">
        <div className="px-6 py-5 border-b border-brand-border">
          <h3 className="text-lg font-semibold text-brand-text">
            Leadership & Assignments
          </h3>
          <p className="text-sm text-brand-text-muted mt-1">
            Configure project ownership and default behaviors.
          </p>
        </div>
        <div className="p-6 space-y-6">
          <div>
            <label className="text-sm font-medium text-brand-text block mb-1">
              Project Lead
            </label>
            <p className="text-xs text-brand-text-muted mb-3">
              Responsible for overall project health.
            </p>
            <ProjectLeadSelector
              value={formData.project_lead_id}
              onChange={(id) =>
                setFormData((prev) => ({ ...prev, project_lead_id: id }))
              }
            />
          </div>

          <div className="border-t border-brand-border pt-6">
            <label className="text-sm font-medium text-brand-text block mb-1">
              Default Assignee
            </label>
            <p className="text-xs text-brand-text-muted mb-3">
              New tasks will be assigned to this user automatically.
            </p>
            <ProjectLeadSelector
              value={formData.default_assignee_id}
              onChange={(id) =>
                setFormData((prev) => ({ ...prev, default_assignee_id: id }))
              }
            />
          </div>
        </div>
      </section>

      {/* Statistics */}
      <section>
        <h3 className="text-lg font-semibold text-brand-text mb-4">
          Project Statistics
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <ProjectStatisticsCard
            title="Total Tasks"
            value={currentSettings.statistics.total_tasks}
            icon={<ListTodo size={20} />}
          />
          <ProjectStatisticsCard
            title="Completed Tasks"
            value={currentSettings.statistics.completed_tasks}
            icon={<CheckSquare size={20} className="text-emerald-500" />}
          />
          <ProjectStatisticsCard
            title="Overdue Tasks"
            value={currentSettings.statistics.overdue_tasks}
            icon={<AlertTriangle size={20} className="text-red-500" />}
          />
          <ProjectStatisticsCard
            title="Members"
            value={currentSettings.statistics.members_count}
            icon={<UsersIcon size={20} />}
          />
          <ProjectStatisticsCard
            title="Columns"
            value={currentSettings.statistics.columns_count}
            icon={<LayoutPanelLeft size={20} />}
          />
          <ProjectStatisticsCard
            title="Last Activity"
            value={
              currentSettings.statistics.last_activity
                ? new Date(
                    currentSettings.statistics.last_activity,
                  ).toLocaleDateString()
                : "N/A"
            }
            icon={<Activity size={20} />}
          />
        </div>
      </section>

      {/* Danger Zone */}
      <section className="bg-brand-surface border border-red-200 dark:border-red-900/50 rounded-xl shadow-sm overflow-hidden mt-12">
        <div className="px-6 py-5 border-b border-red-200 dark:border-red-900/50">
          <h3 className="text-lg font-semibold text-red-600 dark:text-red-500">
            Danger Zone
          </h3>
        </div>
        <div className="p-6 space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h4 className="text-sm font-medium text-brand-text cursor-pointer">
                Archive Project
              </h4>
              <p className="text-sm text-brand-text-muted mt-1">
                Hide this project from normal navigation. Data remains intact.
              </p>
            </div>
            <button
              onClick={() => setIsArchiveDialogOpen(true)}
              className="px-4 py-2 border border-brand-border text-brand-text hover:bg-brand-surface-hover rounded-md text-sm font-medium transition-colors flex items-center gap-2 cursor-pointer"
            >
              <Archive size={16} />
              Archive
            </button>
          </div>

          <div className="flex items-center justify-between pt-6 border-t border-brand-border">
            <div>
              <h4 className="text-sm font-medium text-brand-text">
                Delete Project
              </h4>
              <p className="text-sm text-brand-text-muted mt-1">
                Permanently delete all tasks, comments, and attachments.
              </p>
            </div>
            <button
              onClick={() => setIsDeleteDialogOpen(true)}
              className="px-4 py-2 border border-red-200 text-red-600 hover:bg-red-50 dark:border-red-900/50 dark:text-red-500 dark:hover:bg-red-900/20 rounded-md text-sm font-medium transition-colors flex items-center gap-2 cursor-pointer"
            >
              <Trash2 size={16} />
              Delete Project
            </button>
          </div>
        </div>
      </section>

      {/* Sticky Save Bar */}
      {hasChanges && (
        <div className="fixed bottom-0 left-0 right-0 bg-brand-surface border-t border-brand-border shadow-lg p-4 z-40 transform transition-transform duration-300">
          <div className="max-w-4xl mx-auto flex items-center justify-between">
            <span className="text-sm font-medium text-brand-text">
              You have unsaved changes
            </span>
            <div className="flex gap-3">
              <button
                onClick={handleDiscard}
                className="px-4 py-2 text-sm font-medium text-brand-text bg-transparent border border-brand-border hover:bg-brand-surface-hover rounded-md transition-colors cursor-pointer"
              >
                Discard
              </button>
              <button
                onClick={handleSave}
                disabled={isSaving}
                className="px-6 py-2 text-sm font-medium text-white bg-brand-primary hover:bg-brand-primary/90 rounded-md transition-colors disabled:opacity-50 flex items-center gap-2 cursor-pointer"
              >
                <Save size={16} />
                {isSaving ? "Saving..." : "Save Changes"}
              </button>
            </div>
          </div>
        </div>
      )}

      {boardId && currentSettings.settings.name && (
        <ArchiveProjectDialog
          boardId={parseInt(boardId, 10)}
          projectName={currentSettings.settings.name}
          isOpen={isArchiveDialogOpen}
          onClose={() => setIsArchiveDialogOpen(false)}
        />
      )}

      <ConfirmDialog
        isOpen={isDeleteDialogOpen}
        onClose={() => setIsDeleteDialogOpen(false)}
        onConfirm={handleDelete}
        title="Delete Project"
        description="Are you sure you want to delete this project? All tasks, columns, and data will be permanently removed. This action cannot be undone."
        confirmText="Delete"
        isDestructive={true}
        isLoading={isDeleting}
      />
    </div>
  );
};
