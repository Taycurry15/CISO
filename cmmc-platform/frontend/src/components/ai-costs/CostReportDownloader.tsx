/**
 * AI Cost Report Downloader Component
 * Download PDF and Excel reports for AI costs
 */

import React, { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import {
  FileDown,
  FileText,
  FileSpreadsheet,
  Calendar,
  Building,
  CheckSquare,
  Loader2,
} from 'lucide-react';
import { api } from '../../services/api';

interface ReportDownloaderProps {
  assessmentId?: string;  // If provided, shows assessment report options
  organizationMode?: boolean;  // If true, shows organization report options
}

type ReportFormat = 'pdf' | 'excel';
type ReportScope = 'assessment' | 'organization' | 'monthly';

export const CostReportDownloader: React.FC<ReportDownloaderProps> = ({
  assessmentId,
  organizationMode = false,
}) => {
  const [format, setFormat] = useState<ReportFormat>('pdf');
  const [scope, setScope] = useState<ReportScope>(
    assessmentId ? 'assessment' : 'organization'
  );
  const [startDate, setStartDate] = useState<string>(
    new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
  );
  const [endDate, setEndDate] = useState<string>(
    new Date().toISOString().split('T')[0]
  );
  const [selectedMonth, setSelectedMonth] = useState<string>(
    new Date().toISOString().substring(0, 7) // YYYY-MM format
  );

  // Download assessment report
  const downloadAssessmentReport = useMutation({
    mutationFn: async ({ format }: { format: ReportFormat }) => {
      const response = await api.get(
        `/ai/reports/assessment/${assessmentId}?format=${format}`,
        {
          responseType: 'blob',
        }
      );

      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute(
        'download',
        `assessment_cost_report_${assessmentId}_${
          new Date().toISOString().split('T')[0]
        }.${format === 'pdf' ? 'pdf' : 'xlsx'}`
      );
      document.body.appendChild(link);
      link.click();
      link.remove();
    },
  });

  // Download organization report
  const downloadOrganizationReport = useMutation({
    mutationFn: async ({
      format,
      startDate,
      endDate,
    }: {
      format: ReportFormat;
      startDate: string;
      endDate: string;
    }) => {
      const response = await api.get(
        `/ai/reports/organization?format=${format}&start_date=${startDate}&end_date=${endDate}`,
        {
          responseType: 'blob',
        }
      );

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute(
        'download',
        `organization_cost_report_${startDate}_${endDate}.${
          format === 'pdf' ? 'pdf' : 'xlsx'
        }`
      );
      document.body.appendChild(link);
      link.click();
      link.remove();
    },
  });

  // Download monthly report
  const downloadMonthlyReport = useMutation({
    mutationFn: async ({ format, month }: { format: ReportFormat; month: string }) => {
      const [year, monthNum] = month.split('-');
      const response = await api.get(
        `/ai/reports/monthly?year=${year}&month=${monthNum}&format=${format}`,
        {
          responseType: 'blob',
        }
      );

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute(
        'download',
        `monthly_cost_report_${year}${monthNum}.${format === 'pdf' ? 'pdf' : 'xlsx'}`
      );
      document.body.appendChild(link);
      link.click();
      link.remove();
    },
  });

  const handleDownload = () => {
    if (scope === 'assessment' && assessmentId) {
      downloadAssessmentReport.mutate({ format });
    } else if (scope === 'monthly') {
      downloadMonthlyReport.mutate({ format, month: selectedMonth });
    } else {
      downloadOrganizationReport.mutate({ format, startDate, endDate });
    }
  };

  const isLoading =
    downloadAssessmentReport.isPending ||
    downloadOrganizationReport.isPending ||
    downloadMonthlyReport.isPending;

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center gap-2 mb-6">
        <FileDown className="w-6 h-6 text-blue-600" />
        <h3 className="text-lg font-semibold text-gray-900">Download Cost Report</h3>
      </div>

      <div className="space-y-6">
        {/* Report Scope Selection (if not assessment-specific) */}
        {!assessmentId && organizationMode && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-3">
              Report Scope
            </label>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <button
                onClick={() => setScope('organization')}
                className={`p-4 border-2 rounded-lg flex items-center gap-3 transition-all ${
                  scope === 'organization'
                    ? 'border-blue-500 bg-blue-50'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <Building
                  className={`w-5 h-5 ${
                    scope === 'organization' ? 'text-blue-600' : 'text-gray-400'
                  }`}
                />
                <div className="text-left">
                  <div className="font-medium text-sm">Organization</div>
                  <div className="text-xs text-gray-500">Custom date range</div>
                </div>
              </button>

              <button
                onClick={() => setScope('monthly')}
                className={`p-4 border-2 rounded-lg flex items-center gap-3 transition-all ${
                  scope === 'monthly'
                    ? 'border-blue-500 bg-blue-50'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <Calendar
                  className={`w-5 h-5 ${
                    scope === 'monthly' ? 'text-blue-600' : 'text-gray-400'
                  }`}
                />
                <div className="text-left">
                  <div className="font-medium text-sm">Monthly</div>
                  <div className="text-xs text-gray-500">By month</div>
                </div>
              </button>
            </div>
          </div>
        )}

        {/* Date Range Selection (for organization scope) */}
        {scope === 'organization' && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-3">
              Date Range
            </label>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs text-gray-600 mb-1">Start Date</label>
                <input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  max={endDate}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-600 mb-1">End Date</label>
                <input
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  min={startDate}
                  max={new Date().toISOString().split('T')[0]}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
          </div>
        )}

        {/* Month Selection (for monthly scope) */}
        {scope === 'monthly' && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-3">
              Select Month
            </label>
            <input
              type="month"
              value={selectedMonth}
              onChange={(e) => setSelectedMonth(e.target.value)}
              max={new Date().toISOString().substring(0, 7)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>
        )}

        {/* Format Selection */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-3">
            Report Format
          </label>
          <div className="grid grid-cols-2 gap-3">
            <button
              onClick={() => setFormat('pdf')}
              className={`p-4 border-2 rounded-lg flex items-center gap-3 transition-all ${
                format === 'pdf'
                  ? 'border-red-500 bg-red-50'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
            >
              <FileText
                className={`w-5 h-5 ${format === 'pdf' ? 'text-red-600' : 'text-gray-400'}`}
              />
              <div className="text-left">
                <div className="font-medium text-sm">PDF</div>
                <div className="text-xs text-gray-500">Formatted report</div>
              </div>
            </button>

            <button
              onClick={() => setFormat('excel')}
              className={`p-4 border-2 rounded-lg flex items-center gap-3 transition-all ${
                format === 'excel'
                  ? 'border-green-500 bg-green-50'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
            >
              <FileSpreadsheet
                className={`w-5 h-5 ${
                  format === 'excel' ? 'text-green-600' : 'text-gray-400'
                }`}
              />
              <div className="text-left">
                <div className="font-medium text-sm">Excel</div>
                <div className="text-xs text-gray-500">Spreadsheet data</div>
              </div>
            </button>
          </div>
        </div>

        {/* Report Contents Preview */}
        <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
          <h4 className="text-sm font-medium text-gray-900 mb-3">
            Report will include:
          </h4>
          <ul className="space-y-2 text-sm text-gray-700">
            <li className="flex items-start gap-2">
              <CheckSquare className="w-4 h-4 text-green-600 mt-0.5 flex-shrink-0" />
              <span>Cost summary and total spending</span>
            </li>
            <li className="flex items-start gap-2">
              <CheckSquare className="w-4 h-4 text-green-600 mt-0.5 flex-shrink-0" />
              <span>Breakdown by operation type (embeddings, analysis, RAG)</span>
            </li>
            <li className="flex items-start gap-2">
              <CheckSquare className="w-4 h-4 text-green-600 mt-0.5 flex-shrink-0" />
              <span>Token usage and model statistics</span>
            </li>
            <li className="flex items-start gap-2">
              <CheckSquare className="w-4 h-4 text-green-600 mt-0.5 flex-shrink-0" />
              <span>Daily spending trends</span>
            </li>
            {!assessmentId && (
              <li className="flex items-start gap-2">
                <CheckSquare className="w-4 h-4 text-green-600 mt-0.5 flex-shrink-0" />
                <span>Top assessments by cost</span>
              </li>
            )}
            {assessmentId && (
              <li className="flex items-start gap-2">
                <CheckSquare className="w-4 h-4 text-green-600 mt-0.5 flex-shrink-0" />
                <span>Top controls by cost</span>
              </li>
            )}
          </ul>
        </div>

        {/* Download Button */}
        <button
          onClick={handleDownload}
          disabled={isLoading}
          className={`w-full py-3 px-4 rounded-lg font-medium text-white flex items-center justify-center gap-2 transition-colors ${
            isLoading
              ? 'bg-gray-400 cursor-not-allowed'
              : 'bg-blue-600 hover:bg-blue-700'
          }`}
        >
          {isLoading ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              Generating Report...
            </>
          ) : (
            <>
              <FileDown className="w-5 h-5" />
              Download {format.toUpperCase()} Report
            </>
          )}
        </button>

        {/* Error Display */}
        {(downloadAssessmentReport.isError ||
          downloadOrganizationReport.isError ||
          downloadMonthlyReport.isError) && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">
            Failed to generate report. Please try again or contact support if the problem
            persists.
          </div>
        )}

        {/* Success Message */}
        {(downloadAssessmentReport.isSuccess ||
          downloadOrganizationReport.isSuccess ||
          downloadMonthlyReport.isSuccess) && (
          <div className="bg-green-50 border border-green-200 rounded-lg p-3 text-sm text-green-700">
            Report downloaded successfully!
          </div>
        )}
      </div>
    </div>
  );
};

export default CostReportDownloader;
