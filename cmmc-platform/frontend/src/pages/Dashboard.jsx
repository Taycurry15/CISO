import { useQuery } from '@tanstack/react-query';
import { dashboardAPI } from '../services/api';
import useAuthStore from '../stores/authStore';
import {
  TrendingUp,
  AlertTriangle,
  CheckCircle,
  FileText,
  Activity
} from 'lucide-react';

export default function Dashboard() {
  const user = useAuthStore((state) => state.user);

  const { data: summary, isLoading } = useQuery({
    queryKey: ['dashboard-summary', user?.organizationId],
    queryFn: () => dashboardAPI.getSummary(user?.organizationId).then(res => res.data),
    enabled: !!user?.organizationId,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  const stats = [
    {
      name: 'Active Assessments',
      value: summary?.active_assessments || 0,
      icon: FileText,
      color: 'bg-blue-500',
      change: '+12%',
      changeType: 'positive',
    },
    {
      name: 'Compliance Score',
      value: summary?.compliance_percentage || 0,
      suffix: '%',
      icon: CheckCircle,
      color: 'bg-green-500',
      change: '+5.2%',
      changeType: 'positive',
    },
    {
      name: 'Evidence Items',
      value: summary?.total_evidence || 0,
      icon: Activity,
      color: 'bg-purple-500',
      change: '+18%',
      changeType: 'positive',
    },
    {
      name: 'Open Findings',
      value: summary?.open_findings || 0,
      icon: AlertTriangle,
      color: 'bg-red-500',
      change: '-3%',
      changeType: 'negative',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="mt-1 text-sm text-gray-500">
          Welcome back, {user?.email}! Here's your compliance overview.
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <div key={stat.name} className="card">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className={`p-3 rounded-lg ${stat.color}`}>
                  <stat.icon className="w-6 h-6 text-white" />
                </div>
              </div>
              <div className="ml-4 flex-1">
                <p className="text-sm font-medium text-gray-600">{stat.name}</p>
                <div className="flex items-baseline">
                  <p className="text-2xl font-semibold text-gray-900">
                    {stat.value}{stat.suffix}
                  </p>
                  <span className={`ml-2 text-sm font-medium ${
                    stat.changeType === 'positive' ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {stat.change}
                  </span>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Compliance by Control Family */}
        <div className="card">
          <h3 className="text-lg font-medium text-gray-900 mb-4">
            Compliance by Control Family
          </h3>
          <div className="space-y-4">
            {['AC', 'AU', 'AT', 'CM', 'IA', 'IR', 'MA', 'MP', 'PS', 'PE'].map((family, idx) => (
              <div key={family}>
                <div className="flex items-center justify-between text-sm mb-1">
                  <span className="font-medium text-gray-700">{family}</span>
                  <span className="text-gray-600">{85 + idx}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-primary-600 h-2 rounded-full"
                    style={{ width: `${85 + idx}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Recent Activity */}
        <div className="card">
          <h3 className="text-lg font-medium text-gray-900 mb-4">
            Recent Activity
          </h3>
          <div className="space-y-4">
            {[
              { action: 'Evidence uploaded', item: 'AC-2.1 User Access Control', time: '2 hours ago' },
              { action: 'Control analyzed', item: 'AU-3.1 Audit Review', time: '4 hours ago' },
              { action: 'Assessment updated', item: 'CMMC Level 2 Assessment', time: '1 day ago' },
              { action: 'Report generated', item: 'System Security Plan', time: '2 days ago' },
              { action: 'Finding resolved', item: 'IA-5.1 Password Policy', time: '3 days ago' },
            ].map((activity, idx) => (
              <div key={idx} className="flex items-start space-x-3">
                <div className="flex-shrink-0">
                  <div className="w-2 h-2 mt-2 rounded-full bg-primary-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900">
                    {activity.action}
                  </p>
                  <p className="text-sm text-gray-600">{activity.item}</p>
                  <p className="text-xs text-gray-500 mt-1">{activity.time}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* SPRS Score */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-medium text-gray-900">SPRS Score</h3>
          <span className="text-2xl font-bold text-primary-600">
            {summary?.sprs_score || 85}
          </span>
        </div>
        <p className="text-sm text-gray-600 mb-4">
          Supplier Performance Risk System (SPRS) score based on NIST 800-171 compliance
        </p>
        <div className="w-full bg-gray-200 rounded-full h-4">
          <div
            className="bg-gradient-to-r from-green-500 to-primary-600 h-4 rounded-full"
            style={{ width: `${((summary?.sprs_score || 85) + 203) / 313 * 100}%` }}
          />
        </div>
        <div className="flex justify-between text-xs text-gray-500 mt-2">
          <span>-203 (Minimum)</span>
          <span>110 (Maximum)</span>
        </div>
      </div>
    </div>
  );
}
