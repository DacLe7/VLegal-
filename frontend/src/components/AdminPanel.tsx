'use client';

import { useState, useEffect } from 'react';
import { Upload, Trash2, FileText, RefreshCw, CheckCircle, XCircle, Loader2 } from 'lucide-react';
import apiService, { DocumentInfo, SystemStats } from '@/services/api';

export default function AdminPanel() {
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<{ success: boolean; message: string } | null>(null);

  const fetchData = async () => {
    setIsLoading(true);
    try {
      const [docsResponse, statsResponse] = await Promise.all([
        apiService.getDocuments(),
        apiService.getStats(),
      ]);
      setDocuments(docsResponse.documents);
      setStats(statsResponse);
    } catch (err) {
      console.error('Error fetching data:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setUploadStatus(null);

    try {
      const result = await apiService.uploadDocument(file);
      setUploadStatus({
        success: result.status === 'success',
        message: result.message,
      });
      fetchData();
    } catch (err) {
      setUploadStatus({
        success: false,
        message: err instanceof Error ? err.message : 'Lỗi upload',
      });
    } finally {
      setIsUploading(false);
      e.target.value = '';
    }
  };

  const handleDelete = async (filename: string) => {
    if (!confirm(`Bạn có chắc muốn xóa "${filename}"?`)) return;

    try {
      await apiService.deleteDocument(filename);
      fetchData();
    } catch (err) {
      alert('Lỗi khi xóa văn bản');
    }
  };

  return (
    <div className="p-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-legal-navy">Quản lý Văn bản Pháp luật</h1>
        <button
          onClick={fetchData}
          className="flex items-center gap-2 px-4 py-2 text-gray-600 hover:text-gray-900 transition-colors"
        >
          <RefreshCw className={`w-5 h-5 ${isLoading ? 'animate-spin' : ''}`} />
          Làm mới
        </button>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <div className="bg-white rounded-xl p-4 border border-gray-200 shadow-sm">
            <div className="text-3xl font-bold text-primary-600">{stats.total_documents}</div>
            <div className="text-gray-600">Văn bản</div>
          </div>
          <div className="bg-white rounded-xl p-4 border border-gray-200 shadow-sm">
            <div className="text-3xl font-bold text-legal-gold">{stats.total_chunks}</div>
            <div className="text-gray-600">Đoạn văn bản</div>
          </div>
          <div className="bg-white rounded-xl p-4 border border-gray-200 shadow-sm">
            <div className="text-3xl font-bold text-green-600">{stats.collection_name}</div>
            <div className="text-gray-600">Collection</div>
          </div>
        </div>
      )}

      {/* Upload Section */}
      <div className="bg-white rounded-xl p-6 border border-gray-200 shadow-sm mb-6">
        <h2 className="text-lg font-semibold mb-4">Upload Văn bản Mới</h2>
        
        <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed border-gray-300 rounded-xl cursor-pointer hover:border-primary-500 hover:bg-primary-50 transition-colors">
          <div className="flex flex-col items-center">
            {isUploading ? (
              <Loader2 className="w-8 h-8 text-primary-500 animate-spin" />
            ) : (
              <Upload className="w-8 h-8 text-gray-400" />
            )}
            <p className="mt-2 text-sm text-gray-500">
              {isUploading ? 'Đang upload...' : 'Click để chọn file .docx hoặc .doc'}
            </p>
          </div>
          <input
            type="file"
            className="hidden"
            accept=".docx,.doc"
            onChange={handleUpload}
            disabled={isUploading}
          />
        </label>

        {uploadStatus && (
          <div
            className={`mt-4 p-3 rounded-lg flex items-center gap-2 ${
              uploadStatus.success
                ? 'bg-green-50 text-green-700 border border-green-200'
                : 'bg-red-50 text-red-700 border border-red-200'
            }`}
          >
            {uploadStatus.success ? (
              <CheckCircle className="w-5 h-5" />
            ) : (
              <XCircle className="w-5 h-5" />
            )}
            {uploadStatus.message}
          </div>
        )}
      </div>

      {/* Documents List */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="p-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold">Danh sách Văn bản ({documents.length})</h2>
        </div>
        
        {isLoading ? (
          <div className="p-8 text-center">
            <Loader2 className="w-8 h-8 animate-spin mx-auto text-gray-400" />
          </div>
        ) : documents.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            Chưa có văn bản nào. Upload văn bản để bắt đầu.
          </div>
        ) : (
          <div className="divide-y divide-gray-100">
            {documents.map((doc, index) => (
              <div
                key={index}
                className="p-4 flex items-center justify-between hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <FileText className="w-8 h-8 text-primary-500" />
                  <div>
                    <div className="font-medium text-gray-900">{doc.filename}</div>
                    <div className="text-sm text-gray-500">
                      {doc.document_type} • {doc.document_number} • {doc.year}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <span className="text-sm text-gray-500">{doc.chunk_count} chunks</span>
                  <button
                    onClick={() => handleDelete(doc.filename)}
                    className="p-2 text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                    title="Xóa văn bản"
                  >
                    <Trash2 className="w-5 h-5" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
