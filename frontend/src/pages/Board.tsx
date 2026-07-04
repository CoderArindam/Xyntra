import React, { useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import KanbanBoard from "../components/KanbanBoard";
import { useBoardStore } from "../store/boardStore";

export const Board: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { boards, fetchBoards } = useBoardStore();

  useEffect(() => {
    if (boards.length === 0) {
      fetchBoards();
    }
  }, [boards.length, fetchBoards]);

  const boardId = id ? parseInt(id, 10) : 0;
  const board = boards.find((b) => b.id === boardId);

  return (
    <div className="min-h-screen bg-brand-bg flex flex-col">
      <header className="flex items-center justify-between px-8 py-6 bg-brand-surface border-b border-brand-border shrink-0">
        <div className="flex items-center gap-4">
          <Link
            to="/dashboard"
            className="w-10 h-10 flex items-center justify-center rounded-full hover:bg-brand-surface-low text-brand-text-muted hover:text-brand-text transition-colors"
            title="Back to Projects"
          >
            <ArrowLeft size={20} />
          </Link>
          <h1 className="text-2xl font-bold text-brand-text">
            {board ? board.name : `Board ${id}`}
          </h1>
        </div>
      </header>

      <main className="flex-1 overflow-x-auto bg-brand-bg">
        {boardId ? (
          <KanbanBoard boardId={boardId} />
        ) : (
          <div className="h-full flex items-center justify-center text-brand-text-muted">
            Invalid Board ID
          </div>
        )}
      </main>
    </div>
  );
};

export default Board;
