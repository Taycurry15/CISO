import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { MainLayout } from '@/components/layout';
import { Button } from '@/components/common/Button';
import { Card } from '@/components/common/Card';
import { Modal } from '@/components/common/Modal';
import { Badge } from '@/components/common/Badge';
import { Table } from '@/components/common/Table';
import { integrationsService } from '@/services/integrations';
import {
  Cloud,
  Shield,
  Webhook,
  Key,
  Plus,
  RefreshCw,
  Trash2,
  CheckCircle,
  XCircle,
  AlertCircle,
  Clock,
} from 'lucide-react';

export const Integrations: React.FC = () => {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<'providers' | 'webhooks' | 'api-keys' | 'resources' | 'findings'>('providers');
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);

  // Fetch data
  const { data: providers } = useQuery({
    queryKey: ['integration-providers'],
    queryFn: () => integrationsService.getProviders(),
  });

  const { data: integrations, isLoading: isLoadingIntegrations } = useQuery({
    queryKey: ['integrations'],
    queryFn: () => integrationsService.getIntegrations(),
  });

  const { data: webhooks } = useQuery({
    queryKey: ['webhooks'],
    queryFn: () => integrationsService.getWebhooks(),
  });

  const { data: apiKeys } = useQuery({
    queryKey: ['api-keys'],
    queryFn: () => integrationsService.getAPIKeys(),
  });

  const { data: cloudResources } = useQuery({
    queryKey: ['cloud-resources'],
    queryFn: () => integrationsService.getCloudResources(),
  });

  const { data: securityFindings } = useQuery({
    queryKey: ['security-findings'],
    queryFn: () => integrationsService.getSecurityFindings(),
  });

  // Mutations
  const syncMutation = useMutation({
    mutationFn: (id: string) => integrationsService.syncIntegration(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['integrations'] });
      queryClient.invalidateQueries({ queryKey: ['cloud-resources'] });
      queryClient.invalidateQueries({ queryKey: ['security-findings'] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => integrationsService.deleteIntegration(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['integrations'] });
    },
  });

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'active':
        return <CheckCircle className="w-5 h-5 text-success-600" />;
      case 'error':
        return <XCircle className="w-5 h-5 text-danger-600" />;
      case 'pending':
        return <Clock className="w-5 h-5 text-warning-600" />;
      default:
        return <AlertCircle className="w-5 h-5 text-gray-600" />;
    }
  };

  const getStatusVariant = (status: string) => {
    switch (status) {
      case 'active':
        return 'success';
      case 'error':
        return 'danger';
      case 'pending':
        return 'warning';
      default:
        return 'gray';
    }
  };

  const tabs = [
    { id: 'providers', label: 'Integrations', icon: Cloud },
    { id: 'webhooks', label: 'Webhooks', icon: Webhook },
    { id: 'api-keys', label: 'API Keys', icon: Key },
    { id: 'resources', label: 'Cloud Resources', icon: Cloud },
    { id: 'findings', label: 'Security Findings', icon: Shield },
  ];

  return (
    <MainLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Integration Hub</h1>
            <p className="text-gray-600 mt-2">
              Connect your cloud providers, security tools, and other systems
            </p>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <Card className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Active Integrations</p>
                <p className="text-3xl font-bold text-gray-900">
                  {integrations?.filter((i) => i.status === 'active').length || 0}
                </p>
              </div>
              <Cloud className="w-12 h-12 text-primary-600 opacity-20" />
            </div>
          </Card>

          <Card className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Webhooks</p>
                <p className="text-3xl font-bold text-gray-900">{webhooks?.length || 0}</p>
              </div>
              <Webhook className="w-12 h-12 text-success-600 opacity-20" />
            </div>
          </Card>

          <Card className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">API Keys</p>
                <p className="text-3xl font-bold text-gray-900">
                  {apiKeys?.filter((k) => k.is_active).length || 0}
                </p>
              </div>
              <Key className="w-12 h-12 text-warning-600 opacity-20" />
            </div>
          </Card>

          <Card className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Cloud Resources</p>
                <p className="text-3xl font-bold text-gray-900">{cloudResources?.length || 0}</p>
              </div>
              <Shield className="w-12 h-12 text-danger-600 opacity-20" />
            </div>
          </Card>
        </div>

        {/* Tabs */}
        <div className="border-b border-gray-200">
          <nav className="-mb-px flex space-x-8">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`py-4 px-1 border-b-2 font-medium text-sm flex items-center space-x-2 ${
                    activeTab === tab.id
                      ? 'border-primary-600 text-primary-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  <Icon className="w-5 h-5" />
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </nav>
        </div>

        {/* Integrations Tab */}
        {activeTab === 'providers' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-semibold text-gray-900">Your Integrations</h2>
              <Button variant="primary" onClick={() => setIsCreateModalOpen(true)}>
                <Plus className="w-5 h-5 mr-2" />
                Add Integration
              </Button>
            </div>

            {isLoadingIntegrations ? (
              <div className="text-center py-12">
                <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-primary-600 border-r-transparent"></div>
              </div>
            ) : integrations && integrations.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {integrations.map((integration) => (
                  <Card key={integration.id} className="p-6">
                    <div className="flex items-start justify-between mb-4">
                      <div>
                        <h3 className="text-lg font-semibold text-gray-900">
                          {integration.name}
                        </h3>
                        <p className="text-sm text-gray-600 mt-1">{integration.provider_name}</p>
                      </div>
                      {getStatusIcon(integration.status)}
                    </div>

                    <div className="space-y-2 mb-4">
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-gray-600">Status:</span>
                        <Badge variant={getStatusVariant(integration.status) as any}>
                          {integration.status}
                        </Badge>
                      </div>
                      {integration.last_sync_at && (
                        <div className="flex items-center justify-between text-sm">
                          <span className="text-gray-600">Last Sync:</span>
                          <span className="text-gray-900">
                            {new Date(integration.last_sync_at).toLocaleString()}
                          </span>
                        </div>
                      )}
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-gray-600">Auto-sync:</span>
                        <span className="text-gray-900">
                          {integration.auto_sync_enabled ? 'Enabled' : 'Disabled'}
                        </span>
                      </div>
                    </div>

                    <div className="flex space-x-2">
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => syncMutation.mutate(integration.id)}
                        loading={syncMutation.isPending}
                        className="flex-1"
                      >
                        <RefreshCw className="w-4 h-4 mr-2" />
                        Sync Now
                      </Button>
                      <Button
                        variant="danger"
                        size="sm"
                        onClick={() => {
                          if (confirm('Delete this integration?')) {
                            deleteMutation.mutate(integration.id);
                          }
                        }}
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </Card>
                ))}
              </div>
            ) : (
              <Card className="p-12 text-center">
                <Cloud className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                  No integrations yet
                </h3>
                <p className="text-gray-600 mb-4">
                  Connect your cloud providers and security tools to sync data automatically
                </p>
                <Button variant="primary" onClick={() => setIsCreateModalOpen(true)}>
                  <Plus className="w-5 h-5 mr-2" />
                  Add Your First Integration
                </Button>
              </Card>
            )}
          </div>
        )}

        {/* Webhooks Tab */}
        {activeTab === 'webhooks' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-semibold text-gray-900">Webhooks</h2>
              <Button variant="primary" onClick={() => alert('Webhook creation UI coming soon')}>
                <Plus className="w-5 h-5 mr-2" />
                Add Webhook
              </Button>
            </div>

            {webhooks && webhooks.length > 0 ? (
              <Card>
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                          Name
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                          URL
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                          Events
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                          Status
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                          Actions
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {webhooks.map((webhook) => (
                        <tr key={webhook.id}>
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                            {webhook.name}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                            {webhook.url}
                          </td>
                          <td className="px-6 py-4 text-sm text-gray-600">
                            <div className="flex flex-wrap gap-1">
                              {webhook.events.slice(0, 3).map((event, idx) => (
                                <Badge key={idx} variant="blue">
                                  {event}
                                </Badge>
                              ))}
                              {webhook.events.length > 3 && (
                                <Badge variant="gray">+{webhook.events.length - 3}</Badge>
                              )}
                            </div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <Badge variant={webhook.is_active ? 'success' : 'gray'}>
                              {webhook.is_active ? 'Active' : 'Inactive'}
                            </Badge>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => {
                                if (confirm('Delete this webhook?')) {
                                  integrationsService.deleteWebhook(webhook.id);
                                  queryClient.invalidateQueries({ queryKey: ['webhooks'] });
                                }
                              }}
                            >
                              <Trash2 className="w-4 h-4 text-danger-600" />
                            </Button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>
            ) : (
              <Card className="p-12 text-center">
                <p className="text-gray-600">No webhooks configured</p>
              </Card>
            )}
          </div>
        )}

        {/* API Keys Tab */}
        {activeTab === 'api-keys' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-semibold text-gray-900">API Keys</h2>
              <Button variant="primary" onClick={() => alert('API key creation UI coming soon')}>
                <Plus className="w-5 h-5 mr-2" />
                Create API Key
              </Button>
            </div>

            {apiKeys && apiKeys.length > 0 ? (
              <Card>
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                          Name
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                          Key
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                          Permissions
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                          Last Used
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                          Actions
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {apiKeys.map((key) => (
                        <tr key={key.id}>
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                            {key.name}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm">
                            <code className="bg-gray-100 px-2 py-1 rounded text-gray-900">
                              {key.key_prefix}
                            </code>
                          </td>
                          <td className="px-6 py-4 text-sm text-gray-600">
                            {key.permissions.length} permissions
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                            {key.last_used_at
                              ? new Date(key.last_used_at).toLocaleString()
                              : 'Never'}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => {
                                if (confirm('Revoke this API key?')) {
                                  integrationsService.revokeAPIKey(key.id);
                                  queryClient.invalidateQueries({ queryKey: ['api-keys'] });
                                }
                              }}
                            >
                              <Trash2 className="w-4 h-4 text-danger-600" />
                            </Button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>
            ) : (
              <Card className="p-12 text-center">
                <p className="text-gray-600">No API keys created</p>
              </Card>
            )}
          </div>
        )}

        {/* Cloud Resources Tab */}
        {activeTab === 'resources' && (
          <div className="space-y-6">
            <h2 className="text-xl font-semibold text-gray-900">Cloud Resources</h2>
            {cloudResources && cloudResources.length > 0 ? (
              <Card>
                <Table
                  columns={[
                    {
                      key: 'provider',
                      header: 'Provider',
                      render: (resource: any) => (
                        <Badge variant="blue">{resource.provider.toUpperCase()}</Badge>
                      ),
                    },
                    { key: 'resource_type', header: 'Type' },
                    { key: 'resource_name', header: 'Name' },
                    { key: 'region', header: 'Region' },
                    {
                      key: 'compliance_status',
                      header: 'Compliance',
                      render: (resource: any) =>
                        resource.compliance_status ? (
                          <Badge
                            variant={
                              resource.compliance_status === 'compliant' ? 'success' : 'danger'
                            }
                          >
                            {resource.compliance_status}
                          </Badge>
                        ) : (
                          <span className="text-gray-400">Unknown</span>
                        ),
                    },
                  ]}
                  data={cloudResources}
                />
              </Card>
            ) : (
              <Card className="p-12 text-center">
                <p className="text-gray-600">No cloud resources synced yet</p>
                <p className="text-sm text-gray-500 mt-2">
                  Add a cloud provider integration to sync resources
                </p>
              </Card>
            )}
          </div>
        )}

        {/* Security Findings Tab */}
        {activeTab === 'findings' && (
          <div className="space-y-6">
            <h2 className="text-xl font-semibold text-gray-900">Security Findings</h2>
            {securityFindings && securityFindings.length > 0 ? (
              <div className="space-y-4">
                {securityFindings.map((finding) => (
                  <Card key={finding.id} className="p-6">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center space-x-3 mb-2">
                          <h3 className="text-lg font-semibold text-gray-900">{finding.title}</h3>
                          <Badge
                            variant={
                              finding.severity === 'critical'
                                ? 'danger'
                                : finding.severity === 'high'
                                ? 'warning'
                                : 'gray'
                            }
                          >
                            {finding.severity.toUpperCase()}
                          </Badge>
                        </div>
                        <p className="text-sm text-gray-600 mb-3">{finding.description}</p>
                        <div className="flex items-center space-x-4 text-sm text-gray-500">
                          {finding.affected_resource && (
                            <span>Resource: {finding.affected_resource}</span>
                          )}
                          {finding.cvss_score && <span>CVSS: {finding.cvss_score}</span>}
                          {finding.cve_ids.length > 0 && (
                            <span>CVEs: {finding.cve_ids.join(', ')}</span>
                          )}
                        </div>
                      </div>
                      <Badge variant={finding.status === 'open' ? 'danger' : 'success'}>
                        {finding.status}
                      </Badge>
                    </div>
                  </Card>
                ))}
              </div>
            ) : (
              <Card className="p-12 text-center">
                <p className="text-gray-600">No security findings</p>
                <p className="text-sm text-gray-500 mt-2">
                  Add a security tool integration to sync findings
                </p>
              </Card>
            )}
          </div>
        )}

        {/* Create Integration Modal */}
        <Modal
          isOpen={isCreateModalOpen}
          onClose={() => setIsCreateModalOpen(false)}
          title="Add Integration"
          size="lg"
        >
          <div className="space-y-4">
            <p className="text-gray-600">
              Select a provider to integrate with your CMMC platform
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {providers
                ?.filter((p) => p.category === 'cloud')
                .map((provider) => (
                  <button
                    key={provider.id}
                    className="p-4 border border-gray-200 rounded-lg hover:border-primary-600 hover:bg-primary-50 transition-colors text-left"
                    onClick={() => {
                      // In real implementation, show provider-specific form
                      alert(`Integration setup for ${provider.name} - not implemented in demo`);
                    }}
                  >
                    <h3 className="font-semibold text-gray-900">{provider.name}</h3>
                    <p className="text-sm text-gray-600 mt-1">{provider.description}</p>
                  </button>
                ))}
            </div>
          </div>
        </Modal>
      </div>
    </MainLayout>
  );
};
