import axiosInstance from '../lib/axios';

export interface Invitation {
  id: number;
  email: string;
  role: string;
  expires_at: string;
  created_at: string;
  accepted_at: string | null;
  is_pending: boolean;
}

export interface InvitationDetail {
  id: number;
  organization_id: number;
  org_name: string;
  email: string;
  role: string;
  expires_at: string;
  accepted_at: string | null;
}

export const adminInviteUser = async (email: string, role: string): Promise<Invitation> => {
  const response = await axiosInstance.post('/invitations', { email, role });
  return response.data;
};

export const adminListInvitations = async (): Promise<Invitation[]> => {
  const response = await axiosInstance.get('/invitations');
  return response.data;
};

export const verifyInvitationToken = async (token: string): Promise<InvitationDetail> => {
  const response = await axiosInstance.get(`/invitations/verify/${token}`);
  return response.data;
};

export const acceptInvitation = async (
  token: string,
  password: string,
  confirm_password: string,
  first_name: string,
  last_name: string
): Promise<{ message: string }> => {
  const response = await axiosInstance.post('/invitations/accept', {
    token,
    password,
    confirm_password,
    first_name,
    last_name,
  });
  return response.data;
};
