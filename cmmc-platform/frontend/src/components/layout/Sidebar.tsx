import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  ClipboardCheck,
  Shield,
  FileText,
  FolderOpen,
  Settings,
  BarChart3,
  Upload,
  BookOpen,
} from 'lucide-react';

interface NavItem {
  name: string;
  path: string;
  icon: React.ReactNode;
  badge?: string;
}

const navItems: NavItem[] = [
  {
    name: 'Dashboard',
    path: '/dashboard',
    icon: <LayoutDashboard className="w-5 h-5" />,
  },
  {
    name: 'Assessments',
    path: '/assessments',
    icon: <ClipboardCheck className="w-5 h-5" />,
  },
  {
    name: 'Controls',
    path: '/controls',
    icon: <Shield className="w-5 h-5" />,
  },
  {
    name: 'Evidence',
    path: '/evidence',
    icon: <FolderOpen className="w-5 h-5" />,
  },
  {
    name: 'Reports',
    path: '/reports',
    icon: <FileText className="w-5 h-5" />,
  },
  {
    name: 'Documents',
    path: '/documents',
    icon: <BookOpen className="w-5 h-5" />,
  },
  {
    name: 'Bulk Operations',
    path: '/bulk',
    icon: <Upload className="w-5 h-5" />,
  },
  {
    name: 'Analytics',
    path: '/analytics',
    icon: <BarChart3 className="w-5 h-5" />,
  },
  {
    name: 'Settings',
    path: '/settings',
    icon: <Settings className="w-5 h-5" />,
  },
];

export const Sidebar: React.FC = () => {
  return (
    <aside className="w-64 bg-white border-r border-gray-200 fixed left-0 top-16 bottom-0 overflow-y-auto">
      <nav className="p-4 space-y-1">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              `flex items-center px-4 py-3 text-sm font-medium rounded-lg transition-colors ${
                isActive
                  ? 'bg-primary-50 text-primary-700'
                  : 'text-gray-700 hover:bg-gray-100 hover:text-gray-900'
              }`
            }
          >
            <span className="mr-3">{item.icon}</span>
            {item.name}
            {item.badge && (
              <span className="ml-auto bg-primary-600 text-white text-xs px-2 py-0.5 rounded-full">
                {item.badge}
              </span>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Quick Stats */}
      <div className="p-4 mx-4 mt-6 bg-gray-50 rounded-lg">
        <h3 className="text-xs font-semibold text-gray-500 uppercase mb-3">Quick Stats</h3>
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-600">Compliance</span>
            <span className="font-semibold text-success-700">85%</span>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-600">Controls</span>
            <span className="font-semibold text-gray-900">94/110</span>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-600">Evidence</span>
            <span className="font-semibold text-gray-900">156</span>
          </div>
        </div>
      </div>
    </aside>
  );
};
