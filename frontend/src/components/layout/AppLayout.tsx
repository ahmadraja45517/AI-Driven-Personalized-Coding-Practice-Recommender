import { Outlet, Link, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { LayoutDashboard, Map, BarChart2, Lightbulb, LogOut, Code2, User } from 'lucide-react';

export default function AppLayout() {
  const { user, logout } = useAuth();
  const location = useLocation();

  const navItems = [
    { name: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
    { name: 'Roadmap', path: '/roadmap', icon: Map },
    { name: 'Analytics', path: '/analytics', icon: BarChart2 },
    { name: 'Recommendations', path: '/recommendations', icon: Lightbulb },
    { name: 'Profile', path: '/profile', icon: User },
  ];

  return (
    <div className="flex h-screen bg-slate-900">
      {/* Sidebar */}
      <aside className="w-72 bg-slate-950 border-r border-slate-800 flex flex-col hidden md:flex">
        <div className="p-6 flex items-center space-x-3 border-b border-slate-800">
          <Code2 className="text-brand-500 shrink-0" size={28} />
           <h2 className="text-xl font-bold text-white tracking-tight">
            AI Coding Recommender
           </h2>
        </div>
        <nav className="flex-1 p-4 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname.startsWith(item.path);
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center space-x-3 px-4 py-3 rounded-lg transition-colors ${
                  isActive ? 'bg-slate-800 text-brand-400 font-medium' : 'text-slate-400 hover:bg-slate-800/50 hover:text-slate-200'
                }`}
              >
                <Icon size={20} />
                <span>{item.name}</span>
              </Link>
            );
          })}
        </nav>
        <div className="p-4 border-t border-slate-800">
          <div className="mb-4 px-4">
            <p className="text-sm font-medium text-slate-200 truncate">{user?.full_name}</p>
            <p className="text-xs text-slate-500 truncate">{user?.email}</p>
          </div>
          <button
            onClick={logout}
            className="flex items-center space-x-3 px-4 py-2 w-full text-left text-red-400 hover:bg-slate-800 rounded-lg transition-colors"
          >
            <LogOut size={20} />
            <span>Logout</span>
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto bg-slate-900 text-slate-200">
        <div className="p-8 max-w-6xl mx-auto">
          <Outlet />
        </div>
      </main>
    </div>
  );
}