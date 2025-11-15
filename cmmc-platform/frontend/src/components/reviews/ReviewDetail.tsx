/**
 * Review Detail Component
 * Detailed view for reviewing AI-generated content with feedback interface
 */

import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useParams, useNavigate } from 'react-router-dom';
import {
  CheckCircle2,
  XCircle,
  AlertCircle,
  MessageSquare,
  Send,
  ThumbsUp,
  ThumbsDown,
  Clock,
  User,
  ArrowLeft,
  Star,
  FileText,
  Lightbulb,
  GitCompare,
} from 'lucide-react';
import { api } from '../../services/api';

interface ReviewRequest {
  id: string;
  item_type: string;
  item_id: string;
  item_name: string;
  ai_generated_content: any;
  reference_content: any;
  context_data: any;
  ai_confidence_score: number | null;
  ai_model_version: string | null;
  status: string;
  priority: string;
  required_reviewers: number;
  approved_count: number;
  assigned_to: string[];
  requested_at: string;
  due_date: string | null;
  created_at: string;
}

interface Review {
  id: string;
  reviewer_id: string;
  reviewer_name: string;
  decision: string;
  overall_feedback: string;
  detailed_feedback: any;
  suggested_changes: any;
  accuracy_rating: number | null;
  completeness_rating: number | null;
  quality_rating: number | null;
  submitted_at: string;
}

interface Comment {
  id: string;
  user_id: string;
  user_name: string;
  comment_text: string;
  parent_comment_id: string | null;
  highlighted_section: string | null;
  highlighted_text: string | null;
  is_internal: boolean;
  is_resolved: boolean;
  created_at: string;
}

export const ReviewDetail: React.FC = () => {
  const { reviewId } = useParams<{ reviewId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  // Form state
  const [decision, setDecision] = useState<string>('approve');
  const [overallFeedback, setOverallFeedback] = useState<string>('');
  const [accuracyRating, setAccuracyRating] = useState<number>(5);
  const [completenessRating, setCompletenessRating] = useState<number>(5);
  const [qualityRating, setQualityRating] = useState<number>(5);
  const [suggestedChanges, setSuggestedChanges] = useState<string>('');
  const [newComment, setNewComment] = useState<string>('');
  const [showComparison, setShowComparison] = useState<boolean>(false);

  // Fetch review request
  const { data: reviewRequest, isLoading } = useQuery<ReviewRequest>({
    queryKey: ['review-request', reviewId],
    queryFn: async () => {
      const response = await api.get(`/reviews/requests/${reviewId}`);
      return response.data;
    },
  });

  // Fetch existing reviews
  const { data: existingReviews } = useQuery<Review[]>({
    queryKey: ['review-submissions', reviewId],
    queryFn: async () => {
      const response = await api.get(`/reviews/requests/${reviewId}/reviews`);
      return response.data;
    },
    enabled: !!reviewId,
  });

  // Fetch comments
  const { data: comments } = useQuery<Comment[]>({
    queryKey: ['review-comments', reviewId],
    queryFn: async () => {
      const response = await api.get(`/reviews/requests/${reviewId}/comments`);
      return response.data;
    },
    enabled: !!reviewId,
  });

  // Submit review mutation
  const submitMutation = useMutation({
    mutationFn: async (data: any) => {
      const response = await api.post(`/reviews/requests/${reviewId}/submit`, data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['review-request', reviewId] });
      queryClient.invalidateQueries({ queryKey: ['review-submissions', reviewId] });
      queryClient.invalidateQueries({ queryKey: ['my-review-queue'] });
      navigate('/reviews');
    },
  });

  // Add comment mutation
  const commentMutation = useMutation({
    mutationFn: async (commentText: string) => {
      const response = await api.post(`/reviews/requests/${reviewId}/comments`, {
        comment_text: commentText,
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['review-comments', reviewId] });
      setNewComment('');
    },
  });

  const handleSubmitReview = () => {
    submitMutation.mutate({
      decision,
      overall_feedback: overallFeedback,
      accuracy_rating: accuracyRating,
      completeness_rating: completenessRating,
      quality_rating: qualityRating,
      suggested_changes: suggestedChanges ? { text: suggestedChanges } : null,
    });
  };

  const handleAddComment = () => {
    if (newComment.trim()) {
      commentMutation.mutate(newComment);
    }
  };

  const renderRatingStars = (rating: number, onChange: (rating: number) => void) => {
    return (
      <div className="flex items-center gap-1">
        {[1, 2, 3, 4, 5].map((star) => (
          <button
            key={star}
            type="button"
            onClick={() => onChange(star)}
            className="focus:outline-none"
          >
            <Star
              className={`w-6 h-6 ${
                star <= rating
                  ? 'fill-yellow-400 text-yellow-400'
                  : 'text-gray-300'
              }`}
            />
          </button>
        ))}
        <span className="ml-2 text-sm text-gray-600">{rating}/5</span>
      </div>
    );
  };

  const renderContent = (content: any, title: string) => {
    if (!content) return null;

    return (
      <div className="bg-gray-50 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">{title}</h3>
        <div className="prose max-w-none">
          {typeof content === 'string' ? (
            <p className="text-gray-700 whitespace-pre-wrap">{content}</p>
          ) : (
            <pre className="text-sm text-gray-700 bg-white p-4 rounded border overflow-x-auto">
              {JSON.stringify(content, null, 2)}
            </pre>
          )}
        </div>
      </div>
    );
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Clock className="w-12 h-12 text-gray-400 animate-spin" />
      </div>
    );
  }

  if (!reviewRequest) {
    return (
      <div className="text-center py-12">
        <AlertCircle className="w-16 h-16 text-red-600 mx-auto mb-4" />
        <h3 className="text-xl font-semibold text-gray-900 mb-2">
          Review Not Found
        </h3>
        <p className="text-gray-600 mb-4">
          The requested review could not be found.
        </p>
        <button
          onClick={() => navigate('/reviews')}
          className="text-blue-600 hover:text-blue-700"
        >
          Return to Review Queue
        </button>
      </div>
    );
  }

  const hasSubmittedReview = existingReviews?.some(
    (r) => r.reviewer_id === 'current-user-id' // Would come from auth context
  );

  return (
    <div className="space-y-6 pb-20">
      {/* Header */}
      <div className="bg-white rounded-lg shadow p-6">
        <button
          onClick={() => navigate('/reviews')}
          className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-4"
        >
          <ArrowLeft className="w-5 h-5" />
          Back to Review Queue
        </button>

        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-3xl font-bold text-gray-900">
                {reviewRequest.item_name}
              </h1>
              <span
                className={`px-3 py-1 rounded-full text-xs font-semibold ${
                  reviewRequest.priority === 'critical'
                    ? 'bg-red-100 text-red-800'
                    : reviewRequest.priority === 'high'
                    ? 'bg-orange-100 text-orange-800'
                    : reviewRequest.priority === 'medium'
                    ? 'bg-yellow-100 text-yellow-800'
                    : 'bg-blue-100 text-blue-800'
                }`}
              >
                {reviewRequest.priority.toUpperCase()}
              </span>
            </div>
            <p className="text-gray-600">
              {reviewRequest.item_type
                .split('_')
                .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
                .join(' ')}
            </p>
          </div>

          <div className="text-right">
            <div className="text-sm text-gray-600">
              {reviewRequest.approved_count}/{reviewRequest.required_reviewers}{' '}
              Approved
            </div>
            {reviewRequest.ai_confidence_score && (
              <div className="text-sm text-gray-600 mt-1">
                AI Confidence: {(reviewRequest.ai_confidence_score * 100).toFixed(0)}%
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Content Comparison Toggle */}
      {reviewRequest.reference_content && (
        <div className="flex items-center justify-center">
          <button
            onClick={() => setShowComparison(!showComparison)}
            className="flex items-center gap-2 px-4 py-2 bg-white rounded-lg shadow hover:shadow-md transition-shadow"
          >
            <GitCompare className="w-5 h-5 text-blue-600" />
            <span className="text-sm font-medium">
              {showComparison ? 'Hide' : 'Show'} Comparison
            </span>
          </button>
        </div>
      )}

      {/* Content Display */}
      <div
        className={`grid ${
          showComparison && reviewRequest.reference_content ? 'grid-cols-2' : 'grid-cols-1'
        } gap-6`}
      >
        {/* AI Generated Content */}
        <div>
          {renderContent(reviewRequest.ai_generated_content, 'AI-Generated Content')}
        </div>

        {/* Reference Content */}
        {showComparison && reviewRequest.reference_content && (
          <div>
            {renderContent(reviewRequest.reference_content, 'Reference Content')}
          </div>
        )}
      </div>

      {/* Context Information */}
      {reviewRequest.context_data && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-blue-900 mb-3 flex items-center gap-2">
            <Lightbulb className="w-5 h-5" />
            Context Information
          </h3>
          <div className="text-sm text-blue-800">
            <pre className="whitespace-pre-wrap">
              {JSON.stringify(reviewRequest.context_data, null, 2)}
            </pre>
          </div>
        </div>
      )}

      {/* Existing Reviews */}
      {existingReviews && existingReviews.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-xl font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <User className="w-6 h-6 text-blue-600" />
            Previous Reviews ({existingReviews.length})
          </h3>
          <div className="space-y-4">
            {existingReviews.map((review) => (
              <div
                key={review.id}
                className="border border-gray-200 rounded-lg p-4"
              >
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <div className="font-semibold text-gray-900">
                      {review.reviewer_name || 'Anonymous Reviewer'}
                    </div>
                    <div className="text-sm text-gray-600">
                      {new Date(review.submitted_at).toLocaleString()}
                    </div>
                  </div>
                  <span
                    className={`px-3 py-1 rounded-full text-xs font-semibold ${
                      review.decision === 'approve'
                        ? 'bg-green-100 text-green-800'
                        : review.decision === 'reject'
                        ? 'bg-red-100 text-red-800'
                        : 'bg-yellow-100 text-yellow-800'
                    }`}
                  >
                    {review.decision.replace('_', ' ').toUpperCase()}
                  </span>
                </div>

                {review.overall_feedback && (
                  <p className="text-gray-700 mb-3">{review.overall_feedback}</p>
                )}

                <div className="flex items-center gap-6 text-sm text-gray-600">
                  {review.accuracy_rating && (
                    <span>Accuracy: {review.accuracy_rating}/5</span>
                  )}
                  {review.completeness_rating && (
                    <span>Completeness: {review.completeness_rating}/5</span>
                  )}
                  {review.quality_rating && (
                    <span>Quality: {review.quality_rating}/5</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Review Form */}
      {!hasSubmittedReview && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-xl font-semibold text-gray-900 mb-6 flex items-center gap-2">
            <CheckCircle2 className="w-6 h-6 text-green-600" />
            Submit Your Review
          </h3>

          <div className="space-y-6">
            {/* Decision */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-3">
                Decision
              </label>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {[
                  {
                    value: 'approve',
                    label: 'Approve',
                    icon: CheckCircle2,
                    color: 'green',
                  },
                  {
                    value: 'approve_with_changes',
                    label: 'Approve with Changes',
                    icon: ThumbsUp,
                    color: 'blue',
                  },
                  {
                    value: 'request_revision',
                    label: 'Request Revision',
                    icon: AlertCircle,
                    color: 'yellow',
                  },
                  { value: 'reject', label: 'Reject', icon: XCircle, color: 'red' },
                ].map((option) => {
                  const Icon = option.icon;
                  const isSelected = decision === option.value;
                  return (
                    <button
                      key={option.value}
                      type="button"
                      onClick={() => setDecision(option.value)}
                      className={`p-4 border-2 rounded-lg transition-all ${
                        isSelected
                          ? `border-${option.color}-500 bg-${option.color}-50`
                          : 'border-gray-200 hover:border-gray-300'
                      }`}
                    >
                      <Icon
                        className={`w-6 h-6 mx-auto mb-2 ${
                          isSelected ? `text-${option.color}-600` : 'text-gray-400'
                        }`}
                      />
                      <div className="text-sm font-medium text-gray-900">
                        {option.label}
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Overall Feedback */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Overall Feedback
              </label>
              <textarea
                value={overallFeedback}
                onChange={(e) => setOverallFeedback(e.target.value)}
                rows={4}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                placeholder="Provide your overall assessment..."
              />
            </div>

            {/* Ratings */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Accuracy
                </label>
                {renderRatingStars(accuracyRating, setAccuracyRating)}
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Completeness
                </label>
                {renderRatingStars(completenessRating, setCompletenessRating)}
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Quality
                </label>
                {renderRatingStars(qualityRating, setQualityRating)}
              </div>
            </div>

            {/* Suggested Changes */}
            {(decision === 'approve_with_changes' ||
              decision === 'request_revision') && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Suggested Changes
                </label>
                <textarea
                  value={suggestedChanges}
                  onChange={(e) => setSuggestedChanges(e.target.value)}
                  rows={4}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="Describe the changes you recommend..."
                />
              </div>
            )}

            {/* Submit Button */}
            <div className="flex justify-end gap-3">
              <button
                onClick={() => navigate('/reviews')}
                className="px-6 py-3 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 font-medium"
              >
                Cancel
              </button>
              <button
                onClick={handleSubmitReview}
                disabled={submitMutation.isPending}
                className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium disabled:bg-gray-400 flex items-center gap-2"
              >
                <Send className="w-5 h-5" />
                {submitMutation.isPending ? 'Submitting...' : 'Submit Review'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Comments Section */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-xl font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <MessageSquare className="w-6 h-6 text-blue-600" />
          Discussion ({comments?.length || 0})
        </h3>

        {/* Comments List */}
        <div className="space-y-4 mb-6">
          {comments?.map((comment) => (
            <div key={comment.id} className="border-l-4 border-blue-200 pl-4 py-2">
              <div className="flex items-start justify-between mb-2">
                <div>
                  <span className="font-semibold text-gray-900">
                    {comment.user_name}
                  </span>
                  <span className="text-sm text-gray-500 ml-2">
                    {new Date(comment.created_at).toLocaleString()}
                  </span>
                </div>
                {comment.is_internal && (
                  <span className="px-2 py-1 bg-purple-100 text-purple-800 text-xs rounded">
                    Internal
                  </span>
                )}
              </div>
              <p className="text-gray-700">{comment.comment_text}</p>
            </div>
          ))}
        </div>

        {/* Add Comment */}
        <div className="border-t pt-4">
          <textarea
            value={newComment}
            onChange={(e) => setNewComment(e.target.value)}
            rows={3}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 mb-3"
            placeholder="Add a comment to the discussion..."
          />
          <button
            onClick={handleAddComment}
            disabled={!newComment.trim() || commentMutation.isPending}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 flex items-center gap-2"
          >
            <MessageSquare className="w-4 h-4" />
            {commentMutation.isPending ? 'Adding...' : 'Add Comment'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ReviewDetail;
