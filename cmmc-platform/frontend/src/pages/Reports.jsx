import { FileText, Download } from 'lucide-react';

export default function Reports() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Reports</h1>
        <p className="mt-1 text-sm text-gray-500">
          Generate and download compliance reports
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="card">
          <FileText className="w-12 h-12 text-primary-600 mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            System Security Plan (SSP)
          </h3>
          <p className="text-gray-600 mb-4">
            Complete SSP documentation with all control implementations
          </p>
          <button className="btn btn-primary w-full">
            <Download className="w-4 h-4 mr-2" />
            Generate SSP
          </button>
        </div>

        <div className="card">
          <FileText className="w-12 h-12 text-primary-600 mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            POA&M Report
          </h3>
          <p className="text-gray-600 mb-4">
            Plan of Action & Milestones for non-compliant controls
          </p>
          <button className="btn btn-primary w-full">
            <Download className="w-4 h-4 mr-2" />
            Generate POA&M
          </button>
        </div>
      </div>
    </div>
  );
}
