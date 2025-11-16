import { useQuery } from '@tanstack/react-query';
import { assessmentsAPI } from '../services/api';
import useAuthStore from '../stores/authStore';
import { useNavigate } from 'react-router-dom';
import { Plus, FileText, Calendar, TrendingUp } from 'lucide-react';

export default function Assessments() {
  const user = useAuthStore((state) => state.user);
  const navigate = useNavigate();

  const { data: assessments, isLoading } = useQuery({
    queryKey: ['assessments', user?.organizationId],
    queryFn: () => assessmentsAPI.list(user?.organizationId).then(res => res.data),
    enabled: !!user?.organizationId,
  });

  const getStatusColor = (status) => {
    const colors = {
      planning: 'bg-gray-100 text-gray-800',
      in_progress: 'bg-blue-100 text-blue-800',
      under_review: 'bg-yellow-100 text-yellow-800',
      complete: 'bg-green-100 text-green-800',
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Assessments</h1>
          <p className="mt-1 text-sm text-gray-500">
            Manage your CMMC compliance assessments
          </p>
        </div>
        <button className="btn btn-primary">
          <Plus className="w-4 h-4 mr-2" />
          New Assessment
        </button>
      </div>

      {/* Assessments Grid */}
      {!assessments || assessments.length === 0 ? (
        <div className="card text-center py-12">
          <FileText className="w-12 h-12 mx-auto text-gray-400 mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            No assessments yet
          </h3>
          <p className="text-gray-600 mb-6">
            Get started by creating your first CMMC assessment
          </p>
          <button className="btn btn-primary">
            <Plus className="w-4 h-4 mr-2" />
            Create Assessment
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {assessments.map((assessment) => (
            <div
              key={assessment.id}
              className="card hover:shadow-md transition-shadow cursor-pointer"
              onClick={() => navigate(`/assessments/${assessment.id}`)}
            >
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-gray-900 mb-1">
                    {assessment.name}
                  </h3>
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(assessment.status)}`}>
                    {assessment.status?.replace('_', ' ')}
                  </span>
                </div>
              </div>

              <div className="space-y-3">
                <div className="flex items-center text-sm text-gray-600">
                  <TrendingUp className="w-4 h-4 mr-2" />
                  CMMC Level {assessment.cmmc_level || 2}
                </div>

                <div className="flex items-center text-sm text-gray-600">
                  <Calendar className="w-4 h-4 mr-2" />
                  Target: {assessment.target_completion_date ? new Date(assessment.target_completion_date).toLocaleDateString() : 'Not set'}
                </div>

                <div className="pt-3 border-t border-gray-200">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-600">Progress</span>
                    <span className="font-medium text-gray-900">{assessment.progress || 0}%</span>
                  </div>
                  <div className="mt-2 w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-primary-600 h-2 rounded-full"
                      style={{ width: `${assessment.progress || 0}%` }}
                    />
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
