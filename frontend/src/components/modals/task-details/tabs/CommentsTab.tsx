import React, { useState, useEffect, useRef } from "react";
import {
  MessageCircle,
  Reply,
  Trash2,
  X,
  AtSign,
  Send,
  Loader2,
} from "lucide-react";
import {
  getTaskComments,
  createComment,
  deleteComment,
  type Comment,
} from "../../../../api/commentsApi";
import { type Task } from "../../../../api/tasksApi";
import { type User } from "../../../../api/usersApi";
import toast from "react-hot-toast";
import { useActivityStore } from "../../../../store/activityStore";
import ConfirmDialog from "../../../common/ConfirmDialog/ConfirmDialog";
import { UserAvatar } from "../../../common/UserAvatar";
import { formatUserName } from "../../../../utils/userHelpers";

interface CommentsTabProps {
  task: Task;
  currentUserId: number | null;
  users: User[];
}

const CommentsTab: React.FC<CommentsTabProps> = ({
  task,
  currentUserId,
  users,
}) => {
  const [comments, setComments] = useState<Comment[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [newCommentText, setNewCommentText] = useState("");
  const [replyToCommentId, setReplyToCommentId] = useState<number | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showMentions, setShowMentions] = useState(false);
  const [mentionSearch, setMentionSearch] = useState("");
  const [cursorPos, setCursorPos] = useState(0);

  const [commentToDelete, setCommentToDelete] = useState<number | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const fetchComments = async () => {
    setIsLoading(true);
    try {
      const data = await getTaskComments(task.id);
      setComments(data);
    } catch (error) {
      console.error("Failed to fetch comments", error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchComments();
  }, [task.id]);

  const handleAddComment = async () => {
    if (!newCommentText.trim()) return;
    setIsSubmitting(true);
    try {
      await createComment(task.id, {
        content: newCommentText,
        parent_comment_id: replyToCommentId || undefined,
      });
      setNewCommentText("");
      setReplyToCommentId(null);
      await fetchComments();
      useActivityStore.getState().appendActivity(task.id, {
        entity_type: 'TASK', entity_id: task.id, activity_type: 'COMMENT_ADDED',
        old_value: null, new_value: null, metadata: {}
      });
      toast.success("Comment added");
    } catch (error) {
      console.error("Failed to create comment", error);
      toast.error("Failed to create comment");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleConfirmDeleteComment = async () => {
    if (commentToDelete === null) return;
    setIsDeleting(true);
    try {
      await deleteComment(commentToDelete);
      await fetchComments();
      useActivityStore.getState().appendActivity(task.id, {
        entity_type: 'TASK', entity_id: task.id, activity_type: 'COMMENT_DELETED',
        old_value: null, new_value: null, metadata: {}
      });
      toast.success("Comment deleted");
    } catch (error) {
      console.error("Failed to delete comment", error);
      toast.error("Failed to delete comment");
    } finally {
      setIsDeleting(false);
      setCommentToDelete(null);
    }
  };

  const handleTextareaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value;
    setNewCommentText(value);
    const cursor = e.target.selectionStart;
    setCursorPos(cursor);

    const textBefore = value.slice(0, cursor);
    const match = textBefore.match(/@(\w*)$/);
    if (match) {
      setShowMentions(true);
      setMentionSearch(match[1].toLowerCase());
    } else {
      setShowMentions(false);
    }
  };

  const insertMention = (user: User) => {
    const textBefore = newCommentText.slice(0, cursorPos);
    const textAfter = newCommentText.slice(cursorPos);
    const match = textBefore.match(/@(\w*)$/);
    if (match) {
      const mentionText = user.first_name ? user.first_name.replace(/\s+/g, '') : user.email.split('@')[0];
      const newText =
        textBefore.slice(0, match.index) + `@${mentionText} ` + textAfter;
      setNewCommentText(newText);
    }
    setShowMentions(false);
    textareaRef.current?.focus();
  };

  const filteredUsers = users.filter((u) => {
    const search = mentionSearch.toLowerCase();
    const fullName = `${u.first_name || ''} ${u.last_name || ''}`.toLowerCase();
    return u.email.toLowerCase().includes(search) || fullName.includes(search);
  });
  const rootComments = comments.filter((c) => !c.parent_comment_id);

  return (
    <section className="flex flex-col h-[500px]">
      <div className="flex-1 overflow-y-auto space-y-6 pr-2">
        {isLoading ? (
          <div className="py-8 flex flex-col items-center justify-center text-sm text-brand-text-muted bg-brand-surface-low rounded-lg border border-dashed border-brand-border">
            <Loader2 size={32} className="mb-3 animate-spin opacity-40" />
            Loading comments...
          </div>
        ) : comments.length === 0 ? (
          <div className="py-8 flex flex-col items-center justify-center text-brand-text-muted bg-brand-surface-low rounded-lg border border-dashed border-brand-border">
            <MessageCircle size={32} className="mb-3 opacity-40" />
            <p className="text-sm font-medium">No comments yet</p>
            <p className="text-xs mt-1">
              Be the first to comment on this task.
            </p>
          </div>
        ) : (
          rootComments.map((item) => {
            const itemUser = {
              first_name: item.user_first_name,
              last_name: item.user_last_name,
              email: item.user_email,
              avatar_url: item.user_avatar_url
            };
            const replies = comments.filter(
              (c) => c.parent_comment_id === item.id,
            );

            return (
              <div key={item.id} className="flex gap-3">
                <UserAvatar user={itemUser} size="md" />

                <div className="flex-1">
                  <div className="flex justify-between items-center">
                    <span className="font-semibold text-sm text-brand-text">
                      {formatUserName(itemUser)}
                    </span>
                    <span className="text-xs text-brand-text-muted">
                      {new Date(item.created_at).toLocaleTimeString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </span>
                  </div>

                  <div className="mt-1 bg-brand-surface border border-brand-border rounded-lg p-3 text-sm whitespace-pre-wrap text-brand-text">
                    {item.content}
                  </div>

                  <div className="flex gap-4 mt-2 text-xs text-brand-text-muted">
                    <button
                      onClick={() => setReplyToCommentId(item.id)}
                      className="hover:text-brand-primary flex items-center gap-1"
                    >
                      <Reply size={14} /> Reply
                    </button>
                    {currentUserId === item.user_id && (
                      <button
                        onClick={() => setCommentToDelete(item.id)}
                        className="hover:text-red-500 flex items-center gap-1"
                      >
                        <Trash2 size={14} /> Delete
                      </button>
                    )}
                  </div>

                  {replies.length > 0 && (
                    <div className="mt-3 space-y-3">
                      {replies.map((reply) => {
                        const replyUser = {
                          first_name: reply.user_first_name,
                          last_name: reply.user_last_name,
                          email: reply.user_email,
                          avatar_url: reply.user_avatar_url
                        };
                        return (
                          <div key={reply.id} className="flex gap-2">
                            <UserAvatar user={replyUser} size="sm" />
                            <div className="flex-1">
                              <div className="flex justify-between">
                                <span className="font-medium text-xs text-brand-text">
                                  {formatUserName(replyUser)}
                                </span>
                              </div>
                              <div className="mt-1 bg-brand-surface-low border border-brand-border rounded p-2 text-xs whitespace-pre-wrap text-brand-text">
                                {reply.content}
                              </div>
                              {currentUserId === reply.user_id && (
                                <button
                                  onClick={() => setCommentToDelete(reply.id)}
                                  className="text-[10px] text-brand-text-muted hover:text-red-500 mt-1"
                                >
                                  Delete
                                </button>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>

      <div className="pt-4 mt-4 border-t border-brand-border relative">
        {replyToCommentId && (
          <div className="flex justify-between items-center text-xs text-brand-primary mb-2 bg-brand-surface p-2 rounded border border-brand-border">
            <span>Replying to comment...</span>
            <button
              onClick={() => setReplyToCommentId(null)}
              className="p-1 hover:bg-brand-surface-container rounded"
            >
              <X size={14} />
            </button>
          </div>
        )}

        {showMentions && (
          <div className="absolute bottom-full left-0 mb-2 w-64 bg-brand-surface border border-brand-border rounded-lg shadow-lg z-50 max-h-48 overflow-y-auto">
            {filteredUsers.length > 0 ? (
              filteredUsers.map((u) => (
                <button
                  key={u.id}
                  onClick={() => insertMention(u)}
                  className="w-full text-left px-4 py-2 text-sm hover:bg-brand-surface-low transition text-brand-text flex items-center gap-2"
                >
                  <UserAvatar user={u} size="sm" />
                  <div className="flex flex-col">
                    <span className="font-medium text-xs leading-none">
                      {formatUserName(u)}
                    </span>
                    {u.first_name && <span className="text-[10px] text-brand-text-muted mt-1 leading-none">{u.email}</span>}
                  </div>
                </button>
              ))
            ) : (
              <div className="px-4 py-2 text-sm text-brand-text-muted">
                No users found
              </div>
            )}
          </div>
        )}

        <textarea
          ref={textareaRef}
          rows={3}
          placeholder="Add a comment... (Type @ to mention)"
          value={newCommentText}
          onChange={handleTextareaChange}
          className="w-full bg-brand-surface border border-brand-border rounded-lg p-3 text-sm outline-none focus:border-brand-primary"
        />

        <div className="flex justify-between mt-3">
          <button
            type="button"
            className="text-brand-text-muted hover:text-brand-text"
            onClick={() => {
              setNewCommentText(newCommentText + "@");
              textareaRef.current?.focus();
            }}
          >
            <AtSign size={18} />
          </button>

          <button
            onClick={handleAddComment}
            disabled={!newCommentText.trim() || isSubmitting}
            className="bg-brand-primary hover:bg-brand-primary-hover text-white px-4 py-2 rounded-lg flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed transition text-sm font-medium"
          >
            {isSubmitting && <Loader2 size={15} className="animate-spin" />}
            {isSubmitting ? "Sending..." : "Send"}
            {!isSubmitting && <Send size={15} />}
          </button>
        </div>
      </div>
      
      <ConfirmDialog
        isOpen={commentToDelete !== null}
        onClose={() => setCommentToDelete(null)}
        onConfirm={handleConfirmDeleteComment}
        title="Delete Comment"
        description="Are you sure you want to delete this comment? This action cannot be undone."
        confirmText="Delete"
        isDestructive={true}
        isLoading={isDeleting}
      />
    </section>
  );
};

export default CommentsTab;
