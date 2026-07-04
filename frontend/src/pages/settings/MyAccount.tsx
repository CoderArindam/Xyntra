import React, { useState, useRef, useEffect } from 'react';
import { useAuthStore } from '../../store/authStore';
import { updateProfile, uploadAvatar, deleteAvatar } from '../../api/usersApi';
import { UserAvatar } from '../../components/common/UserAvatar';
import { formatUserName } from '../../utils/userHelpers';
import toast from 'react-hot-toast';
import { Camera, Save, Loader2, Trash2 } from 'lucide-react';

export const MyAccount: React.FC = () => {
  const { user, updateUserLocally } = useAuthStore();
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Profile Form State
  const [firstName, setFirstName] = useState(user?.first_name || '');
  const [lastName, setLastName] = useState(user?.last_name || '');
  const [isSavingProfile, setIsSavingProfile] = useState(false);
  

  // Avatar Upload State
  const [isUploading, setIsUploading] = useState(false);

  // Unsaved changes detection
  const hasProfileChanges = firstName !== (user?.first_name || '') || lastName !== (user?.last_name || '');

  // Reset form when user changes (edge case if rehydrated)
  useEffect(() => {
    setFirstName(user?.first_name || '');
    setLastName(user?.last_name || '');
  }, [user]);

  const handleProfileSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!hasProfileChanges) return;

    try {
      setIsSavingProfile(true);
      const updatedUser = await updateProfile({
        first_name: firstName,
        last_name: lastName
      });
      
      updateUserLocally({
        first_name: updatedUser.first_name || undefined,
        last_name: updatedUser.last_name || undefined
      });
      
      toast.success('Profile updated successfully');
    } catch (error: any) {
      toast.error(error.message || 'Failed to update profile');
    } finally {
      setIsSavingProfile(false);
    }
  };


  const handleAvatarUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith('image/')) {
      toast.error('Please upload a valid image file');
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      toast.error('Image size must be less than 5MB');
      return;
    }

    try {
      setIsUploading(true);
      const avatar_url = await uploadAvatar(file);
      updateUserLocally({ avatar_url });
      toast.success('Avatar updated successfully');
    } catch (error: any) {
      toast.error('Failed to upload avatar');
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleRemoveAvatar = async () => {
    try {
      setIsUploading(true);
      await deleteAvatar();
      updateUserLocally({ avatar_url: undefined });
      toast.success('Avatar removed successfully');
    } catch (error: any) {
      toast.error('Failed to remove avatar');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="max-w-2xl animate-in fade-in duration-300">
      <div className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight text-brand-text mb-2">My Account</h1>
        <p className="text-sm text-brand-text-muted">Manage your personal profile and security preferences.</p>
      </div>

      {/* Profile Section */}
      <div className="bg-brand-surface border border-brand-border rounded-xl shadow-sm overflow-hidden mb-8">
        <div className="p-6 border-b border-brand-border">
          <h2 className="text-lg font-semibold text-brand-text mb-1">Profile Information</h2>
          <p className="text-sm text-brand-text-muted">Update your photo and personal details here.</p>
        </div>

        <div className="p-6">
          <div className="flex items-start gap-8 mb-8">
            <div className="relative group">
              <UserAvatar user={user} size="xl" className="shadow-sm" />
              <button 
                onClick={() => fileInputRef.current?.click()}
                disabled={isUploading}
                className="absolute -bottom-2 -right-2 w-8 h-8 bg-brand-surface border border-brand-border rounded-full flex items-center justify-center text-brand-text-muted hover:text-brand-text shadow-sm transition-colors"
                title="Change Avatar"
              >
                {isUploading ? <Loader2 size={14} className="animate-spin" /> : <Camera size={14} />}
              </button>
              <input 
                type="file"
                ref={fileInputRef}
                className="hidden"
                accept="image/png, image/jpeg, image/gif, image/webp"
                onChange={handleAvatarUpload}
              />
            </div>
            
            <div className="pt-2">
              <p className="text-sm font-medium text-brand-text mb-1">Display Name Preview</p>
              <div className="text-xl font-bold text-brand-text">
                {formatUserName({ first_name: firstName, last_name: lastName, email: user?.email })}
              </div>
              {user?.avatar_url && (
                <button
                  type="button"
                  onClick={handleRemoveAvatar}
                  disabled={isUploading}
                  className="mt-3 flex items-center gap-1.5 text-sm text-red-500 hover:text-red-600 transition-colors disabled:opacity-50"
                >
                  <Trash2 size={14} />
                  Remove profile picture
                </button>
              )}
            </div>
          </div>

          <form onSubmit={handleProfileSubmit} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-brand-text mb-1">First Name</label>
                <input 
                  type="text" 
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                  className="w-full bg-brand-surface-low border border-brand-border rounded-md px-3 py-2 text-sm text-brand-text focus:outline-none focus:ring-1 focus:ring-brand-primary focus:border-brand-primary transition-colors"
                  placeholder="John"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-brand-text mb-1">Last Name</label>
                <input 
                  type="text" 
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                  className="w-full bg-brand-surface-low border border-brand-border rounded-md px-3 py-2 text-sm text-brand-text focus:outline-none focus:ring-1 focus:ring-brand-primary focus:border-brand-primary transition-colors"
                  placeholder="Doe"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-brand-text mb-1">Email</label>
              <input 
                type="text" 
                value={user?.email || ''}
                readOnly
                disabled
                className="w-full bg-brand-surface-low border border-brand-border rounded-md px-3 py-2 text-sm text-brand-text-muted opacity-70 cursor-not-allowed"
              />
              <p className="text-xs text-brand-text-muted mt-1">Your email address cannot be changed right now.</p>
            </div>

            <div className="pt-4 flex items-center justify-end border-t border-brand-border mt-6 gap-3">
              {hasProfileChanges && (
                <button
                  type="button"
                  onClick={() => {
                    setFirstName(user?.first_name || '');
                    setLastName(user?.last_name || '');
                  }}
                  className="px-4 py-2 text-sm font-medium text-brand-text-muted hover:text-brand-text transition-colors"
                >
                  Discard
                </button>
              )}
              <button
                type="submit"
                disabled={!hasProfileChanges || isSavingProfile}
                className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-md transition-all ${
                  hasProfileChanges 
                    ? 'bg-brand-primary text-white hover:bg-brand-primary/90 shadow-sm' 
                    : 'bg-brand-surface-low text-brand-text-muted border border-brand-border cursor-not-allowed'
                }`}
              >
                {isSavingProfile ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
                Save Changes
              </button>
            </div>
          </form>
        </div>
      </div>

    </div>
  );
};

export default MyAccount;
