/**
 * RAG Query Component
 * Semantic search interface for CMMC documentation
 */

import React, { useState } from 'react';
import { Button, Input, Card, Badge } from '../common';
import { queryRAG } from '../../services/document-management';
import type { RAGQueryResponse, RetrievedChunk } from '../../types/document-management';

interface RAGQueryProps {
  organizationId?: string;
  assessmentId?: string;
  controlId?: string;
  onResultClick?: (chunk: RetrievedChunk) => void;
}

export const RAGQuery: React.FC<RAGQueryProps> = ({
  organizationId,
  assessmentId,
  controlId,
  onResultClick,
}) => {
  const [query, setQuery] = useState('');
  const [topK, setTopK] = useState(5);
  const [minSimilarity, setMinSimilarity] = useState(0.5);
  const [searching, setSearching] = useState(false);
  const [results, setResults] = useState<RAGQueryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async () => {
    if (!query.trim()) {
      setError('Please enter a search query');
      return;
    }

    setSearching(true);
    setError(null);
    setResults(null);

    try {
      const response = await queryRAG({
        query: query.trim(),
        top_k: topK,
        min_similarity: minSimilarity,
        organization_id: organizationId,
        assessment_id: assessmentId,
        control_id: controlId,
        include_metadata: true,
      });

      setResults(response);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Search failed');
    } finally {
      setSearching(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSearch();
    }
  };

  const getSimilarityColor = (score: number): string => {
    if (score >= 0.8) return 'text-green-600';
    if (score >= 0.6) return 'text-yellow-600';
    return 'text-orange-600';
  };

  const getSimilarityBadge = (score: number) => {
    const percentage = (score * 100).toFixed(1);
    if (score >= 0.8) return <Badge variant="success">{percentage}%</Badge>;
    if (score >= 0.6) return <Badge variant="warning">{percentage}%</Badge>;
    return <Badge variant="secondary">{percentage}%</Badge>;
  };

  const highlightQuery = (text: string): string => {
    if (!query.trim()) return text;

    const words = query.trim().toLowerCase().split(/\s+/);
    let highlightedText = text;

    words.forEach((word) => {
      const regex = new RegExp(`(${word})`, 'gi');
      highlightedText = highlightedText.replace(
        regex,
        '<mark class="bg-yellow-200 font-semibold">$1</mark>'
      );
    });

    return highlightedText;
  };

  return (
    <div className="space-y-4">
      {/* Search input */}
      <Card>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold">Search CMMC Documentation</h3>
            {results && (
              <span className="text-sm text-gray-500">
                {results.context.chunks.length} results in{' '}
                {results.context.query_time_seconds.toFixed(3)}s
              </span>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Search Query
            </label>
            <textarea
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="e.g., What are the MFA requirements for CMMC Level 2?"
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              rows={3}
              disabled={searching}
            />
            <p className="mt-1 text-xs text-gray-500">
              Press Enter to search, Shift+Enter for new line
            </p>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Number of Results
              </label>
              <input
                type="number"
                value={topK}
                onChange={(e) => setTopK(parseInt(e.target.value) || 5)}
                min={1}
                max={20}
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                disabled={searching}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Min Similarity (0-1)
              </label>
              <input
                type="number"
                value={minSimilarity}
                onChange={(e) => setMinSimilarity(parseFloat(e.target.value) || 0.5)}
                min={0}
                max={1}
                step={0.1}
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                disabled={searching}
              />
            </div>
          </div>

          <Button onClick={handleSearch} disabled={searching || !query.trim()} variant="primary" className="w-full">
            {searching ? (
              <>
                <svg
                  className="animate-spin -ml-1 mr-2 h-4 w-4 text-white inline"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  />
                </svg>
                Searching...
              </>
            ) : (
              <>
                <svg
                  className="-ml-1 mr-2 h-4 w-4 inline"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                  />
                </svg>
                Search
              </>
            )}
          </Button>

          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-md">
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}
        </div>
      </Card>

      {/* Results */}
      {results && results.context.chunks.length > 0 && (
        <Card>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold">Search Results</h3>
              <div className="text-sm text-gray-500">
                Found in {results.context.sources.length} document
                {results.context.sources.length !== 1 ? 's' : ''}
              </div>
            </div>

            <div className="space-y-3">
              {results.context.chunks.map((chunk, index) => (
                <div
                  key={chunk.chunk_id}
                  className="p-4 border border-gray-200 rounded-lg hover:border-blue-300 hover:shadow-sm transition-all cursor-pointer"
                  onClick={() => onResultClick?.(chunk)}
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex-1">
                      <div className="flex items-center space-x-2">
                        <span className="text-xs font-medium text-gray-500">
                          #{index + 1}
                        </span>
                        <h4 className="text-sm font-semibold text-gray-900">
                          {chunk.document_title}
                        </h4>
                      </div>
                      <p className="text-xs text-gray-500 mt-1">
                        Chunk {chunk.chunk_index + 1}
                      </p>
                    </div>
                    {getSimilarityBadge(chunk.similarity_score)}
                  </div>

                  <div
                    className="text-sm text-gray-700 leading-relaxed"
                    dangerouslySetInnerHTML={{
                      __html: highlightQuery(chunk.chunk_text),
                    }}
                  />

                  {chunk.metadata && Object.keys(chunk.metadata).length > 0 && (
                    <div className="mt-3 pt-3 border-t border-gray-100">
                      <p className="text-xs text-gray-500">
                        Metadata: {JSON.stringify(chunk.metadata)}
                      </p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </Card>
      )}

      {/* No results */}
      {results && results.context.chunks.length === 0 && (
        <Card>
          <div className="text-center py-8 text-gray-500">
            <svg
              className="mx-auto h-12 w-12 text-gray-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <p className="mt-2">No results found</p>
            <p className="text-sm">Try adjusting your search query or lowering the minimum similarity threshold</p>
          </div>
        </Card>
      )}
    </div>
  );
};

export default RAGQuery;
