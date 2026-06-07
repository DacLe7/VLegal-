'use client';

import { useState, useEffect } from 'react';
import { BarChart3, FileText, Database, Activity, RefreshCw } from 'lucide-react';
import apiService, { SystemStats, DocumentInfo } from '@/services/api';

export default function StatsPage() {
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isConnected, setIsConnected] = useState(true);

  const fetchData = async () => {
    setIsLoading(true);
    try {
      const isHealthy = await apiService.healthCheck();
      setIsConnected(isHealthy);

      if (isHealthy) {
        const [statsData, docsData] = await Promise.all([
          apiService.getStats(),
          apiService.getDocuments(),
        ]);
        setStats(statsData);
        setDocuments(docsData.documents);
      }
    } catch (err) {
      setIsConnected(false);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // Calculate stats
  const docsByType = documents.reduce((acc, doc) => {
    const type = doc.document_type || 'Khác';
    acc[type] = (acc[type] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const docsByYear = documents.reduce((acc, doc) => {
    const year = doc.year || 'Không rõ';
    acc[year] = (acc[year] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-legal-navy">Thống kê Hệ thống</h1>
        <button
          onClick={fetchData}
          className="flex items-center gap-2 px-4 py-2 text-gray-600 hover:text-gray-900 transition-colors"
        >
          <RefreshCw className={`w-5 h-5 ${isLoading ? 'animate-spin' : ''}`} />
          Làm mới
        </button>
      </div>

      {/* Connection Status */}
      <div className={`mb-6 p-4 rounded-xl flex items-center gap-3 ${
        isConnected ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'
      }`}>
        <Activity className={`w-5 h-5 ${isConnected ? 'text-green-600' : 'text-red-600'}`} />
        <span className={isConnected ? 'text-green-700' : 'text-red-700'}>
          {isConnected ? 'Backend đang hoạt động' : 'Không thể kết nối đến backend'}
        </span>
      </div>

      {isLoading ? (
        <div className="text-center py-12">
          <RefreshCw className="w-8 h-8 animate-spin mx-auto text-gray-400" />
        </div>
      ) : (
        <>
          {/* Overview Stats */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <StatCard
              icon={FileText}
              label="Tổng văn bản"
              value={stats?.total_documents || 0}
              color="blue"
            />
            <StatCard
              icon={Database}
              label="Tổng chunks"
              value={stats?.total_chunks || 0}
              color="amber"
            />
            <StatCard
              icon={BarChart3}
              label="Loại văn bản"
              value={Object.keys(docsByType).length}
              color="green"
            />
            <StatCard
              icon={Activity}
              label="Năm ban hành"
              value={Object.keys(docsByYear).length}
              color="purple"
            />
          </div>

          {/* Charts */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* By Type */}
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h2 className="text-lg font-semibold mb-4">Phân loại theo Loại văn bản</h2>
              <div className="space-y-3">
                {Object.entries(docsByType).sort((a, b) => b[1] - a[1]).map(([type, count]) => (
                  <div key={type}>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-gray-700">{type}</span>
                      <span className="font-medium">{count}</span>
                    </div>
                    <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-primary-500 rounded-full transition-all"
                        style={{ width: `${(count / documents.length) * 100}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* By Year */}
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h2 className="text-lg font-semibold mb-4">Phân loại theo Năm ban hành</h2>
              <div className="space-y-3">
                {Object.entries(docsByYear).sort((a, b) => b[0].localeCompare(a[0])).slice(0, 10).map(([year, count]) => (
                  <div key={year}>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-gray-700">{year}</span>
                      <span className="font-medium">{count}</span>
                    </div>
                    <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-legal-gold rounded-full transition-all"
                        style={{ width: `${(count / documents.length) * 100}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* System Info */}
          <div className="mt-6 bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="text-lg font-semibold mb-4">Thông tin Hệ thống</h2>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-gray-500">Collection:</span>
                <span className="ml-2 font-medium">{stats?.collection_name}</span>
              </div>
              <div>
                <span className="text-gray-500">Vector DB Path:</span>
                <span className="ml-2 font-medium font-mono text-xs">{stats?.vector_db_path}</span>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function StatCard({ 
  icon: Icon, 
  label, 
  value, 
  color 
}: { 
  icon: any; 
  label: string; 
  value: number; 
  color: 'blue' | 'amber' | 'green' | 'purple';
}) {
  const colors = {
    blue: 'bg-blue-50 text-blue-600 border-blue-200',
    amber: 'bg-amber-50 text-amber-600 border-amber-200',
    green: 'bg-green-50 text-green-600 border-green-200',
    purple: 'bg-purple-50 text-purple-600 border-purple-200',
  };

  return (
    <div className={`rounded-xl border p-4 ${colors[color]}`}>
      <div className="flex items-center gap-3">
        <Icon className="w-8 h-8" />
        <div>
          <div className="text-2xl font-bold">{value.toLocaleString()}</div>
          <div className="text-sm opacity-80">{label}</div>
        </div>
      </div>
    </div>
  );
}
