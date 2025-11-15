import React from 'react';
import { ControlStatus } from '@/types';
import { CheckCircle, XCircle, AlertCircle, MinusCircle } from 'lucide-react';

export interface ControlStatusSelectorProps {
  value: ControlStatus;
  onChange?: (status: ControlStatus) => void;
  disabled?: boolean;
}

export const ControlStatusSelector: React.FC<ControlStatusSelectorProps> = ({
  value,
  onChange,
  disabled = false,
}) => {
  const statuses: { value: ControlStatus; label: string; icon: any; color: string }[] = [
    { value: 'Met', label: 'Met', icon: CheckCircle, color: 'success' },
    { value: 'Not Met', label: 'Not Met', icon: XCircle, color: 'danger' },
    { value: 'Partially Met', label: 'Partially Met', icon: AlertCircle, color: 'warning' },
    { value: 'Not Applicable', label: 'N/A', icon: MinusCircle, color: 'gray' },
  ];

  return (
    <div className="flex flex-wrap gap-2">
      {statuses.map((status) => {
        const Icon = status.icon;
        const isSelected = value === status.value;
        const baseStyles = 'px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center space-x-2';

        let colorStyles = '';
        if (isSelected) {
          switch (status.color) {
            case 'success':
              colorStyles = 'bg-success-600 text-white border-success-600';
              break;
            case 'danger':
              colorStyles = 'bg-danger-600 text-white border-danger-600';
              break;
            case 'warning':
              colorStyles = 'bg-warning-600 text-white border-warning-600';
              break;
            case 'gray':
              colorStyles = 'bg-gray-600 text-white border-gray-600';
              break;
          }
        } else {
          colorStyles = 'bg-white text-gray-700 border-gray-300 hover:border-gray-400';
        }

        return (
          <button
            key={status.value}
            onClick={() => !disabled && onChange?.(status.value)}
            disabled={disabled}
            className={`${baseStyles} ${colorStyles} border-2 ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
          >
            <Icon className="w-4 h-4" />
            <span>{status.label}</span>
          </button>
        );
      })}
    </div>
  );
};
