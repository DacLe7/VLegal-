/**
 * API Service for V-Legal Bot
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface ChatRequest {
  question: string;
  top_k?: number;
  document_type?: string;
  year?: number;
  stream?: boolean;
}

export interface Source {
  content: string;
  reference: string;
  score: number;
  filename: string;
  document_type: string;
  document_number: string;
}

export interface ChatResponse {
  answer: string;
  query: string;
  sources: Source[];
  metadata: Record<string, any>;
}

export interface DocumentInfo {
  filename: string;
  document_number: string;
  document_type: string;
  year: string;
  chunk_count: number;
}

export interface SystemStats {
  total_documents: number;
  total_chunks: number;
  collection_name: string;
  vector_db_path: string;
}

class ApiService {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  async chat(request: ChatRequest): Promise<ChatResponse> {
    const response = await fetch(`${this.baseUrl}/chat/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Lỗi khi gửi câu hỏi');
    }

    return response.json();
  }

  async *chatStream(request: ChatRequest): AsyncGenerator<string> {
    const response = await fetch(`${this.baseUrl}/chat/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ ...request, stream: true }),
    });

    if (!response.ok) {
      throw new Error('Lỗi khi gửi câu hỏi');
    }

    const reader = response.body?.getReader();
    const decoder = new TextDecoder();

    if (!reader) {
      throw new Error('Không thể đọc response');
    }

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            if (data.chunk) {
              yield data.chunk;
            }
            if (data.done) {
              return;
            }
          } catch (e) {
            // Skip invalid JSON
          }
        }
      }
    }
  }

  async search(query: string, topK: number = 10): Promise<Source[]> {
    const params = new URLSearchParams({
      query,
      top_k: topK.toString(),
    });

    const response = await fetch(`${this.baseUrl}/chat/search?${params}`);

    if (!response.ok) {
      throw new Error('Lỗi khi tìm kiếm');
    }

    return response.json();
  }

  async getDocuments(): Promise<{ documents: DocumentInfo[]; total_documents: number; total_chunks: number }> {
    const response = await fetch(`${this.baseUrl}/admin/documents`);

    if (!response.ok) {
      throw new Error('Lỗi khi lấy danh sách văn bản');
    }

    return response.json();
  }

  async getStats(): Promise<SystemStats> {
    const response = await fetch(`${this.baseUrl}/admin/stats`);

    if (!response.ok) {
      throw new Error('Lỗi khi lấy thống kê');
    }

    return response.json();
  }

  async uploadDocument(file: File, status: string = 'Còn hiệu lực'): Promise<any> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('status', status);

    const response = await fetch(`${this.baseUrl}/admin/upload`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Lỗi khi upload');
    }

    return response.json();
  }

  async deleteDocument(filename: string): Promise<any> {
    const response = await fetch(`${this.baseUrl}/admin/documents/${encodeURIComponent(filename)}`, {
      method: 'DELETE',
    });

    if (!response.ok) {
      throw new Error('Lỗi khi xóa văn bản');
    }

    return response.json();
  }

  async healthCheck(): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseUrl}/health`);
      return response.ok;
    } catch {
      return false;
    }
  }
}

export const apiService = new ApiService();
export default apiService;
