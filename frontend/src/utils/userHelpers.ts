export interface BaseUser {
  first_name?: string | null;
  last_name?: string | null;
  email?: string | null;
}

/**
 * Standardized function to format a user's display name.
 * Hierarchy: Full Name -> First Name -> Email -> Fallback
 */
export const formatUserName = (user: BaseUser | null | undefined, fallback: string = 'Unknown User'): string => {
  if (!user) return fallback;
  
  if (user.first_name && user.last_name) {
    return `${user.first_name} ${user.last_name}`.trim();
  }
  
  if (user.first_name) {
    return user.first_name;
  }
  
  if (user.email) {
    return user.email;
  }
  
  return fallback;
};

/**
 * Get the initials for a user's avatar.
 * Up to 2 characters (First initial of first name + First initial of last name).
 */
export const getInitials = (user: BaseUser | null | undefined): string => {
  if (!user) return '?';
  
  if (user.first_name && user.last_name) {
    return `${user.first_name[0]}${user.last_name[0]}`.toUpperCase();
  }
  
  if (user.first_name) {
    return user.first_name[0].toUpperCase();
  }
  
  if (user.email) {
    return user.email[0].toUpperCase();
  }
  
  return '?';
};
