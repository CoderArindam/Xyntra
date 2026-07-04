import React, { useState } from "react";
import { Search, Plus, Loader2 } from "lucide-react";
import { useBoardStore } from "../store/boardStore";

interface DashboardBottomBarProps {
  search: string;
  onSearchChange: (value: string) => void;
}

const DashboardBottomBar: React.FC<DashboardBottomBarProps> = ({
  search,
  onSearchChange,
}) => {
  const { createNewBoard, isSubmitting } = useBoardStore();
  const [newBoardName, setNewBoardName] = useState("");

  const handleCreateBoard = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newBoardName.trim()) return;
    await createNewBoard(newBoardName);
    setNewBoardName("");
  };

  return (
    <div className="fixed bottom-6 left-1/2 -translate-x-1/2 w-[90%] max-w-4xl bg-brand-surface border border-brand-border rounded-full shadow-lg px-4 py-3 flex items-center gap-4 z-50">
      {/* Search */}
      <div className="relative flex-1">
        <Search
          size={17}
          className="absolute left-4 top-1/2 -translate-y-1/2 text-brand-outline"
        />

        <input
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="Search projects..."
          className="w-full pl-11 pr-4 py-3 bg-brand-surface-low rounded-full text-sm outline-none"
        />
      </div>

      {/* Create */}
      <form onSubmit={handleCreateBoard} className="flex items-center gap-3">
        <input
          value={newBoardName}
          onChange={(e) => setNewBoardName(e.target.value)}
          placeholder="New project"
          className="w-40 px-4 py-3 bg-brand-surface-low rounded-full text-sm outline-none"
        />

        <button
          disabled={isSubmitting}
          className="bg-brand-primary hover:bg-brand-primary-hover text-white px-6 py-3 rounded-full text-sm font-medium flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
        >
          {isSubmitting ? (
            <Loader2 size={16} className="animate-spin" />
          ) : (
            <Plus size={16} />
          )}
          {isSubmitting ? "Creating..." : "Create"}
        </button>
      </form>
    </div>
  );
};

export default DashboardBottomBar;
