import { create } from 'zustand';
import { getOrganizationProfile, updateOrganizationProfile, type OrganizationProfile, type OrganizationProfileUpdate } from '../services/organizationApi';

interface OrganizationState {
  profile: OrganizationProfile | null;
  isLoading: boolean;
  error: string | null;
  
  fetchProfile: () => Promise<void>;
  updateProfile: (updates: OrganizationProfileUpdate) => Promise<void>;
}

// Document title logic has been moved to AppLayout and usePageTitle hook.

export const useOrganizationStore = create<OrganizationState>((set, get) => ({
  profile: null,
  isLoading: false,
  error: null,

  fetchProfile: async () => {
    set({ isLoading: true, error: null });
    try {
      const profile = await getOrganizationProfile();
      set({ profile, isLoading: false });
    } catch (error: any) {
      set({ error: error.message || 'Failed to fetch organization profile', isLoading: false });
    }
  },

  updateProfile: async (updates: OrganizationProfileUpdate) => {
    const currentProfile = get().profile;
    
    // Optimistic update
    if (currentProfile) {
      const newProfile = { ...currentProfile, ...updates };
      set({ profile: newProfile });
    }

    try {
      const profile = await updateOrganizationProfile(updates);
      set({ profile });
    } catch (error: any) {
      // Revert optimistic update
      if (currentProfile) {
        set({ profile: currentProfile, error: error.message || 'Failed to update organization profile' });
      } else {
        set({ error: error.message || 'Failed to update organization profile' });
      }
      throw error;
    }
  },
}));
