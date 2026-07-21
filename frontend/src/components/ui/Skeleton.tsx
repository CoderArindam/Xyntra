import React from 'react';

export interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'text' | 'circular' | 'rectangular' | 'card';
  width?: string | number;
  height?: string | number;
  className?: string;
}

export const Skeleton: React.FC<SkeletonProps> = ({
  variant = 'rectangular',
  width,
  height,
  className = '',
  style,
  ...props
}) => {
  const baseStyles = 'animate-pulse bg-brand-surface-container/70 border border-brand-border/40';

  const variantStyles = {
    text: 'rounded-md h-4 w-full',
    circular: 'rounded-full shrink-0',
    rectangular: 'rounded-xl w-full',
    card: 'rounded-2xl border border-brand-border/60 p-6 space-y-4 w-full bg-brand-surface-low/50',
  };

  const computedStyle: React.CSSProperties = {
    ...style,
    width: width !== undefined ? (typeof width === 'number' ? `${width}px` : width) : undefined,
    height: height !== undefined ? (typeof height === 'number' ? `${height}px` : height) : undefined,
  };

  return (
    <div
      className={`${baseStyles} ${variantStyles[variant]} ${className}`}
      style={computedStyle}
      aria-hidden="true"
      {...props}
    />
  );
};

export default Skeleton;
