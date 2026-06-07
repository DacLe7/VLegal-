'use client';

import { useState } from 'react';
import { Search, BookOpen, Filter, Loader2 } from 'lucide-react';
import apiService, { Source } from '@/services/api';

export default function SearchPage() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<Source[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setIsLoading(true);
    setHasSearched(true);

    try {
      const data = await apiService.search(query, 20);
      setResults(data);
    } catch (err) {
      console.error('Search error:', err);
      setResults([]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold text-legal-navy mb-6">Tìm kiếm Văn bản Pháp luật</h1>

      {/* Search Form */}
      <form onSubmit={handleSearch} className="mb-6">
        <div className="flex gap-3">
          <div className="flex-1 relative">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Nhập từ khóa tìm kiếm (VD: quyền sở hữu, hợp đồng, đất đai...)"
              className="w-full pl-12 pr-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>
          <button
            type="submit"
            disabled={isLoading}
            className="px-6 py-3 bg-primary-600 text-white rounded-xl hover:bg-primary-700 disabled:opacity-50 transition-colors flex items-center gap-2"
          >
            {isLoading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Search className="w-5 h-5" />
            )}
            Tìm kiếm
          </button>
        </div>
      </form>

      {/* Results */}
      {isLoading ? (
        <div className="text-center py-12">
          <Loader2 className="w-8 h-8 animate-spin mx-auto text-primary-500" />
          <p className="mt-2 text-gray-500">Đang tìm kiếm...</p>
        </div>
      ) : hasSearched ? (
        <>
          <div className="mb-4 text-sm text-gray-600">
            Tìm thấy {results.length} kết quả cho &quot;{query}&quot;
          </div>

          {results.length === 0 ? (
            <div className="text-center py-12 bg-white rounded-xl border border-gray-200">
              <BookOpen className="w-12 h-12 mx-auto text-gray-300" />
              <p className="mt-4 text-gray-500">Không tìm thấy kết quả phù hợp</p>
              <p className="text-sm text-gray-400">Thử với từ khóa khác</p>
            </div>
          ) : (
            <div className="space-y-4">
              {results.map((result, index) => (
                <div
                  key={index}
                  className="bg-white rounded-xl border border-gray-200 p-4 hover:shadow-md transition-shadow"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="px-2 py-1 bg-primary-100 text-primary-700 text-xs font-medium rounded">
                          {result.document_type || 'Văn bản'}
                        </span>
                        <span className="text-sm text-gray-500">
                          {result.document_number}
                        </span>
                      </div>
                      <h3 className="font-medium text-legal-navy mb-2">
                        {result.reference}
                      </h3>
                      <p className="text-sm text-gray-600 line-clamp-3">
                        {result.content}
                      </p>
                      <div className="mt-2 text-xs text-gray-400">
                        Nguồn: {result.filename}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-2xl font-bold text-primary-600">
                        {(result.score * 100).toFixed(0)}%
                      </div>
                      <div className="text-xs text-gray-500">Độ liên quan</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      ) : (
        <div className="text-center py-12 bg-white rounded-xl border border-gray-200">
          <Search className="w-12 h-12 mx-auto text-gray-300" />
          <p className="mt-4 text-gray-500">Nhập từ khóa để tìm kiếm văn bản pháp luật</p>
        </div>
      )}
    </div>
  );
}
