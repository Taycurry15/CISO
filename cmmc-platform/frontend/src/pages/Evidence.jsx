import { Upload, File, CheckCircle, Clock, XCircle } from 'lucide-react';
import { useState } from 'react';
import toast from 'react-hot-toast';

export default function Evidence() {
  const [selectedFile, setSelectedFile] = useState(null);

  const handleFileSelect = (e) => {
    setSelectedFile(e.target.files[0]);
  };

  const handleUpload = () => {
    if (!selectedFile) {
      toast.error('Please select a file to upload');
      return;
    }
    toast.success('Evidence uploaded successfully!');
    setSelectedFile(null);
  };

  const mockEvidence = [
    {
      id: 1,
      title: 'User Access Control Policy',
      control: 'AC.L2-3.1.1',
      type: 'document',
      status: 'approved',
      uploadedAt: '2024-01-15',
    },
    {
      id: 2,
      title: 'Firewall Configuration Screenshot',
      control: 'SC.L2-3.13.1',
      type: 'screenshot',
      status: 'pending_review',
      uploadedAt: '2024-01-14',
    },
    {
      id: 3,
      title: 'Audit Log Export',
      control: 'AU.L2-3.3.1',
      type: 'log',
      status: 'approved',
      uploadedAt: '2024-01-13',
    },
  ];

  const getStatusIcon = (status) => {
    switch (status) {
      case 'approved':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'pending_review':
        return <Clock className="w-5 h-5 text-yellow-500" />;
      case 'rejected':
        return <XCircle className="w-5 h-5 text-red-500" />;
      default:
        return <File className="w-5 h-5 text-gray-500" />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Evidence Collection</h1>
        <p className="mt-1 text-sm text-gray-500">
          Upload and manage evidence for your CMMC controls
        </p>
      </div>

      {/* Upload Section */}
      <div className="card">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Upload Evidence</h3>
        <div className="border-2 border-dashed border-gray-300 rounded-lg p-8">
          <div className="text-center">
            <Upload className="w-12 h-12 mx-auto text-gray-400 mb-4" />
            <div className="mb-4">
              <label htmlFor="file-upload" className="cursor-pointer">
                <span className="text-primary-600 hover:text-primary-700 font-medium">
                  Choose a file
                </span>
                <input
                  id="file-upload"
                  type="file"
                  className="hidden"
                  onChange={handleFileSelect}
                />
              </label>
              <span className="text-gray-600"> or drag and drop</span>
            </div>
            {selectedFile && (
              <div className="mb-4">
                <p className="text-sm text-gray-700">
                  Selected: <span className="font-medium">{selectedFile.name}</span>
                </p>
              </div>
            )}
            <p className="text-xs text-gray-500">
              PDF, DOC, DOCX, PNG, JPG up to 10MB
            </p>
          </div>
        </div>

        {selectedFile && (
          <div className="mt-4 flex justify-end space-x-3">
            <button
              className="btn btn-secondary"
              onClick={() => setSelectedFile(null)}
            >
              Cancel
            </button>
            <button className="btn btn-primary" onClick={handleUpload}>
              Upload Evidence
            </button>
          </div>
        )}
      </div>

      {/* Evidence List */}
      <div className="card">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Evidence Repository</h3>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead>
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Title
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Control
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Type
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Uploaded
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {mockEvidence.map((evidence) => (
                <tr key={evidence.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <File className="w-5 h-5 text-gray-400 mr-3" />
                      <span className="text-sm font-medium text-gray-900">
                        {evidence.title}
                      </span>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                    {evidence.control}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600 capitalize">
                    {evidence.type}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      {getStatusIcon(evidence.status)}
                      <span className="ml-2 text-sm text-gray-600 capitalize">
                        {evidence.status.replace('_', ' ')}
                      </span>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                    {new Date(evidence.uploadedAt).toLocaleDateString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
