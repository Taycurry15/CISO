/**
 * Document Management and RAG Types
 */

export interface UploadedDocument {
  id: string;
  title: string;
  file_path: string;
  file_type: string;
  file_size: number;
  organization_id?: string;
  assessment_id?: string;
  control_id?: string;
  uploaded_by: string;
  uploaded_at: string;
  processed: boolean;
  processing_status?: 'pending' | 'processing' | 'completed' | 'failed';
  processing_error?: string;
  chunk_count?: number;
  embedding_count?: number;
  metadata?: Record<string, any>;
}

export interface DocumentUploadRequest {
  file: File;
  title?: string;
  organization_id?: string;
  assessment_id?: string;
  control_id?: string;
  metadata?: Record<string, any>;
}

export interface DocumentUploadResponse {
  success: boolean;
  document_id: string;
  document: UploadedDocument;
  message: string;
}

export interface ProcessDocumentRequest {
  document_id: string;
  chunk_size?: number;
  chunk_overlap?: number;
  chunking_strategy?: 'fixed' | 'semantic' | 'hybrid';
  auto_embed?: boolean;
}

export interface ProcessDocumentResponse {
  success: boolean;
  message: string;
  chunk_count: number;
  processing_time_seconds?: number;
}

export interface DocumentChunk {
  id: string;
  document_id: string;
  chunk_text: string;
  chunk_index: number;
  start_pos: number;
  end_pos: number;
  has_embedding: boolean;
  metadata?: Record<string, any>;
}

export interface RAGQueryRequest {
  query: string;
  top_k?: number;
  control_id?: string;
  assessment_id?: string;
  organization_id?: string;
  document_ids?: string[];
  min_similarity?: number;
  include_metadata?: boolean;
}

export interface RetrievedChunk {
  chunk_id: string;
  document_id: string;
  document_title: string;
  chunk_text: string;
  chunk_index: number;
  similarity_score: number;
  metadata?: Record<string, any>;
}

export interface RAGContext {
  chunks: RetrievedChunk[];
  total_chunks_searched: number;
  query_time_seconds: number;
  sources: string[];
}

export interface RAGQueryResponse {
  success: boolean;
  query: string;
  context: RAGContext;
  message: string;
}

export interface DocumentListRequest {
  organization_id?: string;
  assessment_id?: string;
  control_id?: string;
  processed_only?: boolean;
  file_type?: string;
  limit?: number;
  offset?: number;
}

export interface DocumentListResponse {
  success: boolean;
  documents: UploadedDocument[];
  total_count: number;
  page: number;
  page_size: number;
}

export interface RAGStats {
  total_documents: number;
  total_chunks: number;
  total_embeddings: number;
  documents_by_type: Record<string, number>;
  avg_chunks_per_document: number;
  total_storage_mb: number;
}

export interface RAGStatsResponse {
  success: boolean;
  stats: RAGStats;
}
