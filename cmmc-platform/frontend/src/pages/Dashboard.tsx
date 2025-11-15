import React from 'react';
import { MainLayout } from '@/components/layout';
import { Card } from '@/components/common/Card';
import { Badge } from '@/components/common/Badge';
import { ProgressBar } from '@/components/common/ProgressBar';
import {
  TrendingUp,
  AlertTriangle,
  CheckCircle,
  Clock,
  FileText,
  Shield,
} from 'lucide-react';

export const Dashboard: React.FC = () => {
  return (
    <MainLayout>
      <div className="space-y-6">
        {/* Page Header */}
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-600 mt-2">
            Overview of your CMMC Level 2 compliance progress
          </p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <Card className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Compliance Rate</p>
                <p className="text-3xl font-bold text-gray-900 mt-1">85%</p>
                <p className="text-sm text-success-600 mt-2 flex items-center">
                  <TrendingUp className="w-4 h-4 mr-1" />
                  +5% from last week
                </p>
              </div>
              <div className="w-12 h-12 bg-success-100 rounded-full flex items-center justify-center">
                <CheckCircle className="w-6 h-6 text-success-600" />
              </div>
            </div>
          </Card>

          <Card className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Controls Met</p>
                <p className="text-3xl font-bold text-gray-900 mt-1">94/110</p>
                <p className="text-sm text-gray-500 mt-2">16 remaining</p>
              </div>
              <div className="w-12 h-12 bg-primary-100 rounded-full flex items-center justify-center">
                <Shield className="w-6 h-6 text-primary-600" />
              </div>
            </div>
          </Card>

          <Card className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">At Risk Controls</p>
                <p className="text-3xl font-bold text-gray-900 mt-1">8</p>
                <p className="text-sm text-danger-600 mt-2">Requires attention</p>
              </div>
              <div className="w-12 h-12 bg-danger-100 rounded-full flex items-center justify-center">
                <AlertTriangle className="w-6 h-6 text-danger-600" />
              </div>
            </div>
          </Card>

          <Card className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Active Assessments</p>
                <p className="text-3xl font-bold text-gray-900 mt-1">3</p>
                <p className="text-sm text-gray-500 mt-2">2 in progress</p>
              </div>
              <div className="w-12 h-12 bg-warning-100 rounded-full flex items-center justify-center">
                <Clock className="w-6 h-6 text-warning-600" />
              </div>
            </div>
          </Card>
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Domain Progress */}
          <Card className="lg:col-span-2" title="Domain Compliance Progress">
            <div className="space-y-4">
              {[
                { domain: 'Access Control (AC)', progress: 92, color: 'success' as const },
                { domain: 'Awareness & Training (AT)', progress: 100, color: 'success' as const },
                { domain: 'Audit & Accountability (AU)', progress: 75, color: 'warning' as const },
                { domain: 'Configuration Management (CM)', progress: 88, color: 'success' as const },
                { domain: 'Identification & Auth (IA)', progress: 67, color: 'danger' as const },
                { domain: 'Incident Response (IR)', progress: 80, color: 'success' as const },
              ].map((item, idx) => (
                <div key={idx}>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-gray-700">{item.domain}</span>
                    <span className="text-sm font-semibold text-gray-900">
                      {item.progress}%
                    </span>
                  </div>
                  <ProgressBar value={item.progress} variant={item.color} showLabel={false} />
                </div>
              ))}
            </div>
          </Card>

          {/* Recent Activity */}
          <Card title="Recent Activity">
            <div className="space-y-4">
              {[
                {
                  action: 'Control AC.L2-3.1.1 marked as Met',
                  user: 'John Smith',
                  time: '2 hours ago',
                  type: 'success' as const,
                },
                {
                  action: 'Evidence uploaded for CM domain',
                  user: 'Sarah Johnson',
                  time: '4 hours ago',
                  type: 'gray' as const,
                },
                {
                  action: 'Assessment "Q1 2024" status updated',
                  user: 'Mike Davis',
                  time: '1 day ago',
                  type: 'blue' as const,
                },
                {
                  action: 'Control IA.L2-3.5.3 flagged as high risk',
                  user: 'Emily Chen',
                  time: '2 days ago',
                  type: 'danger' as const,
                },
              ].map((activity, idx) => (
                <div key={idx} className="flex items-start space-x-3">
                  <div className="flex-shrink-0">
                    <div className="w-2 h-2 bg-primary-500 rounded-full mt-2"></div>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900">{activity.action}</p>
                    <p className="text-xs text-gray-500 mt-1">
                      {activity.user} • {activity.time}
                    </p>
                  </div>
                  <Badge variant={activity.type} className="flex-shrink-0">
                    New
                  </Badge>
                </div>
              ))}
            </div>
          </Card>
        </div>

        {/* Active Assessments */}
        <Card title="Active Assessments">
          <div className="space-y-4">
            {[
              {
                name: 'Q1 2024 Assessment',
                status: 'In Progress',
                progress: 75,
                dueDate: 'Mar 31, 2024',
                assignee: 'John Smith',
              },
              {
                name: 'Annual Compliance Review',
                status: 'Under Review',
                progress: 90,
                dueDate: 'Apr 15, 2024',
                assignee: 'Sarah Johnson',
              },
              {
                name: 'New System Integration',
                status: 'Draft',
                progress: 25,
                dueDate: 'May 1, 2024',
                assignee: 'Mike Davis',
              },
            ].map((assessment, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors cursor-pointer"
              >
                <div className="flex-1">
                  <div className="flex items-center space-x-3">
                    <FileText className="w-5 h-5 text-gray-400" />
                    <div>
                      <h4 className="font-medium text-gray-900">{assessment.name}</h4>
                      <p className="text-sm text-gray-500 mt-1">
                        Assigned to {assessment.assignee} • Due {assessment.dueDate}
                      </p>
                    </div>
                  </div>
                  <div className="mt-3 ml-8">
                    <ProgressBar value={assessment.progress} size="sm" />
                  </div>
                </div>
                <Badge
                  variant={
                    assessment.status === 'In Progress'
                      ? 'blue'
                      : assessment.status === 'Under Review'
                      ? 'warning'
                      : 'gray'
                  }
                >
                  {assessment.status}
                </Badge>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </MainLayout>
  );
};
