import { create } from 'zustand';
import { loginUser, logoutUser, getMe } from '../api/authApi';
import toast from 'react-hot-toast';

interface User {
  id: number;
  email: string;
  first_name?: string;
  last_name?: string;
  avatar_url?: string;
  role: string;
  organization_id: number;
  is_email_verified: boolean;
}

interface AuthState {
  isAuthenticated: boolean;
  isInitializing: boolean;
  user: User | null;
  login: (email: string, password: string) => Promise<void>;
  logout: (forced?: boolean) => Promise<void>;
  initAuth: () => Promise<void>;
  updateUserLocally: (data: Partial<User>) => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  isAuthenticated: false,
  isInitializing: true,
  user: null,

  updateUserLocally: (data) => set((state) => ({
    user: state.user ? { ...state.user, ...data } : null
  })),

  initAuth: async () => {
    try {
      const userData = await getMe();
      set({ 
        isAuthenticated: true, 
        user: {
          id: userData.id,
          email: userData.email,
          first_name: userData.first_name,
          last_name: userData.last_name,
          avatar_url: userData.avatar_url,
          role: userData.role || 'MEMBER',
          organization_id: userData.organization_id,
          is_email_verified: userData.is_email_verified ?? true
        },
        isInitializing: false 
      });
    } catch (error) {
      set({ isAuthenticated: false, user: null, isInitializing: false });
    }
  },

  login: async (email, password) => {
    try {
      await loginUser(email, password);
      // After successful login, fetch the user data
      const userData = await getMe();
      set({ 
        isAuthenticated: true,
        user: {
          id: userData.id,
          email: userData.email,
          first_name: userData.first_name,
          last_name: userData.last_name,
          avatar_url: userData.avatar_url,
          role: userData.role || 'MEMBER',
          organization_id: userData.organization_id,
          is_email_verified: userData.is_email_verified ?? true
        }
      });
    } catch (error) {
      console.error('Login failed', error);
      throw error;
    }
  },

  logout: async (forced?: boolean) => {
    try {
      if (!forced) {
        await logoutUser();
      }
    } catch (error) {
      console.error('Logout API failed, clearing local state anyway', error);
    } finally {
      set({ isAuthenticated: false, user: null });
      if (!forced) {
        toast.success('Logged out successfully');
      } else {
        toast.error('Session expired. Please log in again.');
      }
    }
  }
}));
