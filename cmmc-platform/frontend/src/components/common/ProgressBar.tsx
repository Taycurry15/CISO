import React from 'react';

export interface ProgressBarProps {
  value: number;
  max?: number;
  variant?: 'success' | 'warning' | 'danger' | 'primary';
  showLabel?: boolean;
  className?: string;
  size?: 'sm' | 'md' | 'lg';
}

export const ProgressBar: React.FC<ProgressBarProps> = ({
  value,
  max = 100,
  variant = 'primary',
  showLabel = true,
  className = '',
  size = 'md',
}) => {
  const percentage = Math.min(Math.max((value / max) * 100, 0), 100);

  const variantStyles = {
    success: 'bg-success-500',
    warning: 'bg-warning-500',
    danger: 'bg-danger-500',
    primary: 'bg-primary-600',
  };

  const sizeStyles = {
    sm: 'h-2',
    md: 'h-4',
    lg: 'h-6',
  };

  return (
    <div className={`w-full ${className}`}>
      <div className={`w-full bg-gray-200 rounded-full overflow-hidden ${sizeStyles[size]}`}>
        <div
          className={`${variantStyles[variant]} ${sizeStyles[size]} rounded-full transition-all duration-300 ease-in-out flex items-center justify-center`}
          style={{ width: `${percentage}%` }}
          role="progressbar"
          aria-valuenow={value}
          aria-valuemin={0}
          aria-valuemax={max}
        >
          {showLabel && size !== 'sm' && (
            <span className="text-xs font-medium text-white px-2">
              {Math.round(percentage)}%
            </span>
          )}
        </div>
      </div>
      {showLabel && size === 'sm' && (
        <p className="text-xs text-gray-600 mt-1">{Math.round(percentage)}%</p>
      )}
    </div>
  );
};
