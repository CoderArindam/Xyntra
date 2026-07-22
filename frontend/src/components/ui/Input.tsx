import React from 'react';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className = '', label, error, ...props }, ref) => {
    return (
      <div className="w-full">
        {label && (
          <label className="block text-xs font-medium text-brand-text-muted mb-1">
            {label}
          </label>
        )}
        <input
          ref={ref}
          className={`w-full bg-brand-surface border border-brand-border rounded-lg px-3 py-2 text-sm text-brand-text placeholder-brand-text-muted/50 focus:outline-none focus:border-brand-primary transition-colors disabled:opacity-50 ${
            error ? 'border-red-500' : ''
          } ${className}`}
          {...props}
        />
        {error && <p className="mt-1 text-xs text-red-400">{error}</p>}
      </div>
    );
  }
);

Input.displayName = 'Input';
export default Input;
