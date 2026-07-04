import React, { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { verifyInvitationToken, acceptInvitation, type InvitationDetail } from "../api/invitationsApi";
import { LayoutGrid, Eye, EyeOff, Loader2, AlertTriangle, CheckCircle2 } from "lucide-react";
import toast from "react-hot-toast";

export const AcceptInvitation: React.FC = () => {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token");
  const navigate = useNavigate();

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [invitation, setInvitation] = useState<InvitationDetail | null>(null);

  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);

  useEffect(() => {
    if (!token) {
      setError("No invitation token provided.");
      setIsLoading(false);
      return;
    }

    const verify = async () => {
      try {
        const data = await verifyInvitationToken(token);
        setInvitation(data);
      } catch (err: any) {
        setError(err.message || "Invalid or expired invitation token.");
      } finally {
        setIsLoading(false);
      }
    };

    verify();
  }, [token]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password !== confirmPassword) {
      toast.error("Passwords do not match");
      return;
    }
    if (password.length < 8) {
      toast.error("Password must be at least 8 characters long");
      return;
    }
    if (!token) return;

    setIsSubmitting(true);
    try {
      await acceptInvitation(token, password, confirmPassword, firstName, lastName);
      setIsSuccess(true);
      toast.success("Account created successfully");
      setTimeout(() => navigate("/login"), 3000);
    } catch (err: any) {
      toast.error(err.message || "Failed to accept invitation");
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-brand-bg">
        <Loader2 className="animate-spin text-brand-primary" size={48} />
      </div>
    );
  }

  if (error || !invitation) {
    return (
      <div className="w-full max-w-[440px] px-4 mx-auto flex items-center justify-center min-h-screen">
        <div className="w-full bg-brand-surface border border-brand-border rounded-xl shadow-md p-8 text-center flex flex-col items-center">
          <div className="w-16 h-16 rounded-full bg-red-500/10 text-red-500 flex items-center justify-center mb-4">
            <AlertTriangle size={32} />
          </div>
          <h2 className="text-xl font-bold text-brand-text mb-2">Invalid Invitation</h2>
          <p className="text-sm text-brand-text-muted mb-6">{error}</p>
          <button
            onClick={() => navigate("/login")}
            className="w-full bg-brand-surface-low hover:bg-brand-border text-brand-text font-medium text-sm rounded-lg py-2.5 px-4 transition-colors"
          >
            Return to Login
          </button>
        </div>
      </div>
    );
  }

  if (isSuccess) {
    return (
      <div className="w-full max-w-[440px] px-4 mx-auto flex items-center justify-center min-h-screen">
        <div className="w-full bg-brand-surface border border-brand-border rounded-xl shadow-md p-8 text-center flex flex-col items-center">
          <div className="w-16 h-16 rounded-full bg-green-500/10 text-green-500 flex items-center justify-center mb-4">
            <CheckCircle2 size={32} />
          </div>
          <h2 className="text-xl font-bold text-brand-text mb-2">Account Ready!</h2>
          <p className="text-sm text-brand-text-muted mb-6">
            Your account has been created successfully. You will be redirected to the login page momentarily.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full max-w-[480px] px-4 mx-auto flex items-center justify-center min-h-screen">
      <div className="w-full bg-brand-surface border border-brand-border rounded-xl shadow-md overflow-hidden flex flex-col p-6 md:p-8 transition-all duration-300">
        <div className="flex flex-col items-center mb-6 text-center">
          <div className="w-12 h-12 mb-4 bg-brand-surface-low rounded-lg flex items-center justify-center border border-brand-outline-variant text-brand-primary">
            <LayoutGrid size={24} className="stroke-[2]" />
          </div>
          <h1 className="text-2xl font-semibold tracking-tight text-brand-text mb-2">
            Accept Invitation
          </h1>
          <p className="text-sm text-brand-text-muted max-w-[320px]">
            You've been invited to join <span className="font-semibold text-brand-text">{invitation.org_name}</span>. Set a password to activate your account.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-semibold text-brand-text-muted">Email Address (Locked)</label>
            <input
              type="email"
              value={invitation.email}
              disabled
              className="w-full bg-brand-surface-low border border-brand-outline-variant text-brand-text-muted text-sm rounded px-3 py-2 cursor-not-allowed"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-semibold text-brand-text-muted">Role (Locked)</label>
            <input
              type="text"
              value={invitation.role}
              disabled
              className="w-full bg-brand-surface-low border border-brand-outline-variant text-brand-text-muted text-sm rounded px-3 py-2 cursor-not-allowed"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-semibold text-brand-text-muted">First Name</label>
            <input
              type="text"
              value={firstName}
              onChange={(e) => setFirstName(e.target.value)}
              required
              placeholder="e.g., Alex"
              className="w-full bg-brand-surface border border-brand-outline-variant text-brand-text text-sm rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-primary focus:border-brand-primary transition-colors placeholder:text-brand-outline"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-semibold text-brand-text-muted">Last Name</label>
            <input
              type="text"
              value={lastName}
              onChange={(e) => setLastName(e.target.value)}
              required
              placeholder="e.g., Doe"
              className="w-full bg-brand-surface border border-brand-outline-variant text-brand-text text-sm rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-primary focus:border-brand-primary transition-colors placeholder:text-brand-outline"
            />
          </div>

          <div className="flex flex-col gap-1.5 relative mt-2">
            <label className="text-xs font-semibold text-brand-text-muted">Password</label>
            <div className="relative">
              <input
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                placeholder="••••••••"
                className="w-full bg-brand-surface border border-brand-outline-variant text-brand-text text-sm rounded px-3 py-2 pr-10 focus:outline-none focus:ring-2 focus:ring-brand-primary focus:border-brand-primary transition-colors placeholder:text-brand-outline"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-brand-text-muted hover:text-brand-primary transition"
              >
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          <div className="flex flex-col gap-1.5 relative">
            <label className="text-xs font-semibold text-brand-text-muted">Confirm Password</label>
            <div className="relative">
              <input
                type={showPassword ? "text" : "password"}
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                placeholder="••••••••"
                className="w-full bg-brand-surface border border-brand-outline-variant text-brand-text text-sm rounded px-3 py-2 pr-10 focus:outline-none focus:ring-2 focus:ring-brand-primary focus:border-brand-primary transition-colors placeholder:text-brand-outline"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={isSubmitting || !password || !confirmPassword || !firstName || !lastName}
            className="mt-4 w-full bg-brand-primary hover:bg-brand-primary-hover text-white font-medium text-sm rounded-lg py-2.5 px-4 flex items-center justify-center gap-2 transition-colors duration-300 shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSubmitting && <Loader2 size={16} className="animate-spin" />}
            {isSubmitting ? "Activating Account..." : "Activate Account"}
          </button>
        </form>
      </div>
    </div>
  );
};

export default AcceptInvitation;
