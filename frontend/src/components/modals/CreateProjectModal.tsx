import React, { useState, useEffect, useRef } from "react";
import { Loader2 } from "lucide-react";
import { useBoardStore } from "../../store/boardStore";
import { useUiStore } from "../../store/uiStore";
import Modal from "../common/Modal/Modal";
import { ProjectCard } from "../common/ProjectCard";
import { ProjectIconPicker } from "../projects/ProjectIconPicker";
import { ProjectColorPicker } from "../projects/ProjectColorPicker";
import { ProjectCoverPicker } from "../projects/ProjectCoverPicker";
import { ProjectLeadSelector } from "../projects/ProjectLeadSelector";

const CreateProjectModal: React.FC = () => {
  const { isCreateProjectModalOpen: isOpen, closeCreateProjectModal: onClose } = useUiStore();
  const { createNewBoard, isSubmitting } = useBoardStore();

  const [formData, setFormData] = useState({
    name: "",
    project_key: "",
    description: "",
    icon: "",
    color: "",
    cover_gradient: "",
    default_assignee_id: null as number | null,
    project_lead_id: null as number | null,
  });

  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen) {
      setFormData({
        name: "",
        project_key: "",
        description: "",
        icon: "",
        color: "",
        cover_gradient: "",
        default_assignee_id: null,
        project_lead_id: null,
      });
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [isOpen]);

  // Auto-generate project key if not touched by user (simple heuristic: if key is empty or matches previous auto-gen)
  // Actually, let's keep it simple: if the user types a name and key is empty, auto-fill it.
  const handleNameChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newName = e.target.value;
    setFormData(prev => {
      // Very basic auto-gen logic for preview purposes
      let newKey = prev.project_key;
      if (!prev.project_key || prev.project_key === prev.name.replace(/[^A-Z0-9]/gi, '').toUpperCase().substring(0, 5)) {
        newKey = newName.replace(/[^A-Z0-9]/gi, '').toUpperCase().substring(0, 5);
      }
      return { ...prev, name: newName, project_key: newKey };
    });
  };

  const handleKeyChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value.replace(/[^A-Za-z0-9]/g, '').toUpperCase().substring(0, 5);
    setFormData(prev => ({ ...prev, project_key: val }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name.trim() || !formData.project_key.trim()) return;

    try {
      await createNewBoard(formData);
      onClose();
    } catch (err) {
      // Error is handled by store
    }
  };

  const isInvalid = !formData.name.trim() || !formData.project_key.trim() || formData.project_key.length < 2;

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Create New Project" width="max-w-5xl">
      <div className="flex flex-col lg:flex-row h-[70vh] lg:h-[600px] overflow-hidden -mx-6 -my-4">
        
        {/* Left Column: Form */}
        <div className="flex-1 overflow-y-auto p-6 border-r border-brand-border">
          <form id="create-project-form" onSubmit={handleSubmit} className="space-y-6">
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-1">
                <label className="block text-sm font-medium text-brand-text">
                  Project Name <span className="text-brand-error">*</span>
                </label>
                <input
                  ref={inputRef}
                  type="text"
                  value={formData.name}
                  onChange={handleNameChange}
                  placeholder="e.g. Website Redesign"
                  className="w-full px-3 py-2 bg-brand-surface-low rounded-md text-sm border border-brand-border focus:border-brand-primary outline-none transition-colors"
                />
              </div>
              
              <div className="space-y-1">
                <label className="block text-sm font-medium text-brand-text">
                  Project Key <span className="text-brand-error">*</span>
                </label>
                <input
                  type="text"
                  value={formData.project_key}
                  onChange={handleKeyChange}
                  placeholder="e.g. WEB"
                  className="w-full px-3 py-2 bg-brand-surface-low rounded-md text-sm border border-brand-border focus:border-brand-primary outline-none transition-colors font-mono"
                />
                <p className="text-[11px] text-brand-text-muted">2-5 uppercase letters/numbers.</p>
              </div>
            </div>

            <div className="space-y-1">
              <label className="block text-sm font-medium text-brand-text">Description</label>
              <textarea
                value={formData.description}
                onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                placeholder="What is this project about?"
                rows={2}
                className="w-full px-3 py-2 bg-brand-surface-low rounded-md text-sm border border-brand-border focus:border-brand-primary outline-none transition-colors resize-none"
              />
            </div>

            <div className="space-y-4 pt-4 border-t border-brand-border">
              <h4 className="text-sm font-semibold text-brand-text">Identity & Branding</h4>
              
              <div>
                <label className="text-sm font-medium text-brand-text block mb-2">Project Icon</label>
                <ProjectIconPicker 
                  value={formData.icon} 
                  onChange={(icon) => setFormData(prev => ({ ...prev, icon }))} 
                />
              </div>
              
              <div>
                <label className="text-sm font-medium text-brand-text block mb-2">Theme Color</label>
                <ProjectColorPicker 
                  value={formData.color} 
                  onChange={(color) => setFormData(prev => ({ ...prev, color }))} 
                />
              </div>

              <div>
                <label className="text-sm font-medium text-brand-text block mb-2">Cover Gradient</label>
                <ProjectCoverPicker 
                  value={formData.cover_gradient} 
                  onChange={(gradient) => setFormData(prev => ({ ...prev, cover_gradient: gradient }))} 
                />
              </div>
            </div>

            <div className="space-y-4 pt-4 border-t border-brand-border pb-4">
              <h4 className="text-sm font-semibold text-brand-text">Assignments</h4>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium text-brand-text block mb-1">Project Lead</label>
                  <ProjectLeadSelector 
                    value={formData.project_lead_id} 
                    onChange={(id) => setFormData(prev => ({ ...prev, project_lead_id: id }))} 
                  />
                </div>
                <div>
                  <label className="text-sm font-medium text-brand-text block mb-1">Default Assignee</label>
                  <ProjectLeadSelector 
                    value={formData.default_assignee_id} 
                    onChange={(id) => setFormData(prev => ({ ...prev, default_assignee_id: id }))} 
                  />
                </div>
              </div>
            </div>

          </form>
        </div>

        {/* Right Column: Live Preview */}
        <div className="w-full lg:w-[400px] bg-brand-surface-low p-6 flex flex-col">
          <h4 className="text-sm font-semibold text-brand-text mb-4">Live Preview</h4>
          <div className="flex-1 flex flex-col justify-center max-w-sm mx-auto w-full">
            <ProjectCard 
              board={{
                name: formData.name || 'Unnamed Project',
                project_key: formData.project_key || 'KEY',
                description: formData.description,
                icon: formData.icon,
                color: formData.color,
                cover_gradient: formData.cover_gradient,
                task_count: 0
              }}
              isLink={false}
              className="shadow-xl"
            />
          </div>
          
          <div className="mt-auto pt-6 flex justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="px-6 py-2 rounded-md text-sm font-medium bg-brand-surface border border-brand-border hover:bg-brand-surface-hover transition-colors text-brand-text"
            >
              Cancel
            </button>
            <button
              type="submit"
              form="create-project-form"
              disabled={isSubmitting || isInvalid}
              className="bg-brand-primary hover:bg-brand-primary-hover text-white px-6 py-2 rounded-md text-sm font-medium flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
            >
              {isSubmitting && <Loader2 size={16} className="animate-spin" />}
              {isSubmitting ? "Creating..." : "Create Project"}
            </button>
          </div>
        </div>

      </div>
    </Modal>
  );
};

export default CreateProjectModal;
