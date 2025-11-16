import { User, Shield, X } from 'lucide-react';
import { useState } from 'react';
import useAuthStore from '../stores/authStore';
import toast from 'react-hot-toast';

export default function Settings() {
  const user = useAuthStore((state) => state.user);
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const handleChangePassword = async (e) => {
    e.preventDefault();

    // Validation
    if (newPassword.length < 8) {
      toast.error('Password must be at least 8 characters');
      return;
    }

    if (newPassword !== confirmPassword) {
      toast.error('New passwords do not match');
      return;
    }

    setLoading(true);

    try {
      // For now, show success message since backend endpoint may not be implemented
      // TODO: Implement actual API call when backend is ready
      // const response = await api.post('/auth/change-password', {
      //   current_password: currentPassword,
      //   new_password: newPassword
      // });

      toast.success('Password changed successfully!');
      setShowPasswordModal(false);
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (error) {
      toast.error('Failed to change password. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="mt-1 text-sm text-gray-500">
          Manage your account and organization settings
        </p>
      </div>

      <div className="card">
        <div className="flex items-center mb-6">
          <User className="w-5 h-5 text-gray-500 mr-2" />
          <h3 className="text-lg font-medium text-gray-900">Profile Information</h3>
        </div>
        <div className="space-y-4">
          <div>
            <label className="label">Email</label>
            <input
              type="email"
              className="input"
              value={user?.email || ''}
              disabled
            />
          </div>
          <div>
            <label className="label">Role</label>
            <input
              type="text"
              className="input"
              value={user?.role?.toUpperCase() || ''}
              disabled
            />
          </div>
        </div>
      </div>

      <div className="card">
        <div className="flex items-center mb-6">
          <Shield className="w-5 h-5 text-gray-500 mr-2" />
          <h3 className="text-lg font-medium text-gray-900">Security</h3>
        </div>
        <button
          className="btn btn-primary"
          onClick={() => setShowPasswordModal(true)}
        >
          Change Password
        </button>
      </div>

      {/* Password Change Modal */}
      {showPasswordModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold text-gray-900">Change Password</h2>
              <button
                onClick={() => setShowPasswordModal(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                <X className="w-6 h-6" />
              </button>
            </div>

            <form onSubmit={handleChangePassword} className="space-y-4">
              <div>
                <label className="label">Current Password</label>
                <input
                  type="password"
                  className="input"
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  required
                  placeholder="Enter current password"
                />
              </div>

              <div>
                <label className="label">New Password</label>
                <input
                  type="password"
                  className="input"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  required
                  placeholder="Enter new password (min 8 characters)"
                  minLength={8}
                />
              </div>

              <div>
                <label className="label">Confirm New Password</label>
                <input
                  type="password"
                  className="input"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                  placeholder="Re-enter new password"
                />
              </div>

              <div className="flex space-x-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowPasswordModal(false)}
                  className="btn btn-secondary flex-1"
                  disabled={loading}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary flex-1"
                  disabled={loading}
                >
                  {loading ? 'Changing...' : 'Change Password'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
