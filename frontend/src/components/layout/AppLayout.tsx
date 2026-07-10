import React, { useEffect } from 'react';
import { Outlet } from 'react-router-dom';

import { usePreferencesStore } from '../../store/preferencesStore';
import { useOrganizationStore } from '../../store/organizationStore';
import { useUiStore } from '../../store/uiStore';
import WorkspaceLoader from '../common/WorkspaceLoader';
import { updateFavicon } from '../../utils/favicon';

import ApplicationSidebar from './ApplicationSidebar';
import { AIButton } from '../../features/ai/components/AIButton';
import { AIPanel } from '../../features/ai/components/AIPanel';
import CreateProjectModal from '../../features/projects/components/CreateProjectModal';

export const AppLayout: React.FC = () => {
  
  const { profile, isLoading: isProfileLoading } = useOrganizationStore();
  const { isLoading: isPreferencesLoading } = usePreferencesStore();
  const { pageTitle } = useUiStore();

  // Document Title Logic
  useEffect(() => {
    const workspaceName = profile?.name || "Workspace";
    if (pageTitle) {
      document.title = `${pageTitle} · ${workspaceName} | KAIO`;
    } else {
      document.title = `${workspaceName} | KAIO`;
    }
  }, [pageTitle, profile?.name]);

  // Dynamic Favicon Logic
  useEffect(() => {
    if (profile) {
      updateFavicon(profile.name, profile.logo_url);
    }
  }, [profile?.name, profile?.logo_url]);

  // Bootstrap Flow / Loading Screen
  if (isProfileLoading || isPreferencesLoading || !profile) {
    return <WorkspaceLoader name={profile?.name} logoUrl={profile?.logo_url} />;
  }

  return (
    <div className="flex h-screen overflow-hidden bg-brand-bg text-brand-text">
      <ApplicationSidebar />
      <div className="flex-1 flex flex-col relative overflow-hidden min-w-0 md:pt-0 pt-16">
        <main className="flex-1 overflow-y-auto">
          <Outlet />
        </main>
      </div>
      <AIButton />
      <AIPanel />
      <CreateProjectModal />
    </div>
  );
};

export default AppLayout;
