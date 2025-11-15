import React, { useState } from 'react';
import { MainLayout } from '@/components/layout';
import { Card } from '@/components/common/Card';
import { Input } from '@/components/common/Input';
import { Button } from '@/components/common/Button';
import { Badge } from '@/components/common/Badge';
import { useAuth } from '@/hooks/useAuth';
import { User, Building, Bell, Shield, Key } from 'lucide-react';

export const Settings: React.FC = () => {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState('profile');

  const tabs = [
    { id: 'profile', label: 'Profile', icon: User },
    { id: 'organization', label: 'Organization', icon: Building },
    { id: 'notifications', label: 'Notifications', icon: Bell },
    { id: 'security', label: 'Security', icon: Shield },
  ];

  return (
    <MainLayout>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Settings</h1>
          <p className="text-gray-600 mt-2">Manage your account and preferences</p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Tabs */}
          <div className="lg:col-span-1">
            <Card className="p-4">
              <nav className="space-y-1">
                {tabs.map((tab) => {
                  const Icon = tab.icon;
                  return (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id)}
                      className={`w-full flex items-center px-4 py-3 text-sm font-medium rounded-lg transition-colors ${
                        activeTab === tab.id
                          ? 'bg-primary-50 text-primary-700'
                          : 'text-gray-700 hover:bg-gray-100'
                      }`}
                    >
                      <Icon className="w-5 h-5 mr-3" />
                      {tab.label}
                    </button>
                  );
                })}
              </nav>
            </Card>
          </div>

          {/* Content */}
          <div className="lg:col-span-3">
            {activeTab === 'profile' && (
              <Card title="Profile Settings">
                <div className="space-y-6">
                  <div className="flex items-center space-x-4">
                    <div className="w-20 h-20 bg-primary-600 rounded-full flex items-center justify-center">
                      <User className="w-10 h-10 text-white" />
                    </div>
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900">{user?.fullName}</h3>
                      <p className="text-gray-600">{user?.email}</p>
                      <Badge variant="blue" className="mt-2">
                        {user?.role}
                      </Badge>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <Input label="Full Name" value={user?.fullName || ''} />
                    <Input label="Email" type="email" value={user?.email || ''} disabled />
                  </div>

                  <div className="flex justify-end space-x-3">
                    <Button variant="secondary">Cancel</Button>
                    <Button variant="primary">Save Changes</Button>
                  </div>
                </div>
              </Card>
            )}

            {activeTab === 'organization' && (
              <Card title="Organization Settings">
                <div className="space-y-6">
                  <Input label="Organization Name" defaultValue="Example Organization" />
                  <Input label="Organization Type" defaultValue="Defense Contractor" />
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Subscription Plan
                    </label>
                    <div className="flex items-center space-x-4">
                      <Badge variant="success">Professional</Badge>
                      <span className="text-sm text-gray-600">Valid until Dec 31, 2024</span>
                    </div>
                  </div>

                  <div className="pt-4 border-t border-gray-200">
                    <h4 className="text-sm font-semibold text-gray-900 mb-4">Team Members</h4>
                    <div className="space-y-3">
                      {[1, 2, 3].map((i) => (
                        <div key={i} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                          <div className="flex items-center space-x-3">
                            <div className="w-8 h-8 bg-gray-300 rounded-full"></div>
                            <div>
                              <p className="text-sm font-medium text-gray-900">Team Member {i}</p>
                              <p className="text-xs text-gray-500">member{i}@example.com</p>
                            </div>
                          </div>
                          <Badge variant="gray">Assessor</Badge>
                        </div>
                      ))}
                    </div>
                    <Button variant="secondary" size="sm" className="mt-4">
                      Invite Team Member
                    </Button>
                  </div>
                </div>
              </Card>
            )}

            {activeTab === 'notifications' && (
              <Card title="Notification Preferences">
                <div className="space-y-4">
                  {[
                    { label: 'Email notifications for assessment updates', checked: true },
                    { label: 'Daily compliance progress reports', checked: true },
                    { label: 'Control status change alerts', checked: false },
                    { label: 'Evidence upload confirmations', checked: true },
                    { label: 'Report generation completion', checked: true },
                    { label: 'Team member activity updates', checked: false },
                  ].map((item, idx) => (
                    <div key={idx} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                      <label className="text-sm text-gray-700">{item.label}</label>
                      <input
                        type="checkbox"
                        defaultChecked={item.checked}
                        className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                      />
                    </div>
                  ))}
                  <div className="flex justify-end pt-4">
                    <Button variant="primary">Save Preferences</Button>
                  </div>
                </div>
              </Card>
            )}

            {activeTab === 'security' && (
              <Card title="Security Settings">
                <div className="space-y-6">
                  <div>
                    <h4 className="text-sm font-semibold text-gray-900 mb-4 flex items-center">
                      <Key className="w-4 h-4 mr-2" />
                      Change Password
                    </h4>
                    <div className="space-y-4">
                      <Input label="Current Password" type="password" />
                      <Input label="New Password" type="password" />
                      <Input label="Confirm New Password" type="password" />
                      <Button variant="primary">Update Password</Button>
                    </div>
                  </div>

                  <div className="pt-6 border-t border-gray-200">
                    <h4 className="text-sm font-semibold text-gray-900 mb-4">
                      Two-Factor Authentication
                    </h4>
                    <p className="text-sm text-gray-600 mb-4">
                      Add an extra layer of security to your account
                    </p>
                    <Button variant="secondary">Enable 2FA</Button>
                  </div>

                  <div className="pt-6 border-t border-gray-200">
                    <h4 className="text-sm font-semibold text-gray-900 mb-4">Active Sessions</h4>
                    <div className="space-y-3">
                      <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                        <div>
                          <p className="text-sm font-medium text-gray-900">Current Session</p>
                          <p className="text-xs text-gray-500">Chrome on Windows • Now</p>
                        </div>
                        <Badge variant="success">Active</Badge>
                      </div>
                    </div>
                  </div>
                </div>
              </Card>
            )}
          </div>
        </div>
      </div>
    </MainLayout>
  );
};
