import React, { useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, Settings, Folder } from 'lucide-react';
import KanbanBoard from './components/KanbanBoard';
import { useBoardStore } from '../../store/boardStore';
import { usePageTitle } from '../../hooks/usePageTitle';
import { ProjectIdentity } from '../../components/common/ProjectIdentity';
import EmptyState from '../../components/common/EmptyState';

import BoardProposalsBadge from '../proposals/components/BoardProposalsBadge';

export const Board: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { boards, fetchBoards } = useBoardStore();
  

  useEffect(() => {
    if (boards.length === 0) {
      fetchBoards();
    }
  }, [boards.length, fetchBoards]);

  const boardId = id ? parseInt(id, 10) : 0;
  const board = boards.find((b: any) => b.id === boardId);

  usePageTitle(board ? `${board.icon || ''} ${board.name}`.trim() : "Board");

  if (board && board.archived_at) {
    return (
      <div className="min-h-screen bg-brand-bg flex items-center justify-center p-8">
         <EmptyState
            icon={<Folder size={48} />}
            title="Project Archived"
            description="This project has been archived and is no longer accessible."
            action={
               <Link to="/dashboard" className="px-5 py-2.5 bg-brand-primary text-white rounded-full text-sm font-medium hover:bg-brand-primary-hover transition-colors">
                 Return to Dashboard
               </Link>
            }
         />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-brand-bg flex flex-col">
      <header className="flex items-center justify-between px-8 py-6 bg-brand-surface border-b border-brand-border shrink-0">
        <div className="flex items-center gap-4 min-w-0">
          <Link
            to="/dashboard"
            className="w-10 h-10 flex items-center justify-center rounded-full hover:bg-brand-surface-low text-brand-text-muted hover:text-brand-text transition-colors shrink-0"
            title="Back to Projects"
          >
            <ArrowLeft size={20} />
          </Link>
          {board ? (
            <ProjectIdentity board={board} showKey size="lg" />
          ) : (
            <h1 className="text-2xl font-bold text-brand-text">Board {id}</h1>
          )}
        </div>
        
        {/* Settings & Proposal Badge Actions */}
        <div className="flex items-center gap-3 shrink-0">
          {boardId > 0 && <BoardProposalsBadge boardId={boardId} />}
          <Link
            to={`/board/${boardId}/settings`}
            className="px-4 py-2 bg-brand-surface-low border border-brand-border hover:bg-brand-surface-hover rounded-md text-sm font-medium text-brand-text flex items-center gap-2 transition-colors"
          >
            <Settings size={16} />
            Project Settings
          </Link>
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
