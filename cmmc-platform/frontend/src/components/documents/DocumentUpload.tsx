/**
 * Document Upload Component
 * Handles file uploads for RAG processing
 */

import React, { useState, useRef } from 'react';
import { Button, Input, Card } from '../common';
import { uploadAndProcessDocument } from '../../services/document-management';
import type { DocumentUploadResponse, ProcessDocumentResponse } from '../../types/document-management';

interface DocumentUploadProps {
  organizationId?: string;
  assessmentId?: string;
  controlId?: string;
  onUploadSuccess?: (documentId: string) => void;
  onUploadError?: (error: string) => void;
}

export const DocumentUpload: React.FC<DocumentUploadProps> = ({
  organizationId,
  assessmentId,
  controlId,
  onUploadSuccess,
  onUploadError,
}) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [title, setTitle] = useState('');
  const [uploading, setUploading] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const allowedExtensions = ['.pdf', '.docx', '.doc', '.txt', '.md'];
  const maxFileSize = 50 * 1024 * 1024; // 50MB

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Check file extension
    const fileExt = '.' + file.name.split('.').pop()?.toLowerCase();
    if (!allowedExtensions.includes(fileExt)) {
      setError(`Invalid file type. Allowed: ${allowedExtensions.join(', ')}`);
      return;
    }

    // Check file size
    if (file.size > maxFileSize) {
      setError(`File too large. Maximum size: ${maxFileSize / 1024 / 1024}MB`);
      return;
    }

    setSelectedFile(file);
    setError(null);
    setSuccess(null);

    // Auto-fill title from filename
    if (!title) {
      const fileName = file.name.replace(/\.[^/.]+$/, ''); // Remove extension
      setTitle(fileName);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setError('Please select a file');
      return;
    }

    setUploading(true);
    setProcessing(false);
    setUploadProgress(0);
    setError(null);
    setSuccess(null);

    try {
      // Upload
      setUploadProgress(30);

      // Upload and process in one call
      setProcessing(true);
      setUploadProgress(60);

      const result = await uploadAndProcessDocument(
        selectedFile,
        title || selectedFile.name,
        organizationId,
        assessmentId,
        controlId,
        512, // chunk_size
        50,  // chunk_overlap
        true // auto_embed
      );

      setUploadProgress(100);
      setSuccess(
        `Document uploaded and processed successfully! ${result.process.chunk_count} chunks created.`
      );

      // Reset form
      setSelectedFile(null);
      setTitle('');
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }

      // Notify parent
      if (onUploadSuccess) {
        onUploadSuccess(result.upload.document_id);
      }
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Upload failed';
      setError(errorMessage);
      if (onUploadError) {
        onUploadError(errorMessage);
      }
    } finally {
      setUploading(false);
      setProcessing(false);
      setUploadProgress(0);
    }
  };

  const handleClear = () => {
    setSelectedFile(null);
    setTitle('');
    setError(null);
    setSuccess(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <Card>
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">Upload CMMC Documentation</h3>
          <span className="text-sm text-gray-500">
            Supports: {allowedExtensions.join(', ')}
          </span>
        </div>

        {/* File input */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Select File
          </label>
          <input
            ref={fileInputRef}
            type="file"
            accept={allowedExtensions.join(',')}
            onChange={handleFileSelect}
            className="block w-full text-sm text-gray-500
              file:mr-4 file:py-2 file:px-4
              file:rounded-md file:border-0
              file:text-sm file:font-semibold
              file:bg-blue-50 file:text-blue-700
              hover:file:bg-blue-100
              cursor-pointer"
            disabled={uploading}
          />
          {selectedFile && (
            <p className="mt-2 text-sm text-gray-600">
              Selected: {selectedFile.name} ({(selectedFile.size / 1024).toFixed(2)} KB)
            </p>
          )}
        </div>

        {/* Title input */}
        <div>
          <Input
            label="Document Title (optional)"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Auto-filled from filename"
            disabled={uploading}
          />
        </div>

        {/* Progress bar */}
        {uploading && (
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-600">
                {processing ? 'Processing document...' : 'Uploading...'}
              </span>
              <span className="font-medium">{uploadProgress}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2.5">
              <div
                className="bg-blue-600 h-2.5 rounded-full transition-all duration-300"
                style={{ width: `${uploadProgress}%` }}
              />
            </div>
            {processing && (
              <p className="text-xs text-gray-500">
                Chunking text and generating embeddings...
              </p>
            )}
          </div>
        )}

        {/* Error message */}
        {error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-md">
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        {/* Success message */}
        {success && (
          <div className="p-3 bg-green-50 border border-green-200 rounded-md">
            <p className="text-sm text-green-700">{success}</p>
          </div>
        )}

        {/* Action buttons */}
        <div className="flex space-x-3">
          <Button
            onClick={handleUpload}
            disabled={!selectedFile || uploading}
            variant="primary"
            className="flex-1"
          >
            {uploading ? (
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
                {processing ? 'Processing...' : 'Uploading...'}
              </>
            ) : (
              'Upload & Process'
            )}
          </Button>
          <Button onClick={handleClear} disabled={uploading} variant="secondary">
            Clear
          </Button>
        </div>

        {/* Info */}
        <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-md">
          <p className="text-xs text-blue-700">
            <strong>Note:</strong> Uploaded documents will be automatically processed for semantic search.
            This includes text extraction, intelligent chunking, and vector embedding generation.
          </p>
        </div>
      </div>
    </Card>
  );
};

export default DocumentUpload;
