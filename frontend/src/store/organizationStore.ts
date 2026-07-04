import { create } from 'zustand';
import { getOrganizationProfile, updateOrganizationProfile, type OrganizationProfile, type OrganizationProfileUpdate } from '../api/organizationApi';

interface OrganizationState {
  profile: OrganizationProfile | null;
  isLoading: boolean;
  error: string | null;
  
  fetchProfile: () => Promise<void>;
  updateProfile: (updates: OrganizationProfileUpdate) => Promise<void>;
}

const updateDocumentTitle = (profile: OrganizationProfile | null) => {
  if (profile?.name && document.title.includes('ProSync')) {
    const baseTitle = document.title.split(' • ')[0];
    if (baseTitle !== 'ProSync') {
      document.title = `${baseTitle} • ${profile.name} | ProSync`;
    } else {
      document.title = `${profile.name} | ProSync`;
    }
  }
};

export const useOrganizationStore = create<OrganizationState>((set, get) => ({
  profile: null,
  isLoading: false,
  error: null,

  fetchProfile: async () => {
    set({ isLoading: true, error: null });
    try {
      const profile = await getOrganizationProfile();
      set({ profile, isLoading: false });
      updateDocumentTitle(profile);
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
      updateDocumentTitle(newProfile);
    }

    try {
      const profile = await updateOrganizationProfile(updates);
      set({ profile });
      updateDocumentTitle(profile);
    } catch (error: any) {
      // Revert optimistic update
      if (currentProfile) {
        set({ profile: currentProfile, error: error.message || 'Failed to update organization profile' });
        updateDocumentTitle(currentProfile);
      } else {
        set({ error: error.message || 'Failed to update organization profile' });
      }
      throw error;
    }
  },
}));
