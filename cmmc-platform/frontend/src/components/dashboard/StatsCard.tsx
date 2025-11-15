import React from 'react';
import { LucideIcon } from 'lucide-react';

export interface StatsCardProps {
  title: string;
  value: string | number;
  trend?: string;
  icon: LucideIcon;
  variant?: 'success' | 'warning' | 'danger' | 'primary';
  subtitle?: string;
}

export const StatsCard: React.FC<StatsCardProps> = ({
  title,
  value,
  trend,
  icon: Icon,
  variant = 'primary',
  subtitle,
}) => {
  const variantStyles = {
    success: {
      icon: 'bg-success-100 text-success-600',
      trend: 'text-success-600',
    },
    warning: {
      icon: 'bg-warning-100 text-warning-600',
      trend: 'text-warning-600',
    },
    danger: {
      icon: 'bg-danger-100 text-danger-600',
      trend: 'text-danger-600',
    },
    primary: {
      icon: 'bg-primary-100 text-primary-600',
      trend: 'text-primary-600',
    },
  };

  return (
    <div className="card p-6">
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <p className="text-sm text-gray-600">{title}</p>
          <p className="text-3xl font-bold text-gray-900 mt-1">{value}</p>
          {trend && (
            <p className={`text-sm mt-2 ${variantStyles[variant].trend}`}>
              {trend}
            </p>
          )}
          {subtitle && <p className="text-sm text-gray-500 mt-2">{subtitle}</p>}
        </div>
        <div className={`w-12 h-12 rounded-full flex items-center justify-center ${variantStyles[variant].icon}`}>
          <Icon className="w-6 h-6" />
        </div>
      </div>
    </div>
  );
};
