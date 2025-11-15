import React, { useState } from 'react';
import { MainLayout } from '@/components/layout';
import { Button } from '@/components/common/Button';
import { Card } from '@/components/common/Card';
import { Select } from '@/components/common/Select';
import { reportsService } from '@/services/reports';
import { useAssessments } from '@/hooks/useAssessments';
import { FileText, Download, FileSpreadsheet, PieChart, CheckSquare } from 'lucide-react';

export const Reports: React.FC = () => {
  const { assessments } = useAssessments();
  const [selectedAssessment, setSelectedAssessment] = useState('');
  const [isGenerating, setIsGenerating] = useState<string | null>(null);

  const handleGenerateReport = async (type: 'ssp' | 'poam' | 'executive' | 'matrix', format?: 'pdf' | 'excel') => {
    if (!selectedAssessment) {
      alert('Please select an assessment first');
      return;
    }

    setIsGenerating(type);
    try {
      let blob: Blob;
      let fileName: string;

      switch (type) {
        case 'ssp':
          blob = await reportsService.generateSSP(selectedAssessment);
          fileName = `SSP-${selectedAssessment}-${new Date().toISOString()}.docx`;
          break;
        case 'poam':
          blob = await reportsService.generatePOAM(selectedAssessment);
          fileName = `POAM-${selectedAssessment}-${new Date().toISOString()}.xlsx`;
          break;
        case 'executive':
          blob = await reportsService.generateExecutiveSummary(selectedAssessment);
          fileName = `Executive-Summary-${selectedAssessment}-${new Date().toISOString()}.pdf`;
          break;
        case 'matrix':
          blob = await reportsService.generateComplianceMatrix(selectedAssessment, format || 'pdf');
          fileName = `Compliance-Matrix-${selectedAssessment}-${new Date().toISOString()}.${format || 'pdf'}`;
          break;
        default:
          return;
      }

      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = fileName;
      link.click();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Failed to generate report:', error);
      alert('Failed to generate report. Please try again.');
    } finally {
      setIsGenerating(null);
    }
  };

  const reports = [
    {
      id: 'ssp',
      title: 'System Security Plan (SSP)',
      description: 'Comprehensive 100-400 page SSP document including all control implementations, narratives, and evidence references.',
      icon: FileText,
      format: 'Word Document',
      estimatedPages: '100-400 pages',
      color: 'primary',
    },
    {
      id: 'poam',
      title: 'Plan of Action & Milestones (POA&M)',
      description: 'Excel spreadsheet detailing all control deficiencies, remediation plans, and timelines.',
      icon: FileSpreadsheet,
      format: 'Excel Spreadsheet',
      estimatedPages: 'Multi-sheet workbook',
      color: 'success',
    },
    {
      id: 'executive',
      title: 'Executive Summary',
      description: 'High-level PDF report with compliance metrics, key findings, and recommendations for leadership.',
      icon: PieChart,
      format: 'PDF',
      estimatedPages: '5-10 pages',
      color: 'warning',
    },
    {
      id: 'matrix',
      title: 'Compliance Matrix',
      description: 'Detailed matrix showing all CMMC controls, their status, and evidence mapping.',
      icon: CheckSquare,
      format: 'PDF or Excel',
      estimatedPages: 'Multi-page matrix',
      color: 'blue',
    },
  ];

  return (
    <MainLayout>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Reports</h1>
          <p className="text-gray-600 mt-2">Generate compliance reports and documentation</p>
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

        {/* Reports Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {reports.map((report) => {
            const Icon = report.icon;
            return (
              <Card key={report.id}>
                <div className="flex items-start space-x-4">
                  <div className={`w-12 h-12 bg-${report.color}-100 rounded-lg flex items-center justify-center flex-shrink-0`}>
                    <Icon className={`w-6 h-6 text-${report.color}-600`} />
                  </div>
                  <div className="flex-1">
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">{report.title}</h3>
                    <p className="text-sm text-gray-600 mb-4">{report.description}</p>
                    <div className="flex items-center justify-between text-xs text-gray-500 mb-4">
                      <span>{report.format}</span>
                      <span>{report.estimatedPages}</span>
                    </div>
                    <div className="flex space-x-2">
                      {report.id === 'matrix' ? (
                        <>
                          <Button
                            variant="primary"
                            size="sm"
                            onClick={() => handleGenerateReport('matrix', 'pdf')}
                            loading={isGenerating === 'matrix'}
                            disabled={!selectedAssessment || isGenerating !== null}
                            className="flex-1"
                          >
                            <Download className="w-4 h-4 mr-2" />
                            PDF
                          </Button>
                          <Button
                            variant="secondary"
                            size="sm"
                            onClick={() => handleGenerateReport('matrix', 'excel')}
                            loading={isGenerating === 'matrix'}
                            disabled={!selectedAssessment || isGenerating !== null}
                            className="flex-1"
                          >
                            <Download className="w-4 h-4 mr-2" />
                            Excel
                          </Button>
                        </>
                      ) : (
                        <Button
                          variant="primary"
                          size="sm"
                          onClick={() => handleGenerateReport(report.id as any)}
                          loading={isGenerating === report.id}
                          disabled={!selectedAssessment || isGenerating !== null}
                          className="w-full"
                        >
                          <Download className="w-4 h-4 mr-2" />
                          Generate Report
                        </Button>
                      )}
                    </div>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>

        {/* Info Card */}
        <Card title="Report Generation Tips">
          <div className="space-y-3 text-sm text-gray-700">
            <p>
              <strong>SSP Generation:</strong> Typically takes 2-5 minutes depending on the number
              of controls and evidence. The document includes all control implementations, narratives,
              and references.
            </p>
            <p>
              <strong>POA&M Generation:</strong> Focuses on controls that are "Not Met" or
              "Partially Met" and includes remediation timelines and responsible parties.
            </p>
            <p>
              <strong>Best Practice:</strong> Ensure all control findings have implementation
              narratives and evidence links before generating reports for the most complete output.
            </p>
          </div>
        </Card>
      </div>
    </MainLayout>
  );
};
