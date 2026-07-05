export const PROJECT_COLORS: Record<string, string> = {
  blue: 'bg-blue-500',
  indigo: 'bg-indigo-500',
  emerald: 'bg-emerald-500',
  amber: 'bg-amber-500',
  rose: 'bg-rose-500',
  orange: 'bg-orange-500',
  violet: 'bg-violet-500',
  gray: 'bg-gray-500',
};

export const PROJECT_GRADIENTS: Record<string, string> = {
  blue: 'bg-gradient-to-br from-blue-400 to-indigo-600',
  purple: 'bg-gradient-to-br from-purple-400 to-indigo-600',
  emerald: 'bg-gradient-to-br from-emerald-400 to-teal-600',
  orange: 'bg-gradient-to-br from-orange-400 to-rose-600',
  gray: 'bg-gradient-to-br from-gray-300 to-gray-600',
};

export const getProjectColorClass = (color?: string | null) => {
  return color && PROJECT_COLORS[color] ? PROJECT_COLORS[color] : 'bg-brand-primary';
};

export const getProjectGradientClass = (gradient?: string | null) => {
  return gradient && PROJECT_GRADIENTS[gradient] ? PROJECT_GRADIENTS[gradient] : 'bg-brand-surface-hover';
};
