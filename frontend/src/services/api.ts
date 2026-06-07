/**
 * API service for V-Legal RAG demo.
 */

const CONNECTION_ERROR_MESSAGE =
  'Không thể kết nối backend. Vui lòng kiểm tra API URL hoặc CORS.';

function normalizeBaseUrl(url?: string): string {
  return (url || '').trim().replace(/\/+$/, '');
}

function isAbsoluteUrl(url: string): boolean {
  return /^https?:\/\//i.test(url);
}

function getApiBaseUrl(): string {
  const configuredUrl = normalizeBaseUrl(process.env.NEXT_PUBLIC_API_URL);
  if (configuredUrl) {
    if (process.env.NODE_ENV === 'production' && isAbsoluteUrl(configuredUrl)) {
      return '/api/backend';
    }
    return configuredUrl;
  }
  return process.env.NODE_ENV === 'development' ? 'http://localhost:8000' : '/api/backend';
}

const API_BASE_URL = getApiBaseUrl();

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
    this.baseUrl = normalizeBaseUrl(baseUrl);
  }

  private endpoint(path: string): string {
    const normalizedPath = path.startsWith('/') ? path : `/${path}`;
    return this.baseUrl ? `${this.baseUrl}${normalizedPath}` : normalizedPath;
  }

  private logRequest(endpoint: string): void {
    if (process.env.NODE_ENV === 'development') {
      console.info('API request', {
        apiBaseUrl: this.baseUrl || '(same-origin)',
        endpoint,
      });
    }
  }

  private async parseError(response: Response, fallbackMessage: string): Promise<string> {
    try {
      const error = await response.json();
      return error.detail || fallbackMessage;
    } catch {
      return fallbackMessage;
    }
  }

  private async fetchJson<T>(
    path: string,
    options: RequestInit | undefined,
    errorMessage: string,
  ): Promise<T> {
    const endpoint = this.endpoint(path);
    this.logRequest(endpoint);

    let response: Response;
    try {
      response = await fetch(endpoint, options);
    } catch (error) {
      if (process.env.NODE_ENV === 'development') {
        console.error('API fetch failed', {
          apiBaseUrl: this.baseUrl || '(same-origin)',
          endpoint,
          error,
        });
      }
      throw new Error(CONNECTION_ERROR_MESSAGE);
    }

    if (!response.ok) {
      throw new Error(await this.parseError(response, errorMessage));
    }

    return response.json();
  }

  async chat(request: ChatRequest): Promise<ChatResponse> {
    return this.fetchJson<ChatResponse>(
      '/chat',
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
      },
      'Lỗi khi gửi câu hỏi',
    );
  }

  async *chatStream(request: ChatRequest): AsyncGenerator<string> {
    const endpoint = this.endpoint('/chat');
    this.logRequest(endpoint);

    let response: Response;
    try {
      response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ ...request, stream: true }),
      });
    } catch (error) {
      if (process.env.NODE_ENV === 'development') {
        console.error('API fetch failed', {
          apiBaseUrl: this.baseUrl || '(same-origin)',
          endpoint,
          error,
        });
      }
      throw new Error(CONNECTION_ERROR_MESSAGE);
    }

    if (!response.ok) {
      throw new Error(await this.parseError(response, 'Lỗi khi gửi câu hỏi'));
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
          } catch {
            // Ignore partial or malformed stream frames.
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

    return this.fetchJson<Source[]>(
      `/chat/search?${params}`,
      undefined,
      'Lỗi khi tìm kiếm',
    );
  }

  async getDocuments(): Promise<{
    documents: DocumentInfo[];
    total_documents: number;
    total_chunks: number;
  }> {
    return this.fetchJson<{
      documents: DocumentInfo[];
      total_documents: number;
      total_chunks: number;
    }>('/admin/documents', undefined, 'Lỗi khi lấy danh sách văn bản');
  }

  async getStats(): Promise<SystemStats> {
    return this.fetchJson<SystemStats>('/admin/stats', undefined, 'Lỗi khi lấy thống kê');
  }

  async uploadDocument(file: File, status: string = 'Còn hiệu lực'): Promise<any> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('status', status);

    return this.fetchJson(
      '/admin/upload',
      {
        method: 'POST',
        body: formData,
      },
      'Lỗi khi upload',
    );
  }

  async deleteDocument(filename: string): Promise<any> {
    return this.fetchJson(
      `/admin/documents/${encodeURIComponent(filename)}`,
      {
        method: 'DELETE',
      },
      'Lỗi khi xóa văn bản',
    );
  }

  async healthCheck(): Promise<boolean> {
    try {
      const endpoint = this.endpoint('/health');
      this.logRequest(endpoint);
      const response = await fetch(endpoint);
      return response.ok;
    } catch {
      return false;
    }
  }
}

export const apiService = new ApiService();
export default apiService;
