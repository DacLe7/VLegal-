'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Scale, MessageSquare, Settings, BookOpen, BarChart3 } from 'lucide-react';

export default function Sidebar() {
  const pathname = usePathname();

  const navItems = [
    { href: '/', icon: MessageSquare, label: 'Chat' },
    { href: '/search', icon: BookOpen, label: 'Tìm kiếm' },
    { href: '/admin', icon: Settings, label: 'Quản lý' },
    { href: '/stats', icon: BarChart3, label: 'Thống kê' },
  ];

  return (
    <div className="w-64 bg-legal-navy text-white flex flex-col">
      {/* Logo */}
      <div className="p-4 border-b border-white/10">
        <Link href="/" className="flex items-center gap-3">
          <div className="p-2 bg-legal-gold rounded-lg">
            <Scale className="w-6 h-6 text-legal-navy" />
          </div>
          <div>
            <h1 className="font-bold text-lg">V-Legal Bot</h1>
            <p className="text-xs text-gray-400">Trợ lý Pháp luật</p>
          </div>
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4">
        <ul className="space-y-2">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                    isActive
                      ? 'bg-white/10 text-legal-gold'
                      : 'text-gray-300 hover:bg-white/5 hover:text-white'
                  }`}
                >
                  <item.icon className="w-5 h-5" />
                  <span>{item.label}</span>
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-white/10">
        <div className="text-xs text-gray-400 text-center">
          <p>Phiên bản 1.0.0</p>
          <p className="mt-1">© 2024 V-Legal Bot</p>
        </div>
      </div>
    </div>
  );
}
