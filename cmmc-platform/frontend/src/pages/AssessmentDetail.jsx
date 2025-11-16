import { useParams } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export default function AssessmentDetail() {
  const { id } = useParams();
  const navigate = useNavigate();

  return (
    <div className="space-y-6">
      <div className="flex items-center space-x-4">
        <button
          onClick={() => navigate('/assessments')}
          className="p-2 hover:bg-gray-100 rounded-lg"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Assessment Detail</h1>
          <p className="text-sm text-gray-500">ID: {id}</p>
        </div>
      </div>

      <div className="card">
        <p className="text-gray-600">Assessment details coming soon...</p>
      </div>
    </div>
  );
}
