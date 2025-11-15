/**
 * Document Management and RAG API Service
 */

import axios from 'axios';
import type {
  UploadedDocument,
  DocumentUploadResponse,
  ProcessDocumentRequest,
  ProcessDocumentResponse,
  RAGQueryRequest,
  RAGQueryResponse,
  DocumentListRequest,
  DocumentListResponse,
  RAGStatsResponse,
} from '../types/document-management';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Create axios instance with auth
const api = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

/**
 * Upload a document for RAG processing
 */
export async function uploadDocument(
  file: File,
  title?: string,
  organizationId?: string,
  assessmentId?: string,
  controlId?: string,
  metadata?: Record<string, any>
): Promise<DocumentUploadResponse> {
  const formData = new FormData();
  formData.append('file', file);

  if (title) formData.append('title', title);
  if (organizationId) formData.append('organization_id', organizationId);
  if (assessmentId) formData.append('assessment_id', assessmentId);
  if (controlId) formData.append('control_id', controlId);
  if (metadata) formData.append('metadata', JSON.stringify(metadata));

  const response = await api.post<DocumentUploadResponse>(
    '/documents/upload',
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }
  );

  return response.data;
}

/**
 * Process a document (chunking and embedding)
 */
export async function processDocument(
  request: ProcessDocumentRequest
): Promise<ProcessDocumentResponse> {
  const response = await api.post<ProcessDocumentResponse>(
    '/documents/process',
    request
  );
  return response.data;
}

/**
 * List documents with filters
 */
export async function listDocuments(
  request: DocumentListRequest = {}
): Promise<DocumentListResponse> {
  const params = new URLSearchParams();

  if (request.organization_id) params.append('organization_id', request.organization_id);
  if (request.assessment_id) params.append('assessment_id', request.assessment_id);
  if (request.control_id) params.append('control_id', request.control_id);
  if (request.processed_only) params.append('processed_only', 'true');
  if (request.file_type) params.append('file_type', request.file_type);
  if (request.limit) params.append('limit', request.limit.toString());
  if (request.offset) params.append('offset', request.offset.toString());

  const response = await api.get<DocumentListResponse>(
    `/documents?${params.toString()}`
  );
  return response.data;
}

/**
 * Get document by ID
 */
export async function getDocument(documentId: string): Promise<UploadedDocument> {
  const response = await api.get<UploadedDocument>(`/documents/${documentId}`);
  return response.data;
}

/**
 * Delete a document
 */
export async function deleteDocument(documentId: string): Promise<{ success: boolean }> {
  const response = await api.delete<{ success: boolean }>(`/documents/${documentId}`);
  return response.data;
}

/**
 * Query documents using RAG
 */
export async function queryRAG(request: RAGQueryRequest): Promise<RAGQueryResponse> {
  const response = await api.post<RAGQueryResponse>('/rag/query', request);
  return response.data;
}

/**
 * Get RAG system statistics
 */
export async function getRAGStats(): Promise<RAGStatsResponse> {
  const response = await api.get<RAGStatsResponse>('/rag/stats');
  return response.data;
}

/**
 * Upload and process document in one call
 */
export async function uploadAndProcessDocument(
  file: File,
  title?: string,
  organizationId?: string,
  assessmentId?: string,
  controlId?: string,
  chunkSize: number = 512,
  chunkOverlap: number = 50,
  autoEmbed: boolean = true
): Promise<{
  upload: DocumentUploadResponse;
  process: ProcessDocumentResponse;
}> {
  // Upload first
  const uploadResult = await uploadDocument(
    file,
    title,
    organizationId,
    assessmentId,
    controlId
  );

  // Then process
  const processResult = await processDocument({
    document_id: uploadResult.document_id,
    chunk_size: chunkSize,
    chunk_overlap: chunkOverlap,
    chunking_strategy: 'hybrid',
    auto_embed: autoEmbed,
  });

  return {
    upload: uploadResult,
    process: processResult,
  };
}
