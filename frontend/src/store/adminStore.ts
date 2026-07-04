import { create } from 'zustand';
import { 
  type AdminUser, 
  type AdminBoard, 
  type AdminBoardMember, 
  adminFetchUsers, 
  adminUpdateUserRole, 
  adminDeleteUser, 
  adminFetchBoards, 
  adminFetchBoardMembers, 
  adminAssignUser, 
  adminRemoveUser 
} from '../api/adminApi';
import { adminInviteUser, adminListInvitations, type Invitation } from '../api/invitationsApi';
import toast from 'react-hot-toast';

interface AdminState {
  users: AdminUser[];
  invitations: Invitation[];
  boards: AdminBoard[];
  selectedBoardMembers: AdminBoardMember[];
  
  isFetchingUsers: boolean;
  isFetchingInvitations: boolean;
  isInvitingUser: boolean;
  isUpdatingRole: boolean;
  isDeletingUser: boolean;
  
  isFetchingBoards: boolean;
  isFetchingMembers: boolean;
  isAssigningUser: boolean;
  isRemovingUser: boolean;

  fetchUsers: () => Promise<void>;
  fetchInvitations: () => Promise<void>;
  inviteUser: (email: string, role: string) => Promise<void>;
  updateUserRole: (userId: number, role: string) => Promise<void>;
  deleteUser: (userId: number) => Promise<void>;

  fetchBoards: () => Promise<void>;
  fetchBoardMembers: (boardId: number) => Promise<void>;
  assignUserToBoard: (boardId: number, userId: number, permission: string) => Promise<void>;
  removeUserFromBoard: (boardId: number, userId: number) => Promise<void>;
}

export const useAdminStore = create<AdminState>((set, get) => ({
  users: [],
  invitations: [],
  boards: [],
  selectedBoardMembers: [],

  isFetchingUsers: false,
  isFetchingInvitations: false,
  isInvitingUser: false,
  isUpdatingRole: false,
  isDeletingUser: false,
  
  isFetchingBoards: false,
  isFetchingMembers: false,
  isAssigningUser: false,
  isRemovingUser: false,

  fetchUsers: async () => {
    set({ isFetchingUsers: true });
    try {
      const users = await adminFetchUsers();
      set({ users });
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to fetch users');
    } finally {
      set({ isFetchingUsers: false });
    }
  },

  fetchInvitations: async () => {
    set({ isFetchingInvitations: true });
    try {
      const invitations = await adminListInvitations();
      set({ invitations });
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to fetch invitations');
    } finally {
      set({ isFetchingInvitations: false });
    }
  },

  inviteUser: async (email, role) => {
    set({ isInvitingUser: true });
    try {
      const newInvitation = await adminInviteUser(email, role);
      set((state) => ({ invitations: [newInvitation, ...state.invitations] }));
      toast.success('User invited successfully');
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to invite user');
      throw error;
    } finally {
      set({ isInvitingUser: false });
    }
  },

  updateUserRole: async (userId, role) => {
    set({ isUpdatingRole: true });
    try {
      const updatedUser = await adminUpdateUserRole(userId, role);
      set((state) => ({
        users: state.users.map(u => u.id === userId ? updatedUser : u)
      }));
      toast.success('User role updated');
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to update role');
    } finally {
      set({ isUpdatingRole: false });
    }
  },

  deleteUser: async (userId) => {
    set({ isDeletingUser: true });
    try {
      await adminDeleteUser(userId);
      set((state) => ({
        users: state.users.filter(u => u.id !== userId)
      }));
      toast.success('User deleted successfully');
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to delete user');
    } finally {
      set({ isDeletingUser: false });
    }
  },

  fetchBoards: async () => {
    set({ isFetchingBoards: true });
    try {
      const boards = await adminFetchBoards();
      set({ boards });
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to fetch boards');
    } finally {
      set({ isFetchingBoards: false });
    }
  },

  fetchBoardMembers: async (boardId) => {
    set({ isFetchingMembers: true });
    try {
      const members = await adminFetchBoardMembers(boardId);
      set({ selectedBoardMembers: members });
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to fetch board members');
    } finally {
      set({ isFetchingMembers: false });
    }
  },

  assignUserToBoard: async (boardId, userId, permission) => {
    set({ isAssigningUser: true });
    try {
      await adminAssignUser(boardId, userId, permission);
      toast.success('User assigned to board');
      await get().fetchBoardMembers(boardId);
      await get().fetchBoards(); // Update member count
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to assign user');
    } finally {
      set({ isAssigningUser: false });
    }
  },

  removeUserFromBoard: async (boardId, userId) => {
    set({ isRemovingUser: true });
    try {
      await adminRemoveUser(boardId, userId);
      set((state) => ({
        selectedBoardMembers: state.selectedBoardMembers.filter(m => m.id !== userId)
      }));
      toast.success('User removed from board');
      await get().fetchBoards(); // Update member count
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to remove user');
    } finally {
      set({ isRemovingUser: false });
    }
  }
}));
