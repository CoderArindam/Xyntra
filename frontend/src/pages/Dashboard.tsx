import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  Users,
  Folder,
  Loader2,
  Plus,
  Search,
  Trash2,
} from "lucide-react";

import { useAuthStore } from "../store/authStore";
import { useBoardStore } from "../store/boardStore";
import { useUiStore } from "../store/uiStore";
import CreateProjectModal from "../components/modals/CreateProjectModal";
import ConfirmDialog from "../components/common/ConfirmDialog/ConfirmDialog";

export const Dashboard: React.FC = () => {
  const { user } = useAuthStore();
  const currentUserId = user?.id ?? null;

  const { boards, isFetching, fetchBoards, removeBoard } = useBoardStore();
  const { openCreateProjectModal } = useUiStore();

  const [search, setSearch] = useState("");
  const [boardToDelete, setBoardToDelete] = useState<number | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  useEffect(() => {
    fetchBoards();
  }, [fetchBoards]);

  const handleDeleteClick = (e: React.MouseEvent, boardId: number) => {
    e.preventDefault();
    e.stopPropagation();
    setBoardToDelete(boardId);
  };

  const handleConfirmDelete = async () => {
    if (boardToDelete === null) return;
    setIsDeleting(true);
    await removeBoard(boardToDelete);
    setIsDeleting(false);
    setBoardToDelete(null);
  };

  const filteredBoards = boards.filter((board) =>
    board.name.toLowerCase().includes(search.toLowerCase()),
  );

  return (
    <>
      <main className="max-w-[1400px] mx-auto px-8 py-8 space-y-8">
        {/* Hero */}

        <section className="bg-brand-surface border border-brand-border rounded-2xl p-8">
          <h2 className="text-2xl font-semibold tracking-tight mb-2">
            Projects
          </h2>

          <p className="text-sm text-brand-text-muted">
            Manage your teams, boards and tasks in one place.
          </p>
        </section>

        {/* Title */}

        <section className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <h2 className="text-xl font-semibold">Project Boards</h2>

          <div className="flex items-center gap-3 w-full sm:w-auto">
            <div className="relative flex-1 sm:w-64">
              <Search
                size={16}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-brand-outline"
              />
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search projects..."
                className="w-full pl-9 pr-4 py-2.5 bg-brand-surface border border-brand-border rounded-full text-sm outline-none focus:border-brand-primary transition-colors"
              />
            </div>

            {user?.role !== "MEMBER" && (
              <button
                onClick={openCreateProjectModal}
                className="bg-brand-primary hover:bg-brand-primary-hover text-white px-5 py-2.5 rounded-full text-sm font-medium flex items-center gap-2 transition-colors shrink-0"
              >
                <Plus size={16} />
                Create Project
              </button>
            )}
          </div>
        </section>

        {/* Projects Grid */}

        <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 pb-32">
          {isFetching ? (
            <div className="col-span-full h-56 flex flex-col items-center justify-center text-brand-text-muted">
              <Loader2 className="w-8 h-8 animate-spin mb-4 text-brand-primary opacity-50" />
              <p>Loading projects...</p>
            </div>
          ) : filteredBoards.length === 0 ? (
            <div className="col-span-full h-56 border-2 border-dashed border-brand-border rounded-2xl flex flex-col items-center justify-center bg-brand-surface-low">
              <Folder
                size={48}
                className="text-brand-outline mb-4 opacity-50"
              />
              <h3 className="text-lg font-semibold">No projects found</h3>
              <p className="text-sm text-brand-text-muted mt-2">
                Create a new project to get started.
              </p>
            </div>
          ) : (
            filteredBoards.map((board) => {
              const isOwner = currentUserId === board.owner_id;
              return (
                <Link
                  key={board.id}
                  to={`/board/${board.id}`}
                  className="relative bg-brand-surface border border-brand-border rounded-2xl p-9 hover:shadow-md transition group"
                >
                  {isOwner ? (
                    <button
                      onClick={(e) => handleDeleteClick(e, board.id)}
                      className="absolute top-4 right-4 opacity-0 group-hover:opacity-100 w-8 h-8 rounded-full flex items-center justify-center text-brand-outline hover:text-brand-error hover:bg-red-50 transition"
                    >
                      <Trash2 size={15} />
                    </button>
                  ) : (
                    <span className="absolute top-2 right-4 flex items-center gap-1 text-xs text-brand-text-muted bg-brand-surface-low px-2 py-1 rounded-full">
                      <Users size={11} />
                      Member
                    </span>
                  )}

                  <h3 className="text-lg font-semibold group-hover:text-brand-primary transition">
                    {board.name}
                  </h3>

                  <p className="text-sm text-brand-text-muted mt-3">
                    Created {new Date(board.created_at).toLocaleDateString()}
                  </p>

                  <div className="mt-6 flex items-center justify-between text-sm">
                    <span className="text-brand-text-muted">Project Board</span>
                    <ArrowRight size={16} />
                  </div>
                </Link>
              );
            })
          )}
        </section>
      </main>

      <CreateProjectModal />

      <ConfirmDialog
        isOpen={boardToDelete !== null}
        onClose={() => setBoardToDelete(null)}
        onConfirm={handleConfirmDelete}
        title="Delete Board"
        description="Are you sure you want to delete this board? All tasks will be permanently removed. This action cannot be undone."
        confirmText="Delete"
        isDestructive={true}
        isLoading={isDeleting}
      />
    </>
  );
};

export default Dashboard;
