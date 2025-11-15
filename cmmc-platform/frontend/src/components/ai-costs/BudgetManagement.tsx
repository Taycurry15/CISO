/**
 * AI Budget Management Component
 * Configure spending budgets and view alerts
 */

import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  DollarSign,
  AlertTriangle,
  AlertCircle,
  Bell,
  BellOff,
  Shield,
  Trash2,
  Plus,
  Check,
  X,
} from 'lucide-react';
import { api } from '../../services/api';

interface Budget {
  id: string;
  budget_period: string;
  budget_limit_usd: number;
  warning_threshold_percent: number;
  critical_threshold_percent: number;
  email_alerts_enabled: boolean;
  has_slack_webhook: boolean;
  has_custom_webhook: boolean;
  block_at_limit: boolean;
  assessment_id: string | null;
  created_at: string;
  updated_at: string;
}

interface Alert {
  id: string;
  assessment_id: string | null;
  alert_level: string;
  budget_period: string;
  current_spend_usd: number;
  budget_limit_usd: number;
  percent_used: number;
  period_start: string;
  period_end: string;
  acknowledged: boolean;
  acknowledged_by: string | null;
  acknowledged_at: string | null;
  notification_sent: boolean;
  created_at: string;
}

export const BudgetManagement: React.FC = () => {
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [selectedTab, setSelectedTab] = useState<'budgets' | 'alerts'>('budgets');
  const queryClient = useQueryClient();

  // Fetch budgets
  const { data: budgets, isLoading: budgetsLoading } = useQuery<Budget[]>({
    queryKey: ['ai-budgets'],
    queryFn: async () => {
      const response = await api.get('/ai/budgets');
      return response.data;
    },
  });

  // Fetch alerts
  const { data: alerts, isLoading: alertsLoading } = useQuery<Alert[]>({
    queryKey: ['ai-budget-alerts'],
    queryFn: async () => {
      const response = await api.get('/ai/alerts');
      return response.data;
    },
  });

  // Delete budget mutation
  const deleteBudgetMutation = useMutation({
    mutationFn: async (budgetId: string) => {
      await api.delete(`/ai/budgets/${budgetId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ai-budgets'] });
    },
  });

  // Acknowledge alert mutation
  const acknowledgeAlertMutation = useMutation({
    mutationFn: async (alertId: string) => {
      await api.post(`/ai/alerts/${alertId}/acknowledge`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ai-budget-alerts'] });
    },
  });

  const formatCurrency = (amount: number): string => {
    return `$${amount.toFixed(2)}`;
  };

  const getAlertLevelColor = (level: string): string => {
    const colors: Record<string, string> = {
      warning: 'text-orange-600 bg-orange-100',
      critical: 'text-red-600 bg-red-100',
      limit_reached: 'text-red-800 bg-red-200',
    };
    return colors[level] || 'text-gray-600 bg-gray-100';
  };

  const getAlertIcon = (level: string): React.ReactNode => {
    if (level === 'critical' || level === 'limit_reached') {
      return <AlertCircle className="w-5 h-5" />;
    }
    return <AlertTriangle className="w-5 h-5" />;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Budget Management</h2>
          <p className="text-sm text-gray-600 mt-1">
            Configure AI spending limits and monitor alerts
          </p>
        </div>
        <button
          onClick={() => setShowCreateForm(true)}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2"
        >
          <Plus className="w-4 h-4" />
          Create Budget
        </button>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setSelectedTab('budgets')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              selectedTab === 'budgets'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            <div className="flex items-center gap-2">
              <DollarSign className="w-4 h-4" />
              Budgets ({budgets?.length || 0})
            </div>
          </button>
          <button
            onClick={() => setSelectedTab('alerts')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              selectedTab === 'alerts'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            <div className="flex items-center gap-2">
              <Bell className="w-4 h-4" />
              Alerts (
              {alerts?.filter((a) => !a.acknowledged).length || 0})
            </div>
          </button>
        </nav>
      </div>

      {/* Budgets Tab */}
      {selectedTab === 'budgets' && (
        <div className="space-y-4">
          {budgetsLoading ? (
            <div className="text-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
            </div>
          ) : budgets && budgets.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {budgets.map((budget) => (
                <div
                  key={budget.id}
                  className="bg-white rounded-lg shadow border border-gray-200 p-6 hover:shadow-md transition-shadow"
                >
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900 capitalize">
                        {budget.budget_period} Budget
                      </h3>
                      <p className="text-sm text-gray-500">
                        {budget.assessment_id
                          ? 'Assessment-specific'
                          : 'Organization-wide'}
                      </p>
                    </div>
                    <button
                      onClick={() => deleteBudgetMutation.mutate(budget.id)}
                      className="text-red-600 hover:text-red-700"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>

                  <div className="space-y-3">
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-gray-600">Limit:</span>
                      <span className="text-lg font-bold text-gray-900">
                        {formatCurrency(budget.budget_limit_usd)}
                      </span>
                    </div>

                    <div className="space-y-2">
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600">Warning:</span>
                        <span className="font-medium text-orange-600">
                          {budget.warning_threshold_percent}%
                        </span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600">Critical:</span>
                        <span className="font-medium text-red-600">
                          {budget.critical_threshold_percent}%
                        </span>
                      </div>
                    </div>

                    <div className="pt-3 border-t border-gray-200 space-y-2">
                      <div className="flex items-center gap-2 text-sm">
                        {budget.email_alerts_enabled ? (
                          <Bell className="w-4 h-4 text-green-600" />
                        ) : (
                          <BellOff className="w-4 h-4 text-gray-400" />
                        )}
                        <span className="text-gray-600">
                          Email alerts{' '}
                          {budget.email_alerts_enabled ? 'enabled' : 'disabled'}
                        </span>
                      </div>

                      {budget.has_slack_webhook && (
                        <div className="flex items-center gap-2 text-sm">
                          <Check className="w-4 h-4 text-green-600" />
                          <span className="text-gray-600">Slack configured</span>
                        </div>
                      )}

                      {budget.block_at_limit && (
                        <div className="flex items-center gap-2 text-sm">
                          <Shield className="w-4 h-4 text-red-600" />
                          <span className="text-red-600 font-medium">
                            Blocks at limit
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="bg-gray-50 rounded-lg border border-gray-200 p-12 text-center">
              <DollarSign className="w-16 h-16 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                No budgets configured
              </h3>
              <p className="text-gray-600 mb-4">
                Create your first budget to start monitoring AI spending
              </p>
              <button
                onClick={() => setShowCreateForm(true)}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                Create Budget
              </button>
            </div>
          )}
        </div>
      )}

      {/* Alerts Tab */}
      {selectedTab === 'alerts' && (
        <div className="space-y-4">
          {alertsLoading ? (
            <div className="text-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
            </div>
          ) : alerts && alerts.length > 0 ? (
            <div className="space-y-3">
              {alerts.map((alert) => (
                <div
                  key={alert.id}
                  className={`bg-white rounded-lg shadow border-l-4 p-6 ${
                    alert.acknowledged
                      ? 'border-gray-300 opacity-60'
                      : alert.alert_level === 'critical' ||
                        alert.alert_level === 'limit_reached'
                      ? 'border-red-500'
                      : 'border-orange-500'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-start gap-4 flex-1">
                      <div
                        className={`p-2 rounded-lg ${getAlertLevelColor(
                          alert.alert_level
                        )}`}
                      >
                        {getAlertIcon(alert.alert_level)}
                      </div>

                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <h3 className="text-lg font-semibold text-gray-900 capitalize">
                            {alert.alert_level.replace('_', ' ')} Alert
                          </h3>
                          <span className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded">
                            {alert.budget_period}
                          </span>
                        </div>

                        <p className="text-gray-700 mb-3">
                          AI spending has reached{' '}
                          <span className="font-bold text-gray-900">
                            {alert.percent_used.toFixed(1)}%
                          </span>{' '}
                          of the budget limit
                        </p>

                        <div className="grid grid-cols-2 gap-4 text-sm">
                          <div>
                            <span className="text-gray-600">Current Spend:</span>
                            <span className="ml-2 font-medium text-gray-900">
                              {formatCurrency(alert.current_spend_usd)}
                            </span>
                          </div>
                          <div>
                            <span className="text-gray-600">Budget Limit:</span>
                            <span className="ml-2 font-medium text-gray-900">
                              {formatCurrency(alert.budget_limit_usd)}
                            </span>
                          </div>
                        </div>

                        <div className="mt-3 text-xs text-gray-500">
                          Triggered: {new Date(alert.created_at).toLocaleString()}
                        </div>

                        {alert.acknowledged && (
                          <div className="mt-2 text-xs text-green-600 flex items-center gap-1">
                            <Check className="w-3 h-3" />
                            Acknowledged{' '}
                            {alert.acknowledged_at &&
                              `at ${new Date(alert.acknowledged_at).toLocaleString()}`}
                          </div>
                        )}
                      </div>
                    </div>

                    {!alert.acknowledged && (
                      <button
                        onClick={() => acknowledgeAlertMutation.mutate(alert.id)}
                        className="ml-4 px-3 py-1 bg-green-600 text-white text-sm rounded hover:bg-green-700 flex items-center gap-1"
                      >
                        <Check className="w-4 h-4" />
                        Acknowledge
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="bg-gray-50 rounded-lg border border-gray-200 p-12 text-center">
              <Bell className="w-16 h-16 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                No alerts
              </h3>
              <p className="text-gray-600">
                Your AI spending is within budget limits
              </p>
            </div>
          )}
        </div>
      )}

      {/* Create Budget Modal */}
      {showCreateForm && (
        <CreateBudgetModal
          onClose={() => setShowCreateForm(false)}
          onSuccess={() => {
            setShowCreateForm(false);
            queryClient.invalidateQueries({ queryKey: ['ai-budgets'] });
          }}
        />
      )}
    </div>
  );
};

// Create Budget Modal Component
interface CreateBudgetModalProps {
  onClose: () => void;
  onSuccess: () => void;
}

const CreateBudgetModal: React.FC<CreateBudgetModalProps> = ({
  onClose,
  onSuccess,
}) => {
  const [formData, setFormData] = useState({
    budget_limit_usd: 100,
    budget_period: 'monthly',
    warning_threshold_percent: 75,
    critical_threshold_percent: 90,
    email_alerts_enabled: true,
    slack_webhook_url: '',
    block_at_limit: false,
  });

  const createBudgetMutation = useMutation({
    mutationFn: async (data: typeof formData) => {
      await api.post('/ai/budgets', data);
    },
    onSuccess: () => {
      onSuccess();
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    createBudgetMutation.mutate(formData);
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b border-gray-200">
          <div className="flex justify-between items-center">
            <h3 className="text-xl font-bold text-gray-900">Create Budget</h3>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600"
            >
              <X className="w-6 h-6" />
            </button>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Budget Limit (USD)
              </label>
              <input
                type="number"
                min="1"
                step="0.01"
                value={formData.budget_limit_usd}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    budget_limit_usd: parseFloat(e.target.value),
                  })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Budget Period
              </label>
              <select
                value={formData.budget_period}
                onChange={(e) =>
                  setFormData({ ...formData, budget_period: e.target.value })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
                <option value="monthly">Monthly</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Warning Threshold (%)
              </label>
              <input
                type="number"
                min="1"
                max="100"
                value={formData.warning_threshold_percent}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    warning_threshold_percent: parseInt(e.target.value),
                  })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Critical Threshold (%)
              </label>
              <input
                type="number"
                min="1"
                max="100"
                value={formData.critical_threshold_percent}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    critical_threshold_percent: parseInt(e.target.value),
                  })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                required
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Slack Webhook URL (optional)
            </label>
            <input
              type="url"
              value={formData.slack_webhook_url}
              onChange={(e) =>
                setFormData({ ...formData, slack_webhook_url: e.target.value })
              }
              placeholder="https://hooks.slack.com/services/..."
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div className="space-y-3">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={formData.email_alerts_enabled}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    email_alerts_enabled: e.target.checked,
                  })
                }
                className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700">Enable email alerts</span>
            </label>

            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={formData.block_at_limit}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    block_at_limit: e.target.checked,
                  })
                }
                className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700">
                Block AI operations when limit is reached
              </span>
            </label>
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-gray-200">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={createBudgetMutation.isPending}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {createBudgetMutation.isPending ? 'Creating...' : 'Create Budget'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default BudgetManagement;
