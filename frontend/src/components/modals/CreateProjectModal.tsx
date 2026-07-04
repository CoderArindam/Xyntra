import React, { useState, useEffect, useRef } from "react";
import { Loader2 } from "lucide-react";
import { useBoardStore } from "../../store/boardStore";
import { useUiStore } from "../../store/uiStore";
import Modal from "../common/Modal/Modal";

const CreateProjectModal: React.FC = () => {
  const { isCreateProjectModalOpen: isOpen, closeCreateProjectModal: onClose } =
    useUiStore();
  const { createNewBoard, isSubmitting } = useBoardStore();

  const [projectName, setProjectName] = useState("");
  const [description, setDescription] = useState("");

  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen) {
      setProjectName("");
      setDescription("");
      // Focus input on open after a short delay for animation
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [isOpen]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmedName = projectName.trim();
    if (!trimmedName) return;

    await createNewBoard(trimmedName);
    onClose();
  };

  const isInvalid = !projectName.trim();

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Create New Project" width="max-w-lg">
      <form onSubmit={handleSubmit} className="space-y-6">
        <div>
          <label
            htmlFor="projectName"
            className="block text-sm font-medium text-brand-text mb-2"
          >
            Project Name <span className="text-brand-error">*</span>
          </label>
          <input
            ref={inputRef}
            id="projectName"
            type="text"
            value={projectName}
            onChange={(e) => setProjectName(e.target.value)}
            placeholder="e.g. Website Redesign"
            className="w-full px-4 py-3 bg-brand-surface-low rounded-lg text-sm border border-brand-border focus:border-brand-primary outline-none transition-colors"
          />
        </div>

        <div>
          <label
            htmlFor="description"
            className="block text-sm font-medium text-brand-text mb-2"
          >
            Description (optional)
          </label>
          <textarea
            id="description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="What is this project about?"
            rows={3}
            className="w-full px-4 py-3 bg-brand-surface-low rounded-lg text-sm border border-brand-border focus:border-brand-primary outline-none transition-colors resize-none"
          />
        </div>

        <footer className="flex justify-end gap-3 pt-2">
          <button
            type="button"
            onClick={onClose}
            className="px-6 py-2.5 rounded-full text-sm font-medium bg-brand-surface hover:bg-brand-surface-hover border border-brand-border transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={isSubmitting || isInvalid}
            className="bg-brand-primary hover:bg-brand-primary-hover text-white px-6 py-2.5 rounded-full text-sm font-medium flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
          >
            {isSubmitting && <Loader2 size={16} className="animate-spin" />}
            {isSubmitting ? "Creating..." : "Create Project"}
          </button>
        </footer>
      </form>
    </Modal>
  );
};

export default CreateProjectModal;
