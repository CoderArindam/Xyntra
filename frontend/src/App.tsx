import React, { useEffect } from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import ProtectedRoute from "./routes/ProtectedRoute";
import AppLayout from "./components/layout/AppLayout";
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import LandingPage from "./pages/LandingPage";
import Dashboard from "./pages/Dashboard";
import Board from "./pages/Board";
import MyWork from "./pages/MyWork";
import AcceptInvitation from "./pages/AcceptInvitation";
import AdminLayout from "./pages/admin/AdminLayout";
import AdminDashboard from "./pages/admin/AdminDashboard";
import UsersManagement from "./pages/admin/UsersManagement";
import BoardPermissions from "./pages/admin/BoardPermissions";
import SettingsLayout from "./layouts/SettingsLayout";
import MyAccount from "./pages/settings/MyAccount";
import Security from "./pages/settings/Security";
import Organization from "./pages/settings/Organization";
import Appearance from "./pages/settings/Appearance";
import PlaceholderSetting from "./pages/settings/PlaceholderSetting";
import { ProjectSettingsLayout } from "./pages/boards/ProjectSettingsLayout";
import { ProjectSettingsPage } from "./pages/boards/ProjectSettingsPage";
import {
  Bell,
  Key,
  CreditCard,
  Keyboard,
  Boxes,
  Users,
  GitMerge,
  Tag,
  Zap,
  Puzzle,
} from "lucide-react";
import { Toaster } from "react-hot-toast";
import { useAuthStore } from "./store/authStore";
import { usePreferencesStore } from "./store/preferencesStore";
import { useOrganizationStore } from "./store/organizationStore";

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
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />
          <Route path="/accept-invitation" element={<AcceptInvitation />} />

          <Route element={<ProtectedRoute />}>
            <Route element={<AppLayout />}>
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/my-work" element={<MyWork />} />
              <Route path="/board/:id" element={<Board />} />
              <Route
                path="/board/:boardId/settings"
                element={<ProjectSettingsLayout />}
              >
                <Route index element={<ProjectSettingsPage />} />
                <Route
                  path="members"
                  element={
                    <PlaceholderSetting
                      title="Members"
                      description="Manage project access."
                      Icon={Users}
                    />
                  }
                />
                <Route
                  path="workflow"
                  element={
                    <PlaceholderSetting
                      title="Workflow"
                      description="Customize project statuses and transitions."
                      Icon={GitMerge}
                    />
                  }
                />
                <Route
                  path="labels"
                  element={
                    <PlaceholderSetting
                      title="Labels"
                      description="Manage project tags and labels."
                      Icon={Tag}
                    />
                  }
                />
                <Route
                  path="automation"
                  element={
                    <PlaceholderSetting
                      title="Automation"
                      description="Create rules to automate repetitive tasks."
                      Icon={Zap}
                    />
                  }
                />
                <Route
                  path="integrations"
                  element={
                    <PlaceholderSetting
                      title="Integrations"
                      description="Connect this project to other tools."
                      Icon={Puzzle}
                    />
                  }
                />
              </Route>
              {/* Settings Routes */}
              <Route path="/settings" element={<SettingsLayout />}>
                <Route path="account" element={<MyAccount />} />
                <Route path="organization" element={<Organization />} />
                <Route path="appearance" element={<Appearance />} />
                <Route
                  path="notifications"
                  element={
                    <PlaceholderSetting
                      title="Notifications"
                      description="Choose what we notify you about and how."
                      Icon={Bell}
                    />
                  }
                />
                <Route path="security" element={<Security />} />
                <Route
                  path="integrations"
                  element={
                    <PlaceholderSetting
                      title="Integrations"
                      description="Connect ProSync with your favorite tools."
                      Icon={Boxes}
                    />
                  }
                />
                <Route
                  path="keyboard-shortcuts"
                  element={
                    <PlaceholderSetting
                      title="Keyboard Shortcuts"
                      description="Work faster with keyboard shortcuts."
                      Icon={Keyboard}
                    />
                  }
                />
                <Route
                  path="api-keys"
                  element={
                    <PlaceholderSetting
                      title="API Keys"
                      description="Manage API tokens for custom integrations."
                      Icon={Key}
                    />
                  }
                />
                <Route
                  path="billing"
                  element={
                    <PlaceholderSetting
                      title="Billing"
                      description="Manage your subscription and billing details."
                      Icon={CreditCard}
                    />
                  }
                />
              </Route>

              <Route path="/admin" element={<AdminLayout />}>
                <Route index element={<AdminDashboard />} />
                <Route path="users" element={<UsersManagement />} />
                <Route path="boards" element={<BoardPermissions />} />
              </Route>
            </Route>
          </Route>
        </Routes>
      </Router>
    </>
  );
};

export default App;
