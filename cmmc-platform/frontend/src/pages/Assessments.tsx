import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { MainLayout } from '@/components/layout';
import { Button } from '@/components/common/Button';
import { Input } from '@/components/common/Input';
import { Select } from '@/components/common/Select';
import { Modal } from '@/components/common/Modal';
import { AssessmentCard } from '@/components/assessment';
import { useAssessments } from '@/hooks/useAssessments';
import { Plus } from 'lucide-react';
import { CreateAssessmentDto } from '@/types';

export const Assessments: React.FC = () => {
  const navigate = useNavigate();
  const { assessments, isLoading, createAssessment, isCreating } = useAssessments();
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  const [newAssessment, setNewAssessment] = useState<CreateAssessmentDto>({
    name: '',
    description: '',
    assessmentType: 'CMMC Level 2',
    scope: '',
    startDate: new Date().toISOString().split('T')[0],
    targetCompletionDate: '',
  });

  const handleCreateAssessment = async () => {
    try {
      const assessment = await createAssessment(newAssessment);
      setIsCreateModalOpen(false);
      navigate(`/assessments/${assessment.id}`);
      setNewAssessment({
        name: '',
        description: '',
        assessmentType: 'CMMC Level 2',
        scope: '',
        startDate: new Date().toISOString().split('T')[0],
        targetCompletionDate: '',
      });
    } catch (error) {
      console.error('Failed to create assessment:', error);
    }
  };

  const filteredAssessments = assessments?.filter((assessment) => {
    const matchesSearch =
      searchQuery === '' ||
      assessment.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      assessment.description?.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesStatus = statusFilter === '' || assessment.status === statusFilter;

    return matchesSearch && matchesStatus;
  });

  return (
    <MainLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Assessments</h1>
            <p className="text-gray-600 mt-2">Manage your CMMC compliance assessments</p>
          </div>
          <Button
            variant="primary"
            size="md"
            onClick={() => setIsCreateModalOpen(true)}
          >
            <Plus className="w-5 h-5 mr-2" />
            New Assessment
          </Button>
        </div>

        {/* Filters */}
        <div className="card p-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="md:col-span-2">
              <Input
                placeholder="Search assessments..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full"
              />
            </div>
            <Select
              value={statusFilter}
              onChange={setStatusFilter}
              options={[
                { value: '', label: 'All Statuses' },
                { value: 'Draft', label: 'Draft' },
                { value: 'In Progress', label: 'In Progress' },
                { value: 'Under Review', label: 'Under Review' },
                { value: 'Remediation', label: 'Remediation' },
                { value: 'Final Review', label: 'Final Review' },
                { value: 'Completed', label: 'Completed' },
              ]}
            />
          </div>
        </div>

        {/* Assessments Grid */}
        {isLoading ? (
          <div className="text-center py-12">
            <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-primary-600 border-r-transparent"></div>
            <p className="mt-2 text-gray-600">Loading assessments...</p>
          </div>
        ) : filteredAssessments && filteredAssessments.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredAssessments.map((assessment) => (
              <AssessmentCard
                key={assessment.id}
                assessment={assessment}
                onClick={() => navigate(`/assessments/${assessment.id}`)}
              />
            ))}
          </div>
        ) : (
          <div className="card p-12 text-center">
            <p className="text-gray-600">
              {searchQuery || statusFilter
                ? 'No assessments match your filters'
                : 'No assessments yet. Create your first assessment to get started.'}
            </p>
          </div>
        )}

        {/* Create Assessment Modal */}
        <Modal
          isOpen={isCreateModalOpen}
          onClose={() => setIsCreateModalOpen(false)}
          title="Create New Assessment"
          size="lg"
        >
          <div className="space-y-4">
            <Input
              label="Assessment Name"
              value={newAssessment.name}
              onChange={(e) => setNewAssessment({ ...newAssessment, name: e.target.value })}
              placeholder="Q1 2024 CMMC Assessment"
              required
            />

            <div className="space-y-2">
              <label className="block text-sm font-medium text-gray-700">Description</label>
              <textarea
                className="input"
                rows={3}
                value={newAssessment.description}
                onChange={(e) => setNewAssessment({ ...newAssessment, description: e.target.value })}
                placeholder="Describe the assessment scope and objectives..."
              />
            </div>

            <Select
              label="Assessment Type"
              value={newAssessment.assessmentType}
              onChange={(value) => setNewAssessment({ ...newAssessment, assessmentType: value })}
              options={[
                { value: 'CMMC Level 2', label: 'CMMC Level 2' },
                { value: 'NIST 800-171', label: 'NIST 800-171' },
                { value: 'Custom', label: 'Custom' },
              ]}
            />

            <div className="grid grid-cols-2 gap-4">
              <Input
                label="Start Date"
                type="date"
                value={newAssessment.startDate}
                onChange={(e) => setNewAssessment({ ...newAssessment, startDate: e.target.value })}
              />

              <Input
                label="Target Completion Date"
                type="date"
                value={newAssessment.targetCompletionDate}
                onChange={(e) =>
                  setNewAssessment({ ...newAssessment, targetCompletionDate: e.target.value })
                }
              />
            </div>

            <div className="space-y-2">
              <label className="block text-sm font-medium text-gray-700">Scope</label>
              <textarea
                className="input"
                rows={3}
                value={newAssessment.scope}
                onChange={(e) => setNewAssessment({ ...newAssessment, scope: e.target.value })}
                placeholder="Define the assessment scope, systems, and boundaries..."
              />
            </div>

            <div className="flex justify-end space-x-3 pt-4">
              <Button
                variant="secondary"
                onClick={() => setIsCreateModalOpen(false)}
                disabled={isCreating}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                onClick={handleCreateAssessment}
                loading={isCreating}
                disabled={!newAssessment.name || isCreating}
              >
                Create Assessment
              </Button>
            </div>
          </div>
        </Modal>
      </div>
    </MainLayout>
  );
};
