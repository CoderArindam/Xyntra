import React from 'react';
import { Search, Filter, SortDesc, LayoutList } from 'lucide-react';

interface MyWorkToolbarProps {
  search: string;
  setSearch: (val: string) => void;
  status: string;
  setStatus: (val: string) => void;
  priority: string;
  setPriority: (val: string) => void;
  due: string;
  setDue: (val: string) => void;
  sort: string;
  setSort: (val: string) => void;
  grouping: string;
  setGrouping: (val: string) => void;
}

const MyWorkToolbar: React.FC<MyWorkToolbarProps> = React.memo(({
  search, setSearch,
  status, setStatus,
  priority, setPriority,
  due, setDue,
  sort, setSort,
  grouping, setGrouping
}) => {
  return (
    <div className="flex flex-col md:flex-row gap-4 items-center bg-brand-surface border border-brand-border rounded-2xl p-4">
      {/* Search */}
      <div className="relative flex-1 w-full">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-brand-text-muted" size={18} />
        <input 
          type="text" 
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search your tasks..." 
          className="w-full pl-10 pr-4 py-2 bg-brand-surface-low border border-brand-border rounded-xl text-sm text-brand-text focus:outline-none focus:border-brand-primary focus:ring-1 focus:ring-brand-primary transition-shadow"
        />
      </div>

      {/* Filters Container */}
      <div className="flex flex-wrap gap-2 w-full md:w-auto">
        
        {/* Status Filter */}
        <div className="flex items-center gap-2 bg-brand-surface-low border border-brand-border rounded-xl px-3 py-1.5">
          <Filter size={14} className="text-brand-text-muted" />
          <select 
            value={status} 
            onChange={(e) => setStatus(e.target.value)}
            className="bg-transparent text-sm text-brand-text focus:outline-none cursor-pointer appearance-none pr-4"
          >
            <option value="all">All Status</option>
            <option value="todo">To Do</option>
            <option value="in_progress">In Progress</option>
            <option value="done">Done</option>
          </select>
        </div>

        {/* Priority Filter */}
        <div className="flex items-center gap-2 bg-brand-surface-low border border-brand-border rounded-xl px-3 py-1.5">
          <select 
            value={priority} 
            onChange={(e) => setPriority(e.target.value)}
            className="bg-transparent text-sm text-brand-text focus:outline-none cursor-pointer appearance-none pr-4"
          >
            <option value="all">All Priorities</option>
            <option value="High">High</option>
            <option value="Medium">Medium</option>
            <option value="Low">Low</option>
          </select>
        </div>

        {/* Due Date Filter */}
        <div className="flex items-center gap-2 bg-brand-surface-low border border-brand-border rounded-xl px-3 py-1.5">
          <select 
            value={due} 
            onChange={(e) => setDue(e.target.value)}
            className="bg-transparent text-sm text-brand-text focus:outline-none cursor-pointer appearance-none pr-4"
          >
            <option value="all">All Dates</option>
            <option value="overdue">Overdue</option>
            <option value="today">Due Today</option>
            <option value="week">Due This Week</option>
            <option value="none">No Due Date</option>
          </select>
        </div>
      </div>

      <div className="w-px h-8 bg-brand-border hidden md:block mx-1"></div>

      {/* Sort & Grouping Container */}
      <div className="flex gap-2 w-full md:w-auto">
        <div className="flex items-center gap-2 bg-brand-surface-low border border-brand-border rounded-xl px-3 py-1.5 flex-1 md:flex-none">
          <SortDesc size={14} className="text-brand-text-muted" />
          <select 
            value={sort} 
            onChange={(e) => setSort(e.target.value)}
            className="bg-transparent text-sm text-brand-text focus:outline-none cursor-pointer appearance-none pr-4 w-full"
          >
            <option value="due">Sort: Due Date</option>
            <option value="priority">Sort: Priority</option>
            <option value="updated">Sort: Updated</option>
            <option value="created">Sort: Created</option>
            <option value="alpha">Sort: A-Z</option>
          </select>
        </div>

        <div className="flex items-center gap-2 bg-brand-surface-low border border-brand-border rounded-xl px-3 py-1.5 flex-1 md:flex-none">
          <LayoutList size={14} className="text-brand-text-muted" />
          <select 
            value={grouping} 
            onChange={(e) => setGrouping(e.target.value)}
            className="bg-transparent text-sm text-brand-text focus:outline-none cursor-pointer appearance-none pr-4 w-full"
          >
            <option value="none">Group: None</option>
            <option value="board">Group: Board</option>
            <option value="status">Group: Status</option>
            <option value="priority">Group: Priority</option>
            <option value="due">Group: Due Date</option>
          </select>
        </div>
      </div>
    </div>
  );
});

MyWorkToolbar.displayName = 'MyWorkToolbar';

export default MyWorkToolbar;
