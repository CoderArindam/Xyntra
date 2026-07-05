import React, { useEffect, useState } from "react";
import { Folder, Loader2, Plus, Search, Trash2 } from "lucide-react";

import { useAuthStore } from "../store/authStore";
import {
  useBoardStore,
  useActiveBoards,
  useArchivedBoards,
} from "../store/boardStore";
import { useUiStore } from "../store/uiStore";
import { useOrganizationStore } from "../store/organizationStore";
import { usePageTitle } from "../hooks/usePageTitle";

import EmptyState from "../components/common/EmptyState";
import { ProjectCard } from "../components/common/ProjectCard";

export const Dashboard: React.FC = () => {
  const { user } = useAuthStore();

  usePageTitle("Dashboard");

  const { isFetching, fetchBoards } = useBoardStore();
  const activeBoards = useActiveBoards();
  const archivedBoards = useArchivedBoards();

  const { openCreateProjectModal } = useUiStore();
  const { profile } = useOrganizationStore();

  const [search, setSearch] = useState("");
  useEffect(() => {
    fetchBoards();
  }, [fetchBoards]);

  const filteredActiveBoards = activeBoards.filter((board) =>
    board.name.toLowerCase().includes(search.toLowerCase()),
  );

  const filteredArchivedBoards = archivedBoards.filter((board) =>
    board.name.toLowerCase().includes(search.toLowerCase()),
  );

  return (
    <>
      <main className="max-w-[1400px] mx-auto px-8 py-8 space-y-12">
        {/* Hero */}
        <section className="bg-brand-surface border border-brand-border rounded-2xl p-8">
          <h2 className="text-2xl font-semibold tracking-tight mb-2">
            Projects
          </h2>
          <p className="text-sm text-brand-text-muted">
            Manage your teams, boards and tasks in one place.
          </p>
        </section>

        {/* Header Actions */}
        <section className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <h2 className="text-xl font-semibold">Active Projects</h2>

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
                className="bg-brand-primary hover:bg-brand-primary-hover text-white px-5 py-2.5 rounded-full text-sm font-medium flex items-center gap-2 transition-colors shrink-0 cursor-pointer"
              >
                <Plus size={16} />
                Create Project
              </button>
            )}
          </div>
        </section>

        {/* Active Projects Grid */}
        <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {isFetching ? (
            <div className="col-span-full h-56 flex flex-col items-center justify-center text-brand-text-muted">
              <Loader2 className="w-8 h-8 animate-spin mb-4 text-brand-primary opacity-50" />
              <p>Loading projects...</p>
            </div>
          ) : filteredActiveBoards.length === 0 ? (
            <div className="col-span-full">
              <EmptyState
                icon={<Folder size={48} />}
                title={
                  search
                    ? "No active projects found."
                    : `${profile?.name || "Your Workspace"} doesn't have any projects yet.`
                }
                description={
                  search
                    ? "Try adjusting your search query."
                    : "Create your first project to get started."
                }
                action={
                  !search && user?.role !== "MEMBER" ? (
                    <button
                      onClick={openCreateProjectModal}
                      className="bg-brand-primary hover:bg-brand-primary-hover text-white px-5 py-2.5 rounded-full text-sm font-medium transition-colors cursor-pointer"
                    >
                      Create Project
                    </button>
                  ) : undefined
                }
              />
            </div>
          ) : (
            filteredActiveBoards.map((board) => (
              <ProjectCard
                key={board.id}
                board={board}
                className="shadow-sm hover:shadow-md"
              />
            ))
          )}
        </section>

        {/* Archived Projects Section */}
        {filteredArchivedBoards.length > 0 && (
          <section className="pt-8 border-t border-brand-border space-y-6 pb-32">
            <div>
              <h2 className="text-xl font-semibold">Archived Projects</h2>
              <p className="text-sm text-brand-text-muted mt-1">
                Read-only view of projects that have been archived.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              {filteredArchivedBoards.map((board) => (
                <div
                  key={board.id}
                  className="opacity-70 grayscale-[30%] pointer-events-none"
                >
                  <ProjectCard
                    board={board}
                    isLink={false}
                    className="shadow-sm"
                  />
                </div>
              ))}
            </div>
          </section>
        )}
      </main>
    </>
  );
};

export default Dashboard;
