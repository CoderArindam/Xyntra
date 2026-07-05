import React, { useState, useEffect } from "react";
import {
  Building2,
  Save,
  ExternalLink,
  Image as ImageIcon,
  Users,
  Calendar,
  Hash,
  ArrowRight,
  ShieldAlert,
  Trash2,
} from "lucide-react";
import { useAuthStore } from "../../store/authStore";
import { useOrganizationStore } from "../../store/organizationStore";
import { uploadOrganizationLogo } from "../../api/organizationApi";
import WorkspaceLogo from "../../components/common/WorkspaceLogo";
import toast from "react-hot-toast";
import { useRef } from "react";
import { usePageTitle } from "../../hooks/usePageTitle";

const INDUSTRIES = [
  "Technology",
  "Education",
  "Finance",
  "Healthcare",
  "Marketing",
  "Manufacturing",
  "Agency",
  "Startup",
  "Non-Profit",
  "Other",
];

const COMPANY_SIZES = ["1–10", "11–50", "51–200", "201–500", "500+"];

export const Organization: React.FC = () => {
  const { user } = useAuthStore();
  const { profile, updateProfile } = useOrganizationStore();

  usePageTitle("Workspace Settings");

  const [formData, setFormData] = useState({
    name: "",
    logo_url: "",
    website: "",
    industry: "",
    company_size: "",
    description: "",
  });

  const [isSaving, setIsSaving] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (profile) {
      setFormData({
        name: profile.name || "",
        logo_url: profile.logo_url || "",
        website: profile.website || "",
        industry: profile.industry || "",
        company_size: profile.company_size || "",
        description: profile.description || "",
      });
    }
  }, [profile]);

  if (user?.role !== "SUPER_ADMIN") {
    return (
      <div className="flex items-center justify-center h-full min-h-[400px]">
        <div className="text-center">
          <div className="w-16 h-16 bg-red-100 dark:bg-red-900/20 text-red-600 dark:text-red-500 rounded-full flex items-center justify-center mx-auto mb-4">
            <ShieldAlert size={32} />
          </div>
          <h2 className="text-xl font-bold text-brand-text mb-2">
            Access Denied
          </h2>
          <p className="text-brand-text-muted">
            Only Super Admins can manage Workspace settings.
          </p>
        </div>
      </div>
    );
  }

  const handleChange = (
    e: React.ChangeEvent<
      HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement
    >,
  ) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (file.size > 2 * 1024 * 1024) {
      toast.error("File size must be less than 2MB");
      return;
    }

    setIsUploading(true);
    try {
      const { logo_url } = await uploadOrganizationLogo(file);
      setFormData((prev) => ({ ...prev, logo_url }));
      toast.success(
        "Logo uploaded successfully. Don't forget to save changes.",
      );
    } catch (err: any) {
      toast.error(err.message || "Failed to upload logo");
    } finally {
      setIsUploading(false);
      // Reset input so the same file can be uploaded again if needed
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const handleSave = async () => {
    if (
      !formData.name ||
      formData.name.length < 3 ||
      formData.name.length > 60
    ) {
      toast.error("Workspace Name must be between 3 and 60 characters");
      return;
    }

    if (
      formData.website &&
      !formData.website.startsWith("http://") &&
      !formData.website.startsWith("https://")
    ) {
      toast.error("Website must be a valid HTTPS URL");
      return;
    }

    if (formData.description && formData.description.length > 500) {
      toast.error("Description must be 500 characters or less");
      return;
    }

    setIsSaving(true);
    try {
      await updateProfile({
        name: formData.name,
        logo_url: formData.logo_url || null,
        website: formData.website || null,
        industry: formData.industry || null,
        company_size: formData.company_size || null,
        description: formData.description || null,
      });
      toast.success("Workspace settings updated successfully");
    } catch (err) {
      // Error handled by store
    } finally {
      setIsSaving(false);
    }
  };

  // Determine if there are unsaved changes
  const hasChanges = profile
    ? formData.name !== (profile.name || "") ||
      formData.logo_url !== (profile.logo_url || "") ||
      formData.website !== (profile.website || "") ||
      formData.industry !== (profile.industry || "") ||
      formData.company_size !== (profile.company_size || "") ||
      formData.description !== (profile.description || "")
    : false;

  const displayLogoUrl = formData.logo_url;
  const displayName = formData.name || "Your Workspace";

  return (
    <div className="max-w-5xl animate-in fade-in duration-300">
      <div className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight text-brand-text flex items-center gap-2">
          <Building2 className="text-brand-primary" size={24} />
          Workspace Settings
        </h1>
        <p className="mt-2 text-sm text-brand-text-muted">
          Manage your workspace identity, branding, and fundamental settings.
        </p>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
        <div className="xl:col-span-2 space-y-8">
          {/* Workspace Profile Form */}
          <div className="bg-brand-surface border border-brand-border rounded-xl shadow-sm overflow-hidden">
            <div className="px-6 py-5 border-b border-brand-border">
              <h3 className="text-lg font-semibold text-brand-text">
                Workspace Profile
              </h3>
              <p className="text-sm text-brand-text-muted mt-1">
                Basic information about your organization.
              </p>
            </div>

            <div className="p-6 space-y-6">
              {/* Logo Upload Simulation */}
              <div>
                <label className="block text-sm font-medium text-brand-text mb-2">
                  Workspace Logo
                </label>
                <div className="flex items-start gap-6">
                  <WorkspaceLogo
                    name={displayName}
                    logoUrl={displayLogoUrl}
                    size="xl"
                  />
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <input
                        type="file"
                        accept="image/png, image/jpeg"
                        className="hidden"
                        ref={fileInputRef}
                        onChange={handleFileChange}
                      />
                      <button
                        type="button"
                        onClick={() => fileInputRef.current?.click()}
                        disabled={isUploading}
                        className="px-4 py-2 bg-brand-surface-low border border-brand-border rounded-md text-sm font-medium text-brand-text hover:bg-brand-surface-high transition-colors flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        <ImageIcon size={16} />
                        {isUploading ? "Uploading..." : "Upload Image"}
                      </button>
                      <span className="text-xs text-brand-text-muted">
                        PNG/JPG. Max 2MB.
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="md:col-span-2">
                  <label
                    htmlFor="name"
                    className="block text-sm font-medium text-brand-text mb-1"
                  >
                    Workspace Name <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    id="name"
                    name="name"
                    required
                    minLength={3}
                    maxLength={60}
                    value={formData.name}
                    onChange={handleChange}
                    className="w-full px-3 py-2 bg-brand-bg border border-brand-border rounded-md text-sm text-brand-text focus:outline-none focus:ring-2 focus:ring-brand-primary/50"
                    placeholder="e.g. Acme Corporation"
                  />
                </div>

                <div className="md:col-span-2">
                  <label
                    htmlFor="website"
                    className="block text-sm font-medium text-brand-text mb-1"
                  >
                    Website URL
                  </label>
                  <input
                    type="url"
                    id="website"
                    name="website"
                    value={formData.website}
                    onChange={handleChange}
                    className="w-full px-3 py-2 bg-brand-bg border border-brand-border rounded-md text-sm text-brand-text focus:outline-none focus:ring-2 focus:ring-brand-primary/50"
                    placeholder="https://example.com"
                  />
                </div>

                <div>
                  <label
                    htmlFor="industry"
                    className="block text-sm font-medium text-brand-text mb-1"
                  >
                    Industry
                  </label>
                  <select
                    id="industry"
                    name="industry"
                    value={formData.industry}
                    onChange={handleChange}
                    className="w-full px-3 py-2 bg-brand-bg border border-brand-border rounded-md text-sm text-brand-text focus:outline-none focus:ring-2 focus:ring-brand-primary/50"
                  >
                    <option value="">Select an industry...</option>
                    {INDUSTRIES.map((ind) => (
                      <option key={ind} value={ind}>
                        {ind}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label
                    htmlFor="company_size"
                    className="block text-sm font-medium text-brand-text mb-1"
                  >
                    Company Size
                  </label>
                  <select
                    id="company_size"
                    name="company_size"
                    value={formData.company_size}
                    onChange={handleChange}
                    className="w-full px-3 py-2 bg-brand-bg border border-brand-border rounded-md text-sm text-brand-text focus:outline-none focus:ring-2 focus:ring-brand-primary/50"
                  >
                    <option value="">Select company size...</option>
                    {COMPANY_SIZES.map((size) => (
                      <option key={size} value={size}>
                        {size}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="md:col-span-2">
                  <label
                    htmlFor="description"
                    className="block text-sm font-medium text-brand-text mb-1"
                  >
                    Description
                  </label>
                  <textarea
                    id="description"
                    name="description"
                    rows={3}
                    maxLength={500}
                    value={formData.description}
                    onChange={handleChange}
                    className="w-full px-3 py-2 bg-brand-bg border border-brand-border rounded-md text-sm text-brand-text focus:outline-none focus:ring-2 focus:ring-brand-primary/50 resize-none"
                    placeholder="Tell us a little bit about your workspace..."
                  />
                  <div className="text-right text-xs text-brand-text-muted mt-1">
                    {formData.description.length}/500
                  </div>
                </div>
              </div>
            </div>
            <div className="px-6 py-4 bg-brand-surface-low border-t border-brand-border flex items-center justify-between">
              <span className="text-sm text-brand-text-muted">
                {hasChanges
                  ? "You have unsaved changes."
                  : "All changes saved."}
              </span>
              <button
                onClick={handleSave}
                disabled={!hasChanges || isSaving || !formData.name}
                className="px-6 py-2 bg-brand-primary text-white text-sm font-medium rounded-md hover:bg-brand-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                <Save size={16} />
                {isSaving ? "Saving..." : "Save Changes"}
              </button>
            </div>
          </div>

          {/* Danger Zone */}
          <div className="bg-brand-surface border border-red-200 dark:border-red-900/50 rounded-xl shadow-sm overflow-hidden">
            <div className="px-6 py-5 border-b border-red-200 dark:border-red-900/50">
              <h3 className="text-lg font-semibold text-red-600 dark:text-red-500">
                Danger Zone
              </h3>
              <p className="text-sm text-brand-text-muted mt-1">
                Irreversible and destructive actions.
              </p>
            </div>

            <div className="p-6 space-y-6">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="text-sm font-medium text-brand-text">
                    Transfer Workspace Ownership
                  </h4>
                  <p className="text-sm text-brand-text-muted mt-1">
                    Transfer this workspace to another member.
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <span className="px-2 py-1 bg-brand-surface-low text-xs font-semibold uppercase tracking-wider text-brand-text-muted rounded">
                    Coming Soon
                  </span>
                  <button
                    disabled
                    className="px-4 py-2 border border-brand-border text-brand-text-muted rounded-md text-sm font-medium cursor-not-allowed flex items-center gap-2"
                  >
                    <ArrowRight size={16} />
                    Transfer
                  </button>
                </div>
              </div>

              <div className="w-full h-px bg-brand-border" />

              <div className="flex items-center justify-between">
                <div>
                  <h4 className="text-sm font-medium text-brand-text">
                    Delete Workspace
                  </h4>
                  <p className="text-sm text-brand-text-muted mt-1">
                    Permanently delete all data, projects, and users.
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <span className="px-2 py-1 bg-brand-surface-low text-xs font-semibold uppercase tracking-wider text-brand-text-muted rounded">
                    Coming Soon
                  </span>
                  <button
                    disabled
                    className="px-4 py-2 border border-red-200 text-red-400 dark:border-red-900/50 dark:text-red-800 rounded-md text-sm font-medium cursor-not-allowed flex items-center gap-2"
                  >
                    <Trash2 size={16} />
                    Delete
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Sidebar - Previews & Stats */}
        <div className="space-y-6">
          {/* Read-only Stats */}
          {profile && (
            <div className="bg-brand-surface border border-brand-border rounded-xl shadow-sm p-6 space-y-4">
              <h3 className="text-sm font-semibold text-brand-text uppercase tracking-wider mb-4">
                Workspace Information
              </h3>

              <div className="flex items-center gap-3">
                <Hash size={16} className="text-brand-text-muted" />
                <div className="flex flex-col">
                  <span className="text-xs text-brand-text-muted">
                    Organization ID
                  </span>
                  <span className="text-sm font-medium text-brand-text font-mono">
                    ORG-{profile.id}
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <Calendar size={16} className="text-brand-text-muted" />
                <div className="flex flex-col">
                  <span className="text-xs text-brand-text-muted">
                    Created On
                  </span>
                  <span className="text-sm font-medium text-brand-text">
                    {new Date(profile.created_at).toLocaleDateString("en-US", {
                      year: "numeric",
                      month: "long",
                      day: "numeric",
                    })}
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <Users size={16} className="text-brand-text-muted" />
                <div className="flex flex-col">
                  <span className="text-xs text-brand-text-muted">Owner</span>
                  <span className="text-sm font-medium text-brand-text">
                    {profile.owner_name || profile.owner_email}
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4 mt-6 pt-4 border-t border-brand-border">
                <div className="text-center p-3 bg-brand-surface-low rounded-lg">
                  <span className="block text-2xl font-bold text-brand-text">
                    {profile.members_count}
                  </span>
                  <span className="block text-xs font-medium text-brand-text-muted uppercase tracking-wider mt-1">
                    Members
                  </span>
                </div>
                <div className="text-center p-3 bg-brand-surface-low rounded-lg">
                  <span className="block text-2xl font-bold text-brand-text">
                    {profile.projects_count}
                  </span>
                  <span className="block text-xs font-medium text-brand-text-muted uppercase tracking-wider mt-1">
                    Projects
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Live Preview */}
          <div className="bg-brand-surface border border-brand-border rounded-xl shadow-sm overflow-hidden sticky top-24">
            <div className="px-6 py-4 border-b border-brand-border bg-brand-surface-low">
              <h3 className="text-sm font-semibold text-brand-text flex items-center gap-2">
                <ExternalLink size={16} />
                Live Preview
              </h3>
            </div>

            <div className="p-6 space-y-8 bg-brand-bg">
              {/* Sidebar Preview */}
              <div>
                <p className="text-xs font-medium text-brand-text-muted uppercase tracking-wider mb-3">
                  Sidebar Appearance
                </p>
                <div className="p-4 border border-brand-border bg-brand-surface rounded-lg shadow-sm w-full max-w-[240px]">
                  <div className="flex items-center gap-3">
                    <WorkspaceLogo
                      name={displayName}
                      logoUrl={displayLogoUrl}
                      size="md"
                    />
                    <div className="flex flex-col truncate">
                      <span className="text-sm font-bold text-brand-text truncate">
                        {displayName}
                      </span>
                      <span className="text-[10px] text-brand-text-muted uppercase tracking-wide">
                        ProSync Workspace
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Browser Title Preview */}
              <div>
                <p className="text-xs font-medium text-brand-text-muted uppercase tracking-wider mb-3">
                  Browser Title
                </p>
                <div className="px-4 py-2 border border-brand-border bg-brand-surface rounded-t-lg shadow-sm text-sm text-brand-text truncate border-b-0 w-full max-w-[280px]">
                  Settings • {displayName} | ProSync
                </div>
                <div className="h-6 w-full max-w-[280px] bg-brand-surface-low border border-brand-border rounded-b-lg border-t-0 shadow-sm"></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Organization;
