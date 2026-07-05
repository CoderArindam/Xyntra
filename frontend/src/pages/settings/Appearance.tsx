import React, { useEffect } from 'react';
import { Palette, Monitor, Moon, Sun, CheckCircle } from 'lucide-react';
import { usePreferencesStore } from '../../store/preferencesStore';
import type { ThemeType } from '../../api/preferences';
import toast from 'react-hot-toast';
import { usePageTitle } from '../../hooks/usePageTitle';

const Appearance: React.FC = () => {
  usePageTitle('Appearance');
  const { preferences, fetchPreferences, updatePreferences, isLoading } = usePreferencesStore();

  useEffect(() => {
    if (!preferences) {
      fetchPreferences();
    }
  }, [preferences, fetchPreferences]);

  const handleThemeChange = async (theme: ThemeType) => {
    try {
      await updatePreferences({ theme });
    } catch (e) {
      toast.error('Failed to update theme');
    }
  };

  const handleAccentChange = async (accent_color: string) => {
    try {
      await updatePreferences({ accent_color });
    } catch (e) {
      toast.error('Failed to update accent color');
    }
  };

  const handleSidebarChange = async (sidebar_theme: string) => {
    try {
      await updatePreferences({ sidebar_theme });
    } catch (e) {
      toast.error('Failed to update sidebar appearance');
    }
  };

  const currentTheme = preferences?.theme || 'system';
  const currentAccent = preferences?.accent_color || 'blue';
  const currentSidebar = preferences?.sidebar_theme || 'default';

  const accents = [
    { id: 'blue', color: 'bg-blue-600', name: 'Blue' },
    { id: 'indigo', color: 'bg-indigo-600', name: 'Indigo' },
    { id: 'emerald', color: 'bg-emerald-500', name: 'Emerald' },
    { id: 'rose', color: 'bg-rose-500', name: 'Rose' },
    { id: 'amber', color: 'bg-amber-500', name: 'Amber' },
  ];

  const sidebars = [
    { id: 'default', name: 'Default' },
    { id: 'tinted', name: 'Tinted' },
    { id: 'dark', name: 'Dark' },
  ];

  return (
    <div className="max-w-4xl space-y-8 animate-in fade-in duration-300">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-brand-text flex items-center gap-2">
          <Palette className="text-brand-primary" size={24} />
          Appearance
        </h1>
        <p className="mt-2 text-sm text-brand-text-muted">
          Customize how your workspace looks on your device.
        </p>
      </div>

      <div className="space-y-6">
        {/* Theme Settings */}
        <div className="bg-brand-surface shadow-sm border border-brand-border rounded-lg overflow-hidden">
          <div className="px-6 py-5 border-b border-brand-border">
            <h3 className="text-lg font-medium leading-6 text-brand-text">
              Theme Mode
            </h3>
            <p className="mt-1 text-sm text-brand-text-muted">
              Select your preferred color theme for the application.
            </p>
          </div>
          
          <div className="p-6">
            {isLoading && !preferences ? (
               <div className="animate-pulse flex space-x-4">
                 <div className="h-24 bg-brand-surface-high rounded-lg w-1/3"></div>
                 <div className="h-24 bg-brand-surface-high rounded-lg w-1/3"></div>
                 <div className="h-24 bg-brand-surface-high rounded-lg w-1/3"></div>
               </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* Light */}
                <div 
                  className={`relative flex flex-col items-center p-4 rounded-xl border-2 cursor-pointer transition-all ${
                    currentTheme === 'light' 
                      ? 'border-brand-primary bg-[var(--primary)]/10' 
                      : 'border-brand-border hover:border-brand-outline-variant'
                  }`}
                  onClick={() => handleThemeChange('light')}
                >
                  {currentTheme === 'light' && (
                    <div className="absolute top-3 right-3 text-brand-primary">
                      <CheckCircle className="w-5 h-5 fill-current" />
                    </div>
                  )}
                  <div className="p-3 bg-brand-surface-high rounded-full mb-3 text-brand-text">
                    <Sun className="w-6 h-6" />
                  </div>
                  <span className="font-medium text-brand-text">Light</span>
                </div>
                
                {/* Dark */}
                <div 
                  className={`relative flex flex-col items-center p-4 rounded-xl border-2 cursor-pointer transition-all ${
                    currentTheme === 'dark' 
                      ? 'border-brand-primary bg-[var(--primary)]/10' 
                      : 'border-brand-border hover:border-brand-outline-variant'
                  }`}
                  onClick={() => handleThemeChange('dark')}
                >
                  {currentTheme === 'dark' && (
                    <div className="absolute top-3 right-3 text-brand-primary">
                      <CheckCircle className="w-5 h-5 fill-current" />
                    </div>
                  )}
                  <div className="p-3 bg-gray-800 rounded-full mb-3 text-gray-300">
                    <Moon className="w-6 h-6" />
                  </div>
                  <span className="font-medium text-brand-text">Dark</span>
                </div>
                
                {/* System */}
                <div 
                  className={`relative flex flex-col items-center p-4 rounded-xl border-2 cursor-pointer transition-all ${
                    currentTheme === 'system' 
                      ? 'border-brand-primary bg-[var(--primary)]/10' 
                      : 'border-brand-border hover:border-brand-outline-variant'
                  }`}
                  onClick={() => handleThemeChange('system')}
                >
                  {currentTheme === 'system' && (
                    <div className="absolute top-3 right-3 text-brand-primary">
                      <CheckCircle className="w-5 h-5 fill-current" />
                    </div>
                  )}
                  <div className="p-3 bg-gradient-to-r from-gray-200 to-gray-800 dark:from-gray-600 dark:to-gray-800 rounded-full mb-3 text-white">
                    <Monitor className="w-6 h-6" />
                  </div>
                  <span className="font-medium text-brand-text">System</span>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Accent Color */}
        <div className="bg-brand-surface shadow-sm border border-brand-border rounded-lg overflow-hidden">
          <div className="px-6 py-5 border-b border-brand-border">
            <h3 className="text-lg font-medium leading-6 text-brand-text">
              Accent Color
            </h3>
            <p className="mt-1 text-sm text-brand-text-muted">
              Personalize your workspace with a custom accent color.
            </p>
          </div>
          <div className="p-6">
            <div className="flex gap-4">
              {accents.map((accent) => (
                <button
                  key={accent.id}
                  onClick={() => handleAccentChange(accent.id)}
                  className={`relative w-12 h-12 rounded-full flex items-center justify-center transition-transform hover:scale-110 ${accent.color} ${
                    currentAccent === accent.id ? 'ring-4 ring-offset-2 ring-brand-primary ring-offset-brand-surface' : ''
                  }`}
                  aria-label={`Select ${accent.name} accent`}
                >
                  {currentAccent === accent.id && (
                    <CheckCircle className="w-6 h-6 text-white" />
                  )}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Sidebar Appearance */}
        <div className="bg-brand-surface shadow-sm border border-brand-border rounded-lg overflow-hidden">
          <div className="px-6 py-5 border-b border-brand-border">
            <h3 className="text-lg font-medium leading-6 text-brand-text">
              Sidebar Appearance
            </h3>
            <p className="mt-1 text-sm text-brand-text-muted">
              Choose how the sidebar navigation looks.
            </p>
          </div>
          <div className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {sidebars.map((sidebar) => (
                <div
                  key={sidebar.id}
                  onClick={() => handleSidebarChange(sidebar.id)}
                  className={`relative flex items-center justify-center p-4 rounded-xl border-2 cursor-pointer transition-all ${
                    currentSidebar === sidebar.id
                      ? 'border-brand-primary bg-[var(--primary)]/10'
                      : 'border-brand-border hover:border-brand-outline-variant'
                  }`}
                >
                  {currentSidebar === sidebar.id && (
                    <div className="absolute top-3 right-3 text-brand-primary">
                      <CheckCircle className="w-5 h-5 fill-current" />
                    </div>
                  )}
                  <span className="font-medium text-brand-text">{sidebar.name}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

      </div>
    </div>
  );
};

export default Appearance;
