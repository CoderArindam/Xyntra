import React from 'react';
import { Routes, Route } from 'react-router-dom';
import ProtectedRoute from '../routes/ProtectedRoute';
import AppLayout from '../components/layout/AppLayout';

import Login from '../features/auth/Login';
import Signup from '../features/auth/Signup';
import LandingPage from '../features/auth/LandingPage';
import AcceptInvitation from '../features/auth/AcceptInvitation';

import DashboardView from '../features/dashboard/DashboardView';
import BoardPage from '../features/boards/BoardPage';
import MyWorkPage from '../features/my-work/MyWorkPage';

import AdminLayout from '../features/admin/AdminLayout';
import AdminDashboard from '../features/admin/AdminDashboard';
import UsersManagement from '../features/admin/UsersManagement';
import BoardPermissions from '../features/admin/BoardPermissions';

import SettingsLayout from '../components/layout/SettingsLayout';
import MyAccount from '../features/settings/MyAccount';
import Security from '../features/settings/Security';
import Organization from '../features/settings/Organization';
import Appearance from '../features/settings/Appearance';
import NotificationSettings from '../features/settings/NotificationSettings';
import PlaceholderSetting from '../features/settings/PlaceholderSetting';

import { ProjectSettingsLayout } from '../features/projects/ProjectSettingsLayout';
import { ProjectSettingsPage } from '../features/projects/ProjectSettingsPage';

import {
  Key,
  CreditCard,
  Keyboard,
  Boxes,
  Users,
  GitMerge,
  Tag,
  Zap,
  Puzzle,
} from 'lucide-react';

import RequireRole from '../routes/RequireRole';
import ProposalQueueView from '../features/proposals/components/ProposalQueueView';

export const AppRoutes: React.FC = () => {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<Login />} />
      <Route path="/signup" element={<Signup />} />
      <Route path="/accept-invitation" element={<AcceptInvitation />} />

      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route path="/dashboard" element={<DashboardView />} />
          <Route path="/my-work" element={<MyWorkPage />} />
          <Route path="/board/:id" element={<BoardPage />} />


          {/* Role-gated proposal review queue routes */}
          <Route element={<RequireRole allowedRoles={['SUPER_ADMIN', 'MANAGER']} />}>
            <Route path="/meetings/:sessionId/proposals" element={<ProposalQueueView />} />
            <Route path="/meeting/:sessionId/proposals" element={<ProposalQueueView />} />
          </Route>

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
            <Route path="notifications" element={<NotificationSettings />} />
            <Route path="security" element={<Security />} />
            <Route
              path="integrations"
              element={
                <PlaceholderSetting
                  title="Integrations"
                  description="Connect KAIO with your favorite tools."
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
  );
};
