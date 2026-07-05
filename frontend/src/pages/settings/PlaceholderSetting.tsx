import React from 'react';
import { usePageTitle } from '../../hooks/usePageTitle';

interface PlaceholderSettingProps {
  title: string;
  description: string;
  Icon: React.ElementType;
}

export const PlaceholderSetting: React.FC<PlaceholderSettingProps> = ({ title, description, Icon }) => {
  usePageTitle(title);

  return (
    <div className="flex flex-col h-full items-center justify-center text-center mt-20 animate-in fade-in duration-500">
      <div className="w-24 h-24 bg-brand-surface border border-brand-border rounded-2xl flex items-center justify-center mb-6 shadow-sm">
        <Icon size={48} className="text-brand-text-muted" />
      </div>
      <h2 className="text-2xl font-bold text-brand-text mb-3">{title} Settings</h2>
      <p className="text-brand-text-muted max-w-md mx-auto mb-8 text-sm leading-relaxed">
        {description}
      </p>
      
      <div className="inline-flex items-center justify-center px-4 py-2 bg-brand-surface-low border border-brand-border rounded-full text-xs font-semibold text-brand-text uppercase tracking-wider">
        Coming Soon
      </div>
    </div>
  );
};

export default PlaceholderSetting;
