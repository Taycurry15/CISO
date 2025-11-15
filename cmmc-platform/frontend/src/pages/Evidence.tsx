import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import { MainLayout } from '@/components/layout';
import { Button } from '@/components/common/Button';
import { Input } from '@/components/common/Input';
import { Select } from '@/components/common/Select';
import { Modal } from '@/components/common/Modal';
import { Badge } from '@/components/common/Badge';
import { Table } from '@/components/common/Table';
import { useEvidence } from '@/hooks/useEvidence';
import { Upload, Download, FileText, Trash2 } from 'lucide-react';
import { Evidence as EvidenceType } from '@/types';

export const Evidence: React.FC = () => {
  const { assessmentId } = useParams<{ assessmentId: string }>();
  const {
    evidence,
    isLoading,
    uploadEvidence,
    deleteEvidence,
    downloadEvidence,
    isUploading,
  } = useEvidence(assessmentId || '');

  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [evidenceType, setEvidenceType] = useState('Policy');
  const [description, setDescription] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState('');

  const handleFileUpload = async () => {
    if (!selectedFile || !assessmentId) return;

    try {
      await uploadEvidence({
        file: selectedFile,
        metadata: {
          evidenceType,
          description,
        },
      });
      setIsUploadModalOpen(false);
      setSelectedFile(null);
      setDescription('');
    } catch (error) {
      console.error('Failed to upload evidence:', error);
    }
  };

  const handleDownload = async (item: EvidenceType) => {
    try {
      await downloadEvidence(item.id, item.fileName);
    } catch (error) {
      console.error('Failed to download evidence:', error);
    }
  };

  const handleDelete = async (id: string) => {
    if (confirm('Are you sure you want to delete this evidence?')) {
      try {
        await deleteEvidence(id);
      } catch (error) {
        console.error('Failed to delete evidence:', error);
      }
    }
  };

  const filteredEvidence = evidence?.filter((item) => {
    const matchesSearch =
      searchQuery === '' ||
      item.fileName.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.description?.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesType = typeFilter === '' || item.evidenceType === typeFilter;

    return matchesSearch && matchesType;
  });

  const columns = [
    {
      key: 'fileName',
      header: 'File Name',
      render: (item: EvidenceType) => (
        <div className="flex items-center space-x-2">
          <FileText className="w-4 h-4 text-gray-400" />
          <span className="font-medium text-gray-900">{item.fileName}</span>
        </div>
      ),
    },
    {
      key: 'evidenceType',
      header: 'Type',
      render: (item: EvidenceType) => <Badge variant="blue">{item.evidenceType}</Badge>,
    },
    {
      key: 'fileSize',
      header: 'Size',
      render: (item: EvidenceType) => (
        <span className="text-gray-600">{(item.fileSize / 1024).toFixed(2)} KB</span>
      ),
    },
    {
      key: 'controls',
      header: 'Linked Controls',
      render: (item: EvidenceType) => (
        <span className="text-gray-600">{item.controlIds.length} controls</span>
      ),
    },
    {
      key: 'createdAt',
      header: 'Uploaded',
      render: (item: EvidenceType) => (
        <span className="text-gray-600">{new Date(item.createdAt).toLocaleDateString()}</span>
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (item: EvidenceType) => (
        <div className="flex items-center space-x-2">
          <Button variant="ghost" size="sm" onClick={() => handleDownload(item)}>
            <Download className="w-4 h-4" />
          </Button>
          <Button variant="ghost" size="sm" onClick={() => handleDelete(item.id)}>
            <Trash2 className="w-4 h-4 text-danger-600" />
          </Button>
        </div>
      ),
    },
  ];

  return (
    <MainLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Evidence Management</h1>
            <p className="text-gray-600 mt-2">Upload and manage assessment evidence</p>
          </div>
          <Button variant="primary" onClick={() => setIsUploadModalOpen(true)}>
            <Upload className="w-5 h-5 mr-2" />
            Upload Evidence
          </Button>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="card p-4">
            <p className="text-sm text-gray-600">Total Files</p>
            <p className="text-2xl font-bold text-gray-900">{evidence?.length || 0}</p>
          </div>
          <div className="card p-4">
            <p className="text-sm text-gray-600">Total Size</p>
            <p className="text-2xl font-bold text-gray-900">
              {((evidence?.reduce((sum, e) => sum + e.fileSize, 0) || 0) / 1024 / 1024).toFixed(2)} MB
            </p>
          </div>
          <div className="card p-4">
            <p className="text-sm text-gray-600">Linked</p>
            <p className="text-2xl font-bold text-gray-900">
              {evidence?.filter((e) => e.controlIds.length > 0).length || 0}
            </p>
          </div>
          <div className="card p-4">
            <p className="text-sm text-gray-600">Unlinked</p>
            <p className="text-2xl font-bold text-warning-600">
              {evidence?.filter((e) => e.controlIds.length === 0).length || 0}
            </p>
          </div>
        </div>

        {/* Filters */}
        <div className="card p-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              placeholder="Search evidence..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            <Select
              value={typeFilter}
              onChange={setTypeFilter}
              options={[
                { value: '', label: 'All Types' },
                { value: 'Policy', label: 'Policy' },
                { value: 'Procedure', label: 'Procedure' },
                { value: 'Screenshot', label: 'Screenshot' },
                { value: 'Configuration', label: 'Configuration' },
                { value: 'Log', label: 'Log' },
                { value: 'Report', label: 'Report' },
                { value: 'Other', label: 'Other' },
              ]}
            />
          </div>
        </div>

        {/* Evidence Table */}
        <div className="card">
          <Table
            columns={columns}
            data={filteredEvidence || []}
            loading={isLoading}
            emptyMessage="No evidence files uploaded yet"
          />
        </div>

        {/* Upload Modal */}
        <Modal
          isOpen={isUploadModalOpen}
          onClose={() => setIsUploadModalOpen(false)}
          title="Upload Evidence"
          size="md"
        >
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">File</label>
              <input
                type="file"
                onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                className="input"
              />
              {selectedFile && (
                <p className="text-sm text-gray-600 mt-2">
                  Selected: {selectedFile.name} ({(selectedFile.size / 1024).toFixed(2)} KB)
                </p>
              )}
            </div>

            <Select
              label="Evidence Type"
              value={evidenceType}
              onChange={setEvidenceType}
              options={[
                { value: 'Policy', label: 'Policy' },
                { value: 'Procedure', label: 'Procedure' },
                { value: 'Screenshot', label: 'Screenshot' },
                { value: 'Configuration', label: 'Configuration' },
                { value: 'Log', label: 'Log' },
                { value: 'Report', label: 'Report' },
                { value: 'Other', label: 'Other' },
              ]}
            />

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Description (Optional)
              </label>
              <textarea
                className="input"
                rows={3}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Describe the evidence file..."
              />
            </div>

            <div className="flex justify-end space-x-3 pt-4">
              <Button
                variant="secondary"
                onClick={() => setIsUploadModalOpen(false)}
                disabled={isUploading}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                onClick={handleFileUpload}
                loading={isUploading}
                disabled={!selectedFile || isUploading}
              >
                Upload
              </Button>
            </div>
          </div>
        </Modal>
      </div>
    </MainLayout>
  );
};
