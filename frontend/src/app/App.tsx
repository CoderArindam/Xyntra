import React, { useEffect } from 'react';
import { BrowserRouter as Router } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { useAuthStore } from '../store/authStore';
import { usePreferencesStore } from '../store/preferencesStore';
import { useOrganizationStore } from '../store/organizationStore';
import { AppRoutes } from './routes';

export const App: React.FC = () => {
  const { initAuth, isAuthenticated } = useAuthStore();
  const { fetchPreferences } = usePreferencesStore();
  const { fetchProfile } = useOrganizationStore();

  useEffect(() => {
    initAuth();
  }, [initAuth]);

  useEffect(() => {
    if (isAuthenticated) {
      fetchPreferences();
      fetchProfile();
    }
  }, [isAuthenticated, fetchPreferences, fetchProfile]);

  return (
    <>
      <Toaster
        position="bottom-left"
        toastOptions={{
          style: {
            padding: "16px 24px",
            borderRadius: "4px",
            fontSize: "15px",
            boxShadow: "0 8px 16px rgba(0,0,0,0.2)",
            maxWidth: "500px",
            color: "#fff",
          },
          success: {
            style: {
              background: "#0052CC", // Jira Blue
            },
          },
          error: {
            style: {
              background: "#DE350B", // Jira Red
            },
          },
        }}
      />
      <Router>
        <AppRoutes />
      </Router>
    </>
  );
};

export default App;
