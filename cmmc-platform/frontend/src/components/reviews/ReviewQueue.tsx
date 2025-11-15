/**
 * Review Queue Component
 * Dashboard showing pending reviews assigned to the current user
 */

import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  CheckCircle2,
  Clock,
  AlertTriangle,
  FileText,
  Filter,
  Search,
  ChevronRight,
  TrendingUp,
  BarChart3,
  Calendar,
} from 'lucide-react';
import { api } from '../../services/api';
import { Link } from 'react-router-dom';

interface ReviewRequest {
  id: string;
  item_type: string;
  item_id: string;
  item_name: string;
  priority: 'low' | 'medium' | 'high' | 'critical';
  status: string;
  requested_at: string;
  due_date: string | null;
  required_reviewers: number;
  approved_count: number;
  ai_confidence_score: number | null;
  assessment_id: string | null;
}

interface ReviewStats {
  total_reviews: number;
  pending_reviews: number;
  approved_reviews: number;
  rejected_reviews: number;
  avg_review_time_hours: number;
  overdue_reviews: number;
  ai_accuracy_rate: number;
}

export const ReviewQueue: React.FC = () => {
  const [filterPriority, setFilterPriority] = useState<string>('all');
  const [filterItemType, setFilterItemType] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Fetch user's review queue
  const { data: reviewQueue, isLoading: queueLoading } = useQuery<ReviewRequest[]>({
    queryKey: ['my-review-queue'],
    queryFn: async () => {
      const response = await api.get('/reviews/my-queue');
      return response.data;
    },
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  // Fetch organization stats
  const { data: stats } = useQuery<ReviewStats>({
    queryKey: ['review-stats'],
    queryFn: async () => {
      const response = await api.get('/reviews/stats');
      return response.data;
    },
  });

  const getPriorityColor = (priority: string): string => {
    const colors: Record<string, string> = {
      critical: 'bg-red-100 text-red-800 border-red-300',
      high: 'bg-orange-100 text-orange-800 border-orange-300',
      medium: 'bg-yellow-100 text-yellow-800 border-yellow-300',
      low: 'bg-blue-100 text-blue-800 border-blue-300',
    };
    return colors[priority] || 'bg-gray-100 text-gray-800';
  };

  const getPriorityBadgeColor = (priority: string): string => {
    const colors: Record<string, string> = {
      critical: 'bg-red-600',
      high: 'bg-orange-600',
      medium: 'bg-yellow-600',
      low: 'bg-blue-600',
    };
    return colors[priority] || 'bg-gray-600';
  };

  const getItemTypeIcon = (itemType: string) => {
    const icons: Record<string, any> = {
      control_assessment: FileText,
      gap_analysis: TrendingUp,
      recommendation: CheckCircle2,
      evidence_analysis: BarChart3,
      report_finding: FileText,
      cost_forecast: BarChart3,
    };
    const Icon = icons[itemType] || FileText;
    return <Icon className="w-5 h-5" />;
  };

  const formatItemType = (itemType: string): string => {
    return itemType
      .split('_')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  const isOverdue = (dueDate: string | null): boolean => {
    if (!dueDate) return false;
    return new Date(dueDate) < new Date();
  };

  const formatDueDate = (dueDate: string | null): string => {
    if (!dueDate) return 'No deadline';
    const date = new Date(dueDate);
    const now = new Date();
    const diffMs = date.getTime() - now.getTime();
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffHours / 24);

    if (diffMs < 0) {
      const overdueDays = Math.abs(diffDays);
      return `Overdue by ${overdueDays} day${overdueDays !== 1 ? 's' : ''}`;
    } else if (diffDays === 0) {
      return `Due in ${diffHours} hour${diffHours !== 1 ? 's' : ''}`;
    } else if (diffDays === 1) {
      return 'Due tomorrow';
    } else if (diffDays < 7) {
      return `Due in ${diffDays} days`;
    } else {
      return date.toLocaleDateString();
    }
  };

  // Filter reviews
  const filteredReviews = React.useMemo(() => {
    if (!reviewQueue) return [];

    return reviewQueue.filter((review) => {
      // Priority filter
      if (filterPriority !== 'all' && review.priority !== filterPriority) {
        return false;
      }

      // Item type filter
      if (filterItemType !== 'all' && review.item_type !== filterItemType) {
        return false;
      }

      // Search filter
      if (searchQuery) {
        const query = searchQuery.toLowerCase();
        return (
          review.item_name.toLowerCase().includes(query) ||
          review.item_id.toLowerCase().includes(query) ||
          formatItemType(review.item_type).toLowerCase().includes(query)
        );
      }

      return true;
    });
  }, [reviewQueue, filterPriority, filterItemType, searchQuery]);

  // Get unique item types for filter
  const itemTypes = React.useMemo(() => {
    if (!reviewQueue) return [];
    return Array.from(new Set(reviewQueue.map((r) => r.item_type)));
  }, [reviewQueue]);

  // Count by priority
  const priorityCounts = React.useMemo(() => {
    if (!reviewQueue) return { critical: 0, high: 0, medium: 0, low: 0 };
    return reviewQueue.reduce(
      (acc, review) => {
        acc[review.priority] = (acc[review.priority] || 0) + 1;
        return acc;
      },
      { critical: 0, high: 0, medium: 0, low: 0 } as Record<string, number>
    );
  }, [reviewQueue]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Review Queue</h1>
          <p className="text-gray-600 mt-1">
            AI-generated content awaiting your validation
          </p>
        </div>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Pending Reviews</p>
                <p className="text-3xl font-bold text-blue-600 mt-1">
                  {reviewQueue?.length || 0}
                </p>
              </div>
              <Clock className="w-10 h-10 text-blue-600 opacity-20" />
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Overdue</p>
                <p className="text-3xl font-bold text-red-600 mt-1">
                  {reviewQueue?.filter((r) => isOverdue(r.due_date)).length || 0}
                </p>
              </div>
              <AlertTriangle className="w-10 h-10 text-red-600 opacity-20" />
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">AI Accuracy</p>
                <p className="text-3xl font-bold text-green-600 mt-1">
                  {stats.ai_accuracy_rate?.toFixed(0) || 0}%
                </p>
              </div>
              <TrendingUp className="w-10 h-10 text-green-600 opacity-20" />
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Avg Review Time</p>
                <p className="text-3xl font-bold text-purple-600 mt-1">
                  {stats.avg_review_time_hours?.toFixed(1) || 0}h
                </p>
              </div>
              <BarChart3 className="w-10 h-10 text-purple-600 opacity-20" />
            </div>
          </div>
        </div>
      )}

      {/* Priority Quick Filters */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex items-center gap-4 flex-wrap">
          <span className="text-sm font-medium text-gray-700">Quick Filter:</span>
          <button
            onClick={() => setFilterPriority('all')}
            className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
              filterPriority === 'all'
                ? 'bg-gray-800 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            All ({reviewQueue?.length || 0})
          </button>
          <button
            onClick={() => setFilterPriority('critical')}
            className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
              filterPriority === 'critical'
                ? 'bg-red-600 text-white'
                : 'bg-red-100 text-red-700 hover:bg-red-200'
            }`}
          >
            Critical ({priorityCounts.critical})
          </button>
          <button
            onClick={() => setFilterPriority('high')}
            className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
              filterPriority === 'high'
                ? 'bg-orange-600 text-white'
                : 'bg-orange-100 text-orange-700 hover:bg-orange-200'
            }`}
          >
            High ({priorityCounts.high})
          </button>
          <button
            onClick={() => setFilterPriority('medium')}
            className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
              filterPriority === 'medium'
                ? 'bg-yellow-600 text-white'
                : 'bg-yellow-100 text-yellow-700 hover:bg-yellow-200'
            }`}
          >
            Medium ({priorityCounts.medium})
          </button>
        </div>
      </div>

      {/* Filters and Search */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              placeholder="Search reviews..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Item Type Filter */}
          <div className="relative">
            <Filter className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
            <select
              value={filterItemType}
              onChange={(e) => setFilterItemType(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 appearance-none"
            >
              <option value="all">All Types</option>
              {itemTypes.map((type) => (
                <option key={type} value={type}>
                  {formatItemType(type)}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Review List */}
      <div className="space-y-3">
        {queueLoading ? (
          <div className="bg-white rounded-lg shadow p-12 text-center">
            <Clock className="w-12 h-12 text-gray-400 mx-auto mb-4 animate-spin" />
            <p className="text-gray-600">Loading reviews...</p>
          </div>
        ) : filteredReviews.length === 0 ? (
          <div className="bg-white rounded-lg shadow p-12 text-center">
            <CheckCircle2 className="w-16 h-16 text-green-600 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-gray-900 mb-2">
              {reviewQueue?.length === 0
                ? "You're all caught up!"
                : 'No matching reviews'}
            </h3>
            <p className="text-gray-600">
              {reviewQueue?.length === 0
                ? 'No pending reviews at the moment.'
                : 'Try adjusting your filters to see more results.'}
            </p>
          </div>
        ) : (
          filteredReviews.map((review) => (
            <Link
              key={review.id}
              to={`/reviews/${review.id}`}
              className="block bg-white rounded-lg shadow hover:shadow-lg transition-shadow border-l-4 border-transparent hover:border-blue-500"
            >
              <div className="p-6">
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-4 flex-1">
                    {/* Priority Badge */}
                    <div
                      className={`w-2 h-2 rounded-full mt-2 ${getPriorityBadgeColor(
                        review.priority
                      )}`}
                    />

                    {/* Icon */}
                    <div className="text-gray-600">
                      {getItemTypeIcon(review.item_type)}
                    </div>

                    {/* Content */}
                    <div className="flex-1">
                      <div className="flex items-start gap-3 mb-2">
                        <h3 className="text-lg font-semibold text-gray-900">
                          {review.item_name}
                        </h3>
                        <span
                          className={`px-2 py-1 rounded-full text-xs font-medium border ${getPriorityColor(
                            review.priority
                          )}`}
                        >
                          {review.priority.toUpperCase()}
                        </span>
                      </div>

                      <div className="flex items-center gap-6 text-sm text-gray-600">
                        <span className="flex items-center gap-1">
                          <FileText className="w-4 h-4" />
                          {formatItemType(review.item_type)}
                        </span>
                        {review.ai_confidence_score && (
                          <span className="flex items-center gap-1">
                            <TrendingUp className="w-4 h-4" />
                            AI Confidence:{' '}
                            {(review.ai_confidence_score * 100).toFixed(0)}%
                          </span>
                        )}
                        <span className="flex items-center gap-1">
                          <CheckCircle2 className="w-4 h-4" />
                          {review.approved_count}/{review.required_reviewers} approved
                        </span>
                      </div>

                      {/* Due Date */}
                      {review.due_date && (
                        <div
                          className={`mt-2 flex items-center gap-2 text-sm ${
                            isOverdue(review.due_date)
                              ? 'text-red-600 font-semibold'
                              : 'text-gray-600'
                          }`}
                        >
                          {isOverdue(review.due_date) ? (
                            <AlertTriangle className="w-4 h-4" />
                          ) : (
                            <Calendar className="w-4 h-4" />
                          )}
                          {formatDueDate(review.due_date)}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Arrow */}
                  <ChevronRight className="w-6 h-6 text-gray-400" />
                </div>
              </div>
            </Link>
          ))
        )}
      </div>
    </div>
  );
};

export default ReviewQueue;
