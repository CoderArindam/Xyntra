import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';
import { LayoutGrid, Eye, EyeOff, Loader2 } from 'lucide-react';
import toast from 'react-hot-toast';

export const Login: React.FC = () => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { login } = useAuthStore();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      await login(email, password);
      toast.success("Logged in successfully");
      navigate("/dashboard");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Login failed. Please check your credentials.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="w-full max-w-[440px] px-4 mx-auto flex items-center justify-center min-h-screen">
      <div className="w-full bg-brand-surface border border-brand-border rounded-xl shadow-md overflow-hidden flex flex-col p-6 md:p-8 transition-all duration-300">
        {/* Header Icon */}
        <div className="flex flex-col items-center mb-6 text-center">
          <div className="w-12 h-12 mb-4 bg-brand-surface-low rounded-lg flex items-center justify-center border border-brand-outline-variant text-brand-primary">
            <LayoutGrid size={24} className="stroke-[2]" />
          </div>

          <h1 className="text-2xl font-semibold tracking-tight text-brand-text mb-2">
            Welcome back
          </h1>

          <p className="text-sm text-brand-text-muted max-w-[280px]">
            Sign in to continue managing your projects with KAIO.
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          {/* Email */}
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-semibold text-brand-text-muted">
              Email Address
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              placeholder="alex@company.com"
              className="w-full bg-brand-surface border border-brand-outline-variant text-brand-text text-sm rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-primary focus:border-brand-primary transition-colors placeholder:text-brand-outline"
            />
          </div>

          {/* Password */}
          <div className="flex flex-col gap-1.5 relative">
            <label className="text-xs font-semibold text-brand-text-muted">
              Password
            </label>
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

          {/* Submit */}
          <button
            type="submit"
            disabled={isSubmitting}
            className="mt-3 w-full bg-brand-primary hover:bg-brand-primary-hover text-white font-medium text-sm rounded-lg py-2.5 px-4 flex items-center justify-center gap-2 transition-colors duration-300 shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSubmitting && <Loader2 size={16} className="animate-spin" />}
            {isSubmitting ? "Signing in..." : "Sign in"}
          </button>
        </form>

        <div className="mt-6 text-center">
          <p className="text-sm text-brand-text-muted">
            Don't have an account?{" "}
            <Link
              to="/signup"
              className="text-brand-primary hover:text-brand-primary-hover font-semibold text-xs transition-colors ml-1"
            >
              Sign up
            </Link>
          </p>
          <div className="mt-6">
            <span className="text-[10px] text-brand-text-muted uppercase tracking-wider font-semibold">Powered by KAIO</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;
