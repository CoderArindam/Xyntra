export interface UserLike {
  role?: string | null;
}

export function isSuperAdmin(user?: UserLike | null): boolean {
  if (!user || !user.role) return false;
  const role = user.role.toUpperCase();
  return role === 'SUPER_ADMIN' || role === 'SUPERADMIN';
}

export function isManagerOrAdmin(user?: UserLike | null): boolean {
  if (!user || !user.role) return false;
  const role = user.role.toUpperCase();
  return role === 'SUPER_ADMIN' || role === 'SUPERADMIN' || role === 'MANAGER';
}
