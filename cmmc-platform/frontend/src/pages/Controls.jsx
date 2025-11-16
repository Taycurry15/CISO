import { Shield, CheckCircle, XCircle, AlertTriangle } from 'lucide-react';

export default function Controls() {
  const controls = [
    { id: 'AC.L2-3.1.1', family: 'AC', title: 'Limit system access', status: 'Met', confidence: 95 },
    { id: 'AC.L2-3.1.2', family: 'AC', title: 'Limit transaction permissions', status: 'Met', confidence: 88 },
    { id: 'AU.L2-3.3.1', family: 'AU', title: 'Create audit records', status: 'Met', confidence: 92 },
    { id: 'AU.L2-3.3.2', family: 'AU', title: 'Review and update audited events', status: 'Partially Met', confidence: 75 },
    { id: 'IA.L2-3.5.1', family: 'IA', title: 'Identify system users', status: 'Met', confidence: 90 },
    { id: 'IA.L2-3.5.2', family: 'IA', title: 'Authenticate users', status: 'Not Met', confidence: 45 },
  ];

  const getStatusIcon = (status) => {
    switch (status) {
      case 'Met':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'Partially Met':
        return <AlertTriangle className="w-5 h-5 text-yellow-500" />;
      case 'Not Met':
        return <XCircle className="w-5 h-5 text-red-500" />;
      default:
        return <Shield className="w-5 h-5 text-gray-500" />;
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Control Compliance</h1>
        <p className="mt-1 text-sm text-gray-500">
          NIST 800-171 control compliance status
        </p>
      </div>

      <div className="card">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead>
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Control ID
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Title
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  AI Confidence
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {controls.map((control) => (
                <tr key={control.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    {control.id}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-600">
                    {control.title}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      {getStatusIcon(control.status)}
                      <span className="ml-2 text-sm">{control.status}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <div className="w-24 bg-gray-200 rounded-full h-2 mr-2">
                        <div
                          className="bg-primary-600 h-2 rounded-full"
                          style={{ width: `${control.confidence}%` }}
                        />
                      </div>
                      <span className="text-sm text-gray-600">{control.confidence}%</span>
                    </div>
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
