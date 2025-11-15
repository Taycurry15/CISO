import { api } from './api';

export interface IntegrationProvider {
  id: string;
  name: string;
  category: 'cloud' | 'security' | 'ticketing' | 'sso' | 'other';
  description?: string;
  logo_url?: string;
  documentation_url?: string;
  is_active: boolean;
}

export interface Integration {
  id: string;
  organization_id: string;
  provider_id: string;
  provider_name: string;
  name: string;
  status: 'active' | 'disabled' | 'error' | 'pending';
  configuration: Record<string, any>;
  last_sync_at?: string;
  last_sync_status?: string;
  sync_frequency_minutes: number;
  auto_sync_enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface CreateIntegrationRequest {
  provider_id: string;
  name: string;
  configuration?: Record<string, any>;
  credentials: Record<string, string>;
  auto_sync_enabled?: boolean;
  sync_frequency_minutes?: number;
}

export interface Webhook {
  id: string;
  organization_id: string;
  name: string;
  url: string;
  secret: string;
  events: string[];
  is_active: boolean;
  headers: Record<string, string>;
  retry_count: number;
  timeout_seconds: number;
  created_at: string;
}

export interface CreateWebhookRequest {
  name: string;
  url: string;
  events: string[];
  headers?: Record<string, string>;
  retry_count?: number;
  timeout_seconds?: number;
}

export interface APIKey {
  id: string;
  organization_id: string;
  name: string;
  key?: string;
  key_prefix: string;
  permissions: string[];
  rate_limit_per_minute: number;
  expires_at?: string;
  last_used_at?: string;
  is_active: boolean;
  created_at: string;
}

export interface CreateAPIKeyRequest {
  name: string;
  permissions: string[];
  rate_limit_per_minute?: number;
  expires_at?: string;
}

export interface CloudResource {
  id: string;
  provider: string;
  resource_type: string;
  resource_id: string;
  resource_name?: string;
  region?: string;
  tags: Record<string, any>;
  compliance_status?: string;
  last_scanned_at?: string;
}

export interface SecurityFinding {
  id: string;
  finding_id: string;
  title: string;
  description?: string;
  severity: string;
  status: string;
  affected_resource?: string;
  cvss_score?: number;
  cve_ids: string[];
  remediation?: string;
  first_seen_at: string;
  last_seen_at: string;
}

export const integrationsService = {
  // Providers
  async getProviders(category?: string): Promise<IntegrationProvider[]> {
    const params = category ? { category } : {};
    const { data } = await api.get('/api/v1/integrations/providers', { params });
    return data;
  },

  // Integrations
  async getIntegrations(provider_id?: string, status?: string): Promise<Integration[]> {
    const params: any = {};
    if (provider_id) params.provider_id = provider_id;
    if (status) params.status = status;
    const { data } = await api.get('/api/v1/integrations', { params });
    return data;
  },

  async getIntegration(id: string): Promise<Integration> {
    const { data } = await api.get(`/api/v1/integrations/${id}`);
    return data;
  },

  async createIntegration(request: CreateIntegrationRequest): Promise<Integration> {
    const { data } = await api.post('/api/v1/integrations', request);
    return data;
  },

  async updateIntegration(id: string, updates: Partial<Integration>): Promise<Integration> {
    const { data } = await api.put(`/api/v1/integrations/${id}`, updates);
    return data;
  },

  async deleteIntegration(id: string): Promise<void> {
    await api.delete(`/api/v1/integrations/${id}`);
  },

  async syncIntegration(id: string): Promise<any> {
    const { data } = await api.post(`/api/v1/integrations/${id}/sync`);
    return data;
  },

  // Webhooks
  async getWebhooks(): Promise<Webhook[]> {
    const { data } = await api.get('/api/v1/webhooks');
    return data;
  },

  async createWebhook(request: CreateWebhookRequest): Promise<Webhook> {
    const { data } = await api.post('/api/v1/webhooks', request);
    return data;
  },

  async deleteWebhook(id: string): Promise<void> {
    await api.delete(`/api/v1/webhooks/${id}`);
  },

  // API Keys
  async getAPIKeys(): Promise<APIKey[]> {
    const { data } = await api.get('/api/v1/api-keys');
    return data;
  },

  async createAPIKey(request: CreateAPIKeyRequest): Promise<APIKey> {
    const { data } = await api.post('/api/v1/api-keys', request);
    return data;
  },

  async revokeAPIKey(id: string): Promise<void> {
    await api.delete(`/api/v1/api-keys/${id}`);
  },

  // Cloud Resources
  async getCloudResources(provider?: string, resource_type?: string): Promise<CloudResource[]> {
    const params: any = {};
    if (provider) params.provider = provider;
    if (resource_type) params.resource_type = resource_type;
    const { data } = await api.get('/api/v1/cloud-resources', { params });
    return data;
  },

  // Security Findings
  async getSecurityFindings(severity?: string, status?: string): Promise<SecurityFinding[]> {
    const params: any = {};
    if (severity) params.severity = severity;
    if (status) params.status = status;
    const { data } = await api.get('/api/v1/security-findings', { params });
    return data;
  },
};
