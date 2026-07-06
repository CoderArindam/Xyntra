import React from 'react';
import { UserRound } from 'lucide-react';
import { type User } from '../../services/usersApi';
import { formatUserName } from '../../utils/userHelpers';

interface AssigneeSelectorProps {
  assigneeId: number | null | undefined;
  users: User[];
  onChange: (newAssigneeId: number | null) => void;
  disabled?: boolean;
}

const AssigneeSelector: React.FC<AssigneeSelectorProps> = ({ assigneeId, users, onChange, disabled }) => {
  return (
    <div className="flex items-center gap-2">
      <UserRound size={14} className="text-brand-text-muted" />
      <select
        value={assigneeId ?? ""}
        onChange={(e) => {
          const val = e.target.value;
          onChange(val ? parseInt(val, 10) : null);
        }}
        disabled={disabled}
        className="bg-brand-surface border border-brand-border rounded px-2 py-1 text-sm outline-none focus:border-brand-primary"
      >
        <option value="">Unassigned</option>
        {users.map(u => (
          <option key={u.id} value={u.id}>{formatUserName(u)}</option>
        ))}
      </select>
    </div>
  );
};

export default AssigneeSelector;
