import React from 'react';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className = '', variant = 'primary', size = 'md', disabled, children, ...props }, ref) => {
    const baseStyles = 'inline-flex items-center justify-center font-medium rounded-lg transition-colors cursor-pointer disabled:cursor-not-allowed disabled:opacity-50';
    
    const variantStyles = {
      primary: 'bg-brand-primary text-white hover:bg-brand-primary-hover',
      secondary: 'bg-brand-surface-low text-brand-text hover:bg-brand-surface-container',
      outline: 'border border-brand-border text-brand-text hover:bg-brand-surface-low',
      ghost: 'text-brand-text-muted hover:text-brand-text hover:bg-brand-surface-low',
      danger: 'bg-brand-error text-white hover:bg-red-700',
    };

    const sizeStyles = {
      sm: 'px-3 py-1.5 text-xs',
      md: 'px-4 py-2 text-sm',
      lg: 'px-6 py-3 text-base',
    };

    return (
      <button
        ref={ref}
        disabled={disabled}
        className={`${baseStyles} ${variantStyles[variant]} ${sizeStyles[size]} ${className}`}
        {...props}
      >
        {children}
      </button>
    );
  }
);

Button.displayName = 'Button';
export default Button;
