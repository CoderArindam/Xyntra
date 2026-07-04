import api from './axios';

export interface OrganizationProfile {
  id: number;
  name: string;
  logo_url: string | null;
  website: string | null;
  description: string | null;
  industry: string | null;
  company_size: string | null;
  created_at: string;
  owner_name: string | null;
  owner_email: string | null;
  members_count: number;
  projects_count: number;
}

export interface OrganizationProfileUpdate {
  name?: string;
  logo_url?: string | null;
  website?: string | null;
  description?: string | null;
  industry?: string | null;
  company_size?: string | null;
}

export const getOrganizationProfile = async (): Promise<OrganizationProfile> => {
  const response = await api.get('/organization/profile');
  return response.data;
};

export const uploadOrganizationLogo = async (file: File): Promise<{ logo_url: string }> => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post('/organization/logo', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

export const updateOrganizationProfile = async (updates: OrganizationProfileUpdate): Promise<OrganizationProfile> => {
  const response = await api.patch('/organization/profile', updates);
  return response.data;
};
