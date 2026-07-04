import React, { useState, useEffect } from 'react';
import { Paperclip, Plus, Loader2, Image, FileText } from 'lucide-react';
import { getTaskAttachments, createAttachment, type Attachment } from '../../../../api/attachmentsApi';
import { type Task } from '../../../../api/tasksApi';
import toast from 'react-hot-toast';
import { useActivityStore } from '../../../../store/activityStore';

interface AttachmentsTabProps {
  task: Task;
}

const AttachmentsTab: React.FC<AttachmentsTabProps> = ({ task }) => {
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchAttachments = async () => {
    setIsLoading(true);
    try {
      const data = await getTaskAttachments(task.id);
      setAttachments(data);
    } catch (error) {
      console.error("Failed to fetch attachments", error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAttachments();
  }, [task.id]);

  const handleAdd = async () => {
    if (!name || !url) return;
    setIsSubmitting(true);
    try {
      await createAttachment(task.id, { file_name: name, file_url: url });
      setName("");
      setUrl("");
      setShowForm(false);
      await fetchAttachments();
      useActivityStore.getState().appendActivity(task.id, {
        entity_type: 'TASK', entity_id: task.id, activity_type: 'ATTACHMENT_ADDED',
        old_value: null, new_value: { file_name: name, file_url: url }, metadata: {}
      });
      toast.success("Attachment added");
    } catch (error) {
      console.error("Failed to add attachment", error);
      toast.error("Failed to add attachment");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <section>
      <div className="flex justify-between items-center mb-4">
        <h3 className="font-medium text-brand-text">Files</h3>
        <button
          onClick={() => setShowForm(!showForm)}
          className="text-xs text-brand-primary hover:underline flex items-center gap-1"
        >
          <Plus size={14} /> Add MVP Attachment
        </button>
      </div>

      {showForm && (
        <div className="mb-4 p-4 border border-brand-border rounded-lg bg-brand-surface-low space-y-3">
          <input
            type="text"
            placeholder="File Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full bg-brand-surface border border-brand-border rounded p-2 text-sm outline-none focus:border-brand-primary"
          />
          <input
            type="text"
            placeholder="File URL"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            className="w-full bg-brand-surface border border-brand-border rounded p-2 text-sm outline-none focus:border-brand-primary"
          />
          <button
            onClick={handleAdd}
            disabled={isSubmitting || !name || !url}
            className="bg-brand-primary hover:bg-brand-primary-hover text-white px-4 py-1.5 rounded text-sm flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed transition"
          >
            {isSubmitting && <Loader2 size={14} className="animate-spin" />}
            {isSubmitting ? "Submitting..." : "Submit"}
          </button>
        </div>
      )}

      {isLoading ? (
        <div className="py-6 text-sm text-brand-text-muted flex flex-col items-center justify-center bg-brand-surface-low rounded-lg border border-dashed border-brand-border">
          <Loader2 size={24} className="mb-2 animate-spin opacity-50" />
          Loading attachments...
        </div>
      ) : attachments.length === 0 ? (
        <div className="py-6 text-sm text-brand-text-muted flex flex-col items-center justify-center bg-brand-surface-low rounded-lg border border-dashed border-brand-border">
          <Paperclip size={24} className="mb-2 opacity-50" />
          <p>No attachments yet</p>
        </div>
      ) : (
        <div className="grid grid-cols-3 md:grid-cols-4 gap-4">
          {attachments.map((att) => (
            <div
              key={att.id}
              className="aspect-video rounded-lg border border-brand-border bg-brand-surface-low flex flex-col items-center justify-center p-2 text-center relative group"
            >
              {att.file_url.match(/\.(jpeg|jpg|gif|png)$/i) ? (
                <Image size={32} className="text-brand-text-muted group-hover:text-brand-primary transition" />
              ) : (
                <FileText size={32} className="text-brand-text-muted group-hover:text-brand-primary transition" />
              )}
              <span className="text-xs mt-2 break-all line-clamp-1 px-1 text-brand-text">
                {att.file_name}
              </span>
              <a
                href={att.file_url}
                target="_blank"
                rel="noopener noreferrer"
                className="absolute inset-0 rounded-lg hover:bg-black/5 transition"
                aria-label={`View ${att.file_name}`}
              />
            </div>
          ))}
        </div>
      )}
    </section>
  );
};

export default AttachmentsTab;
