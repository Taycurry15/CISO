import React, { useState } from 'react';
import { MainLayout } from '@/components/layout';
import { Button } from '@/components/common/Button';
import { Card } from '@/components/common/Card';
import { Select } from '@/components/common/Select';
import { bulkService } from '@/services/bulk';
import { useAssessments } from '@/hooks/useAssessments';
import { Upload, Download, Package, TrendingUp } from 'lucide-react';

export const BulkOperations: React.FC = () => {
  const { assessments } = useAssessments();
  const [selectedAssessment, setSelectedAssessment] = useState('');
  const [isProcessing, setIsProcessing] = useState<string | null>(null);
  const [result, setResult] = useState<any>(null);

  const handleExcelImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !selectedAssessment) {
      alert('Please select an assessment and file');
      return;
    }

    setIsProcessing('excel-import');
    try {
      const response = await bulkService.importFindingsFromExcel(selectedAssessment, file);
      setResult(response);
      alert(`Import complete: ${response.successCount} succeeded, ${response.failureCount} failed`);
    } catch (error) {
      console.error('Failed to import Excel:', error);
      alert('Failed to import Excel file');
    } finally {
      setIsProcessing(null);
      e.target.value = '';
    }
  };

  const handleExcelExport = async () => {
    if (!selectedAssessment) {
      alert('Please select an assessment');
      return;
    }

    setIsProcessing('excel-export');
    try {
      const blob = await bulkService.exportFindingsToExcel(selectedAssessment);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `findings-${selectedAssessment}-${new Date().toISOString()}.xlsx`;
      link.click();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Failed to export Excel:', error);
      alert('Failed to export Excel file');
    } finally {
      setIsProcessing(null);
    }
  };

  const handleZipUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !selectedAssessment) {
      alert('Please select an assessment and file');
      return;
    }

    setIsProcessing('zip-upload');
    try {
      const response = await bulkService.bulkUploadEvidenceZip(
        selectedAssessment,
        file,
        'Other'
      );
      setResult(response);
      alert(`Upload complete: ${response.successCount} files uploaded, ${response.failureCount} failed`);
    } catch (error) {
      console.error('Failed to upload ZIP:', error);
      alert('Failed to upload ZIP file');
    } finally {
      setIsProcessing(null);
      e.target.value = '';
    }
  };

  const operations = [
    {
      id: 'excel-export',
      title: 'Export Findings to Excel',
      description: 'Download all control findings as a formatted Excel spreadsheet for bulk editing.',
      icon: Download,
      color: 'success',
      action: handleExcelExport,
      buttonText: 'Export to Excel',
      timeSaving: '2-3 hours saved vs. manual export',
    },
    {
      id: 'excel-import',
      title: 'Import Findings from Excel',
      description: 'Upload a bulk-edited Excel file to update 50-100 control findings at once.',
      icon: Upload,
      color: 'primary',
      isFileUpload: true,
      accept: '.xlsx,.xls',
      onChange: handleExcelImport,
      buttonText: 'Choose Excel File',
      timeSaving: '5-10 hours saved vs. manual entry',
    },
    {
      id: 'zip-upload',
      title: 'Bulk Evidence Upload (ZIP)',
      description: 'Upload multiple evidence files at once by providing a ZIP archive.',
      icon: Package,
      color: 'blue',
      isFileUpload: true,
      accept: '.zip',
      onChange: handleZipUpload,
      buttonText: 'Choose ZIP File',
      timeSaving: '3-5 hours saved vs. individual uploads',
    },
  ];

  return (
    <MainLayout>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Bulk Operations</h1>
          <p className="text-gray-600 mt-2">
            Perform batch operations to save 5-10 hours per assessment
          </p>
        </div>

        {/* Time Savings Banner */}
        <div className="bg-gradient-to-r from-primary-500 to-primary-600 rounded-lg p-6 text-white">
          <div className="flex items-center space-x-4">
            <div className="w-12 h-12 bg-white/20 rounded-lg flex items-center justify-center">
              <TrendingUp className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-xl font-bold">Save 5-10 Hours Per Assessment</h3>
              <p className="text-primary-100 mt-1">
                Bulk operations dramatically reduce manual data entry and file management
              </p>
            </div>
          </div>
        </div>

        {/* Assessment Selector */}
        <Card title="Select Assessment">
          <Select
            label="Assessment"
            value={selectedAssessment}
            onChange={setSelectedAssessment}
            options={[
              { value: '', label: 'Choose an assessment...' },
              ...(assessments?.map((a) => ({
                value: a.id,
                label: `${a.name} (${a.status})`,
              })) || []),
            ]}
            placeholder="Select an assessment"
          />
        </Card>

        {/* Operations Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {operations.map((operation) => {
            const Icon = operation.icon;
            return (
              <Card key={operation.id}>
                <div className="flex flex-col h-full">
                  <div className={`w-12 h-12 bg-${operation.color}-100 rounded-lg flex items-center justify-center mb-4`}>
                    <Icon className={`w-6 h-6 text-${operation.color}-600`} />
                  </div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">
                    {operation.title}
                  </h3>
                  <p className="text-sm text-gray-600 mb-4 flex-1">
                    {operation.description}
                  </p>
                  <div className="bg-success-50 text-success-700 text-xs px-3 py-2 rounded-lg mb-4 flex items-center">
                    <TrendingUp className="w-3 h-3 mr-2" />
                    {operation.timeSaving}
                  </div>
                  {operation.isFileUpload ? (
                    <label className="cursor-pointer">
                      <input
                        type="file"
                        accept={operation.accept}
                        onChange={operation.onChange}
                        className="hidden"
                        disabled={!selectedAssessment || isProcessing !== null}
                      />
                      <div
                        className={`btn btn-primary w-full text-center ${
                          !selectedAssessment || isProcessing !== null
                            ? 'opacity-50 cursor-not-allowed'
                            : ''
                        }`}
                      >
                        {isProcessing === operation.id ? (
                          <>
                            <div className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-solid border-white border-r-transparent mr-2"></div>
                            Processing...
                          </>
                        ) : (
                          <>
                            <Upload className="w-4 h-4 mr-2 inline" />
                            {operation.buttonText}
                          </>
                        )}
                      </div>
                    </label>
                  ) : (
                    <Button
                      variant="primary"
                      size="md"
                      onClick={operation.action}
                      loading={isProcessing === operation.id}
                      disabled={!selectedAssessment || isProcessing !== null}
                      className="w-full"
                    >
                      {operation.buttonText}
                    </Button>
                  )}
                </div>
              </Card>
            );
          })}
        </div>

        {/* Result Display */}
        {result && (
          <Card title="Operation Results">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-gray-700">Total Processed:</span>
                <span className="font-semibold text-gray-900">{result.totalProcessed}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-success-700">Successful:</span>
                <span className="font-semibold text-success-700">{result.successCount}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-danger-700">Failed:</span>
                <span className="font-semibold text-danger-700">{result.failureCount}</span>
              </div>
              {result.errors && result.errors.length > 0 && (
                <div className="mt-4 pt-4 border-t border-gray-200">
                  <h4 className="text-sm font-semibold text-gray-900 mb-2">Errors:</h4>
                  <div className="space-y-2 max-h-40 overflow-y-auto">
                    {result.errors.map((error: any, idx: number) => (
                      <div key={idx} className="text-sm text-danger-600 bg-danger-50 p-2 rounded">
                        {error.controlId || error.fileName}: {error.error}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </Card>
        )}

        {/* Guidelines */}
        <Card title="Bulk Operations Guidelines">
          <div className="space-y-3 text-sm text-gray-700">
            <div>
              <strong>Excel Import/Export:</strong>
              <ul className="list-disc list-inside ml-4 mt-1 space-y-1">
                <li>Use Export first to get the template with all controls</li>
                <li>Edit statuses, narratives, and assessor notes in Excel</li>
                <li>Import to update 50-100 controls at once (vs. 1-2 per minute manually)</li>
                <li>Invalid data will be skipped with error details provided</li>
              </ul>
            </div>
            <div>
              <strong>ZIP Upload:</strong>
              <ul className="list-disc list-inside ml-4 mt-1 space-y-1">
                <li>Create a ZIP file containing multiple evidence files</li>
                <li>All files will be extracted and uploaded automatically</li>
                <li>Empty files and unsupported formats will be skipped</li>
                <li>Link evidence to controls after upload if needed</li>
              </ul>
            </div>
          </div>
        </Card>
      </div>
    </MainLayout>
  );
};
