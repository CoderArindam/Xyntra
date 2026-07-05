import React, { useEffect, useState } from "react";
import { useAdminStore } from "../../store/adminStore";
import { Users, Loader2, Trash2 } from "lucide-react";
import { UserAvatar } from "../../components/common/UserAvatar";
import { formatUserName } from "../../utils/userHelpers";
import { usePageTitle } from "../../hooks/usePageTitle";

const BoardPermissions: React.FC = () => {
  const {
    boards,
    fetchBoards,
    isFetchingBoards,
    users,
    fetchUsers,
    selectedBoardMembers,
    fetchBoardMembers,
    isFetchingMembers,
    assignUserToBoard,
    removeUserFromBoard,
    isAssigningUser,
    isRemovingUser,
  } = useAdminStore();

  usePageTitle("Board Permissions");

  const [selectedBoardId, setSelectedBoardId] = useState<number | null>(null);

  // Assign user form state
  const [assignUserId, setAssignUserId] = useState<string>("");
  const [assignPermission, setAssignPermission] = useState<string>("VIEWER");

  useEffect(() => {
    fetchBoards();
    fetchUsers(); // Needed for the user dropdown
  }, [fetchBoards, fetchUsers]);

  useEffect(() => {
    if (selectedBoardId) {
      fetchBoardMembers(selectedBoardId);
    }
  }, [selectedBoardId, fetchBoardMembers]);

  const handleAssign = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedBoardId || !assignUserId) return;

    await assignUserToBoard(
      selectedBoardId,
      parseInt(assignUserId, 10),
      assignPermission,
    );
    setAssignUserId("");
    setAssignPermission("VIEWER");
  };

  const handleRemove = async (userId: number) => {
    if (!selectedBoardId) return;
    await removeUserFromBoard(selectedBoardId, userId);
  };

  const selectedBoard = boards.find((b) => b.id === selectedBoardId);

  return (
    <div className="flex flex-col h-full gap-6">
      <header>
        <h1 className="text-2xl font-bold tracking-tight text-brand-text">
          Board Permissions
        </h1>
        <p className="text-brand-text-muted text-sm mt-1">
          Manage who has access to specific projects.
        </p>
      </header>

      <div className="flex flex-col lg:flex-row gap-8 flex-1 lg:min-h-0 lg:overflow-hidden mt-4">
        {/* Boards List (Sidebar) */}
        <div className="w-full lg:w-1/3 bg-brand-bg border border-brand-border rounded-2xl flex flex-col shadow-sm overflow-hidden max-h-[400px] lg:max-h-none lg:min-h-0">
          <div className="p-5 border-b border-brand-border bg-brand-surface-low">
            <h2 className="font-semibold text-brand-text flex items-center gap-3">
              <FolderKanbanIcon />
              All Projects
            </h2>
          </div>

          <div className="flex-1 overflow-y-auto p-3 space-y-2">
            {isFetchingBoards ? (
              <div className="p-8 flex justify-center">
                <Loader2
                  className="animate-spin text-brand-text-muted"
                  size={24}
                />
              </div>
            ) : boards.length === 0 ? (
              <div className="p-8 text-center text-sm text-brand-text-muted">
                No projects found.
              </div>
            ) : (
              boards.map((board) => (
                <button
                  key={board.id}
                  onClick={() => setSelectedBoardId(board.id)}
                  className={`w-full text-left px-5 py-4 rounded-xl flex items-center justify-between transition-all duration-200 group cursor-pointer ${
                    selectedBoardId === board.id
                      ? "bg-brand-primary/10 text-brand-primary ring-1 ring-brand-primary/20"
                      : "hover:bg-brand-surface text-brand-text"
                  }`}
                >
                  <span className="font-medium truncate pr-4">
                    {board.name}
                  </span>
                  <span
                    className={`text-xs px-2.5 py-1 rounded-full font-medium transition-colors ${
                      selectedBoardId === board.id
                        ? "bg-brand-primary/20 text-brand-primary"
                        : "bg-brand-surface-low text-brand-text-muted group-hover:bg-brand-border"
                    }`}
                  >
                    {board.member_count}{" "}
                    {board.member_count === 1 ? "member" : "members"}
                  </span>
                </button>
              ))
            )}
          </div>
        </div>

        {/* Board Details (Main Content) */}
        <div className="flex-1 bg-brand-bg border border-brand-border rounded-2xl flex flex-col shadow-sm min-h-[500px] lg:min-h-0 overflow-hidden">
          {!selectedBoardId ? (
            <div className="flex-1 flex flex-col items-center justify-center text-brand-text-muted p-12 text-center bg-brand-surface-low/30">
              <Users size={64} className="mb-6 opacity-10" />
              <h3 className="text-lg font-semibold text-brand-text mb-2">
                Select a Project
              </h3>
              <p className="max-w-xs text-sm">
                Choose a project from the sidebar to view and manage its member
                access levels.
              </p>
            </div>
          ) : (
            <>
              <div className="p-8 border-b border-brand-border flex flex-col gap-8 bg-brand-surface">
                <div>
                  <h2 className="text-2xl font-bold text-brand-text tracking-tight">
                    {selectedBoard?.name}
                  </h2>
                  <p className="text-brand-text-muted text-sm mt-2">
                    Manage members and their roles for this project.
                  </p>
                </div>

                {/* Assign Form */}
                <form
                  onSubmit={handleAssign}
                  className="flex flex-col sm:flex-row flex-wrap gap-4 bg-brand-bg p-5 rounded-2xl border border-brand-border shadow-sm"
                >
                  <select
                    value={assignUserId}
                    onChange={(e) => setAssignUserId(e.target.value)}
                    className="flex-1 min-w-[200px] bg-brand-surface border border-brand-border rounded-xl px-4 py-3 text-sm text-brand-text outline-none focus:border-brand-primary focus:ring-1 focus:ring-brand-primary transition-shadow cursor-pointer"
                    required
                  >
                    <option value="" disabled>
                      Select User...
                    </option>
                    {users.map((u) => (
                      <option key={u.id} value={u.id} className="text-black">
                        {formatUserName(u)}
                      </option>
                    ))}
                  </select>

                  <select
                    value={assignPermission}
                    onChange={(e) => setAssignPermission(e.target.value)}
                    className="w-full sm:w-auto bg-brand-surface border border-brand-border rounded-xl px-4 py-3 text-sm text-brand-text outline-none focus:border-brand-primary focus:ring-1 focus:ring-brand-primary transition-shadow appearance-none cursor-pointer"
                  >
                    <option value="VIEWER" className="text-black">
                      Viewer
                    </option>
                    <option value="EDITOR" className="text-black">
                      Editor
                    </option>
                    <option value="OWNER" className="text-black">
                      Owner
                    </option>
                  </select>

                  <button
                    type="submit"
                    disabled={isAssigningUser || !assignUserId}
                    className="w-full sm:w-auto bg-brand-primary hover:bg-brand-primary-hover text-white px-6 py-3 rounded-xl font-medium text-sm flex items-center justify-center gap-2 transition-colors disabled:opacity-50 whitespace-nowrap shadow-sm cursor-pointer"
                  >
                    {isAssigningUser ? (
                      <Loader2 size={16} className="animate-spin" />
                    ) : null}
                    Assign Access
                  </button>
                </form>
              </div>

              {/* Members Table */}
              <div className="flex-1 overflow-auto bg-brand-bg">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-brand-border bg-brand-surface text-brand-text-muted text-xs uppercase tracking-wider font-semibold sticky top-0 z-10">
                      <th className="px-8 py-4">Team Member</th>
                      <th className="px-8 py-4">Access Level</th>
                      <th className="px-8 py-4 text-center">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-brand-border">
                    {isFetchingMembers ? (
                      <tr>
                        <td
                          colSpan={3}
                          className="p-12 text-center text-brand-text-muted"
                        >
                          <Loader2
                            className="animate-spin mx-auto mb-2"
                            size={24}
                          />
                          <p className="text-sm">Loading members...</p>
                        </td>
                      </tr>
                    ) : selectedBoardMembers.length === 0 ? (
                      <tr>
                        <td
                          colSpan={3}
                          className="p-12 text-center text-brand-text-muted"
                        >
                          <p>No members explicitly assigned.</p>
                        </td>
                      </tr>
                    ) : (
                      selectedBoardMembers.map((member) => (
                        <tr
                          key={member.id}
                          className="hover:bg-brand-surface/50 transition-colors group"
                        >
                          <td className="px-8 py-4">
                            <div className="flex items-center gap-4">
                              <UserAvatar user={member} size="md" />
                              <div>
                                <div className="text-sm font-medium text-brand-text">
                                  {formatUserName(member)}
                                </div>
                                {member.role === "SUPER_ADMIN" && (
                                  <div className="text-[10px] text-brand-primary font-bold mt-1 tracking-wider">
                                    SUPER ADMIN
                                  </div>
                                )}
                              </div>
                            </div>
                          </td>
                          <td className="px-8 py-4">
                            <span
                              className={`px-3 py-1.5 rounded-full text-xs font-semibold tracking-wide ${
                                member.permission === "OWNER"
                                  ? "bg-purple-500/10 text-purple-500 border border-purple-500/20"
                                  : member.permission === "EDITOR"
                                    ? "bg-blue-500/10 text-blue-500 border border-blue-500/20"
                                    : "bg-brand-surface text-brand-text-muted border border-brand-border"
                              }`}
                            >
                              {member.permission}
                            </span>
                          </td>
                          <td className="px-8 py-4 text-center">
                            <div className="flex justify-center">
                              <button
                                onClick={() => handleRemove(member.id)}
                                disabled={isRemovingUser}
                                className="p-2 text-brand-text-muted hover:text-red-500 hover:bg-red-500/10 rounded-lg transition-colors disabled:opacity-30 disabled:hover:bg-transparent disabled:hover:text-brand-text-muted"
                                title="Revoke access"
                              >
                                <Trash2 size={18} />
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

// Helper icon component since FolderKanban might not be in lucide-react if old version
const FolderKanbanIcon = () => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width="18"
    height="18"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M4 20h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.93a2 2 0 0 1-1.66-.9l-.82-1.2A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13c0 1.1.9 2 2 2Z" />
    <path d="M8 10v4" />
    <path d="M12 10v2" />
    <path d="M16 10v6" />
  </svg>
);

export default BoardPermissions;
