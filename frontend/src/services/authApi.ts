import api from '../lib/axios';

export const registerOrganization = async (org_name: string, email: string, password: string, first_name: string, last_name: string) => {
  const response = await api.post('/auth/register', { org_name, email, password, first_name, last_name });
  return response.data;
};

export const loginUser = async (email: string, password: string) => {
  const response = await api.post('/auth/login', { email, password });
  return response.data;
};

export const logoutUser = async () => {
  const response = await api.post('/auth/logout');
  return response.data;
};

export const getMe = async () => {
  const response = await api.get('/auth/me');
  return response.data;
};

export const getSessions = async () => {
  const response = await api.get('/auth/sessions');
  return response.data;
};

export const signOutOtherSessions = async () => {
  const response = await api.delete('/auth/sessions/other');
  return response.data;
};

export const getSecurityEvents = async () => {
  const response = await api.get('/auth/security-events');
  return response.data;
};

export const getPasswordPolicy = async () => {
  const response = await api.get('/auth/password-policy');
  return response.data;
};
