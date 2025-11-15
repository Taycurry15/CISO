import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import { MainLayout } from '@/components/layout';
import { Input } from '@/components/common/Input';
import { Select } from '@/components/common/Select';
import { ControlCard } from '@/components/controls';
import { useControlFindings } from '@/hooks/useControls';
import { ControlStatus } from '@/types';

export const Controls: React.FC = () => {
  const { assessmentId } = useParams<{ assessmentId: string }>();
  const { findings, isLoading, updateFinding } = useControlFindings(assessmentId || '');

  const [searchQuery, setSearchQuery] = useState('');
  const [domainFilter, setDomainFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  const handleStatusChange = async (controlId: string, status: ControlStatus) => {
    try {
      await updateFinding({ controlId, updates: { status } });
    } catch (error) {
      console.error('Failed to update control status:', error);
    }
  };

  const domains = [
    'AC', 'AT', 'AU', 'CA', 'CM', 'IA', 'IR', 'MA', 'MP', 'PE', 'PS', 'RE', 'SA', 'SC', 'SI'
  ];

  const filteredFindings = findings?.filter((finding) => {
    const control = finding.control;
    if (!control) return false;

    const matchesSearch =
      searchQuery === '' ||
      control.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      control.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      control.objective.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesDomain = domainFilter === '' || control.domain === domainFilter;
    const matchesStatus = statusFilter === '' || finding.status === statusFilter;

    return matchesSearch && matchesDomain && matchesStatus;
  });

  const stats = {
    total: findings?.length || 0,
    met: findings?.filter((f) => f.status === 'Met').length || 0,
    notMet: findings?.filter((f) => f.status === 'Not Met').length || 0,
    partial: findings?.filter((f) => f.status === 'Partially Met').length || 0,
    na: findings?.filter((f) => f.status === 'Not Applicable').length || 0,
  };

  return (
    <MainLayout>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Control Findings</h1>
          <p className="text-gray-600 mt-2">Review and assess CMMC Level 2 controls</p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div className="card p-4">
            <p className="text-sm text-gray-600">Total</p>
            <p className="text-2xl font-bold text-gray-900">{stats.total}</p>
          </div>
          <div className="card p-4">
            <p className="text-sm text-gray-600">Met</p>
            <p className="text-2xl font-bold text-success-600">{stats.met}</p>
          </div>
          <div className="card p-4">
            <p className="text-sm text-gray-600">Not Met</p>
            <p className="text-2xl font-bold text-danger-600">{stats.notMet}</p>
          </div>
          <div className="card p-4">
            <p className="text-sm text-gray-600">Partial</p>
            <p className="text-2xl font-bold text-warning-600">{stats.partial}</p>
          </div>
          <div className="card p-4">
            <p className="text-sm text-gray-600">N/A</p>
            <p className="text-2xl font-bold text-gray-600">{stats.na}</p>
          </div>
        </div>

        {/* Filters */}
        <div className="card p-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="md:col-span-2">
              <Input
                placeholder="Search controls..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
            <Select
              value={domainFilter}
              onChange={setDomainFilter}
              options={[
                { value: '', label: 'All Domains' },
                ...domains.map((d) => ({ value: d, label: d })),
              ]}
            />
            <Select
              value={statusFilter}
              onChange={setStatusFilter}
              options={[
                { value: '', label: 'All Statuses' },
                { value: 'Met', label: 'Met' },
                { value: 'Not Met', label: 'Not Met' },
                { value: 'Partially Met', label: 'Partially Met' },
                { value: 'Not Applicable', label: 'Not Applicable' },
              ]}
            />
          </div>
        </div>

        {/* Controls List */}
        {isLoading ? (
          <div className="text-center py-12">
            <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-primary-600 border-r-transparent"></div>
            <p className="mt-2 text-gray-600">Loading controls...</p>
          </div>
        ) : filteredFindings && filteredFindings.length > 0 ? (
          <div className="space-y-4">
            {filteredFindings.map((finding) => (
              finding.control && (
                <ControlCard
                  key={finding.controlId}
                  control={finding.control}
                  finding={finding}
                  onStatusChange={handleStatusChange}
                />
              )
            ))}
          </div>
        ) : (
          <div className="card p-12 text-center">
            <p className="text-gray-600">No controls found matching your filters</p>
          </div>
        )}
      </div>
    </MainLayout>
  );
};
