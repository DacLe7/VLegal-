import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import '@/styles/globals.css';
import Sidebar from '@/components/Sidebar';

const inter = Inter({ subsets: ['latin', 'vietnamese'] });

export const metadata: Metadata = {
  title: 'V-Legal Bot - Trợ lý Pháp luật Việt Nam',
  description: 'Chatbot thông minh hỗ trợ tra cứu và giải đáp pháp luật Việt Nam',
  icons: {
    icon: '/favicon.ico',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="vi">
      <body className={inter.className}>
        <div className="flex h-screen">
          <Sidebar />
          <main className="flex-1 overflow-hidden bg-legal-cream">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
