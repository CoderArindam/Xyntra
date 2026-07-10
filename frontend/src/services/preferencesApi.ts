import api from '../lib/axios';

export type ThemeType = 'light' | 'dark' | 'system';

export interface UserPreferences {
  id: number;
  user_id: number;
  theme: ThemeType;
  accent_color: string;
  sidebar_theme: string;
  sidebar_collapsed: boolean;
  created_at: string;
  updated_at: string;
}

export interface UserPreferencesUpdate {
  theme?: ThemeType;
  accent_color?: string;
  sidebar_theme?: string;
  sidebar_collapsed?: boolean;
}

export const getPreferences = async (): Promise<UserPreferences> => {
  const response = await api.get(`/users/me/preferences?t=${new Date().getTime()}`);
  return response.data;
};

export const updatePreferences = async (updates: UserPreferencesUpdate): Promise<UserPreferences> => {
  const response = await api.patch('/users/me/preferences', updates);
  return response.data;
};
