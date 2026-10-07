import {
  Project,
  Build,
  Deployment,
  MobileApp,
  MobileBuild,
  EnvVar,
  User,
  AnalysisResult,
  DashboardMetrics,
} from '@ziref/types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const DEPLOY_BASE = process.env.NEXT_PUBLIC_DEPLOY_DOMAIN || 'http://localhost:8080';

export class ApiError extends Error {
  status: number;
  code?: string;
  details?: any;

  constructor(message: string, status: number, code?: string, details?: any) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

function getCookie(name: string): string | null {
  if (typeof document === 'undefined') return null;
  const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
  return match ? decodeURIComponent(match[2]) : null;
}

function setCookie(name: string, value: string, days = 30) {
  if (typeof document === 'undefined') return;
  const expires = new Date(Date.now() + days * 864e5).toUTCString();
  document.cookie = `${name}=${encodeURIComponent(value)}; path=/; expires=${expires}; SameSite=Lax`;
}

function deleteCookie(name: string) {
  if (typeof document === 'undefined') return;
  document.cookie = `${name}=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT; SameSite=Lax`;
}

export interface SystemStatus {
  worker: {
    status: 'online' | 'offline';
    sandbox_mode: 'docker' | 'subprocess' | 'unavailable';
    docker_available: boolean;
    last_seen: string | null;
  };
  metrics: {
    total_projects: number;
    active_deployments: number;
    active_builds: number;
  };
}

class ApiClient {
  public getToken(): string | null {
    if (typeof window === 'undefined') return null;
    const fromStorage = localStorage.getItem('ziref_token');
    if (fromStorage) return fromStorage;
    const fromCookie = getCookie('ziref_token');
    if (fromCookie) {
      try {
        localStorage.setItem('ziref_token', fromCookie);
      } catch (_) {}
      return fromCookie;
    }
    return null;
  }

  public setToken(token: string) {
    if (typeof window !== 'undefined') {
      try {
        localStorage.setItem('ziref_token', token);
      } catch (_) {}
      setCookie('ziref_token', token);
      window.dispatchEvent(new Event('ziref:auth-change'));
    }
  }

  public clearToken() {
    if (typeof window !== 'undefined') {
      try {
        localStorage.removeItem('ziref_token');
      } catch (_) {}
      deleteCookie('ziref_token');
      window.dispatchEvent(new Event('ziref:auth-change'));
    }
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const token = this.getToken();
    const headers: Record<string, string> = {
      ...(options.headers as Record<string, string>),
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    if (!(options.body instanceof FormData) && !headers['Content-Type']) {
      headers['Content-Type'] = 'application/json';
    }

    let res: Response;
    const controller = new AbortController();
    const isUpload = options.body instanceof FormData;
    const timeoutMs = isUpload ? 120000 : 15000;
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    try {
      res = await fetch(`${API_BASE}${endpoint}`, {
        ...options,
        headers,
        signal: options.signal || controller.signal,
      });
    } catch (networkErr: any) {
      if (networkErr.name === 'AbortError') {
        throw new ApiError(
          'Request timed out. The server took too long to respond.',
          408,
          'TIMEOUT'
        );
      }
      throw new ApiError(
        'Unable to connect to the backend server. Please check your network connection.',
        0,
        'NETWORK_ERROR'
      );
    } finally {
      clearTimeout(timeoutId);
    }

    if (!res.ok) {
      let errMsg = `Request failed: ${res.status} ${res.statusText}`;
      let errCode = `HTTP_${res.status}`;
      let errDetails: any = null;

      try {
        const errorData = await res.json();
        if (errorData.error?.message) {
          errMsg = errorData.error.message;
          errCode = errorData.error.code || errCode;
          errDetails = errorData.error.details;
        } else if (errorData.detail) {
          errMsg = typeof errorData.detail === 'string' ? errorData.detail : JSON.stringify(errorData.detail);
        }
      } catch (_) {}

      // Handle session expiration
      if (res.status === 401) {
        if (typeof window !== 'undefined') {
          window.dispatchEvent(new CustomEvent('ziref:auth-unauthorized', { detail: { endpoint } }));
        }
      }

      throw new ApiError(errMsg, res.status, errCode, errDetails);
    }

    if (res.status === 204) {
      return {} as T;
    }

    return res.json();
  }

  // ==========================================
  // Auth API
  // ==========================================
  async register(email: string, password: string, name: string): Promise<{ token: string; user: User }> {
    const data = await this.request<{ token: string; user: User }>('/api/v1/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, name }),
    });
    this.setToken(data.token);
    return data;
  }

  async login(email: string, password: string): Promise<{ token: string; user: User }> {
    const data = await this.request<{ token: string; user: User }>('/api/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    this.setToken(data.token);
    return data;
  }

  async getMe(): Promise<User> {
    return this.request<User>('/api/v1/auth/me');
  }

  async logout(): Promise<void> {
    try {
      await this.request('/api/v1/auth/logout', { method: 'POST' }).catch(() => {});
    } finally {
      this.clearToken();
    }
  }

  // ==========================================
  // Projects API
  // ==========================================
  async getProjects(): Promise<Project[]> {
    return this.request<Project[]>('/api/v1/projects');
  }

  async createProject(name: string, slug?: string): Promise<Project> {
    return this.request<Project>('/api/v1/projects', {
      method: 'POST',
      body: JSON.stringify({ name, slug }),
    });
  }

  async getProject(idOrSlug: string): Promise<Project> {
    return this.request<Project>(`/api/v1/projects/${idOrSlug}`);
  }

  async updateProject(
    id: string,
    updates: { name?: string; build_command?: string; output_directory?: string }
  ): Promise<Project> {
    return this.request<Project>(`/api/v1/projects/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(updates),
    });
  }

  async deleteProject(id: string): Promise<void> {
    return this.request<void>(`/api/v1/projects/${id}`, {
      method: 'DELETE',
    });
  }

  async redeployProject(projectId: string): Promise<{ project_id: string; build_id: string; status: string; message: string }> {
    return this.request(`/api/v1/projects/${projectId}/redeploy`, {
      method: 'POST',
    });
  }

  // ==========================================
  // Uploads & Analysis API
  // ==========================================
  async uploadZip(
    projectId: string,
    file: File
  ): Promise<{
    id: string;
    project_id: string;
    filename: string;
    file_size: number;
    checksum: string;
    analysis?: AnalysisResult;
  }> {
    const formData = new FormData();
    formData.append('file', file);
    return this.request(`/api/v1/projects/${projectId}/uploads`, {
      method: 'POST',
      body: formData,
    });
  }

  async importGitProject(
    name: string,
    repoUrl: string,
    branch?: string,
    slug?: string
  ): Promise<{
    project_id: string;
    slug: string;
    build_id: string;
    analysis?: AnalysisResult;
    message: string;
  }> {
    return this.request('/api/v1/projects/import-git', {
      method: 'POST',
      body: JSON.stringify({ name, repo_url: repoUrl, branch, slug }),
    });
  }

  // ==========================================
  // Builds API
  // ==========================================
  async triggerBuild(
    projectId: string,
    uploadId: string,
    buildCommand?: string,
    outputDirectory?: string
  ): Promise<Build> {
    return this.request<Build>(`/api/v1/projects/${projectId}/builds`, {
      method: 'POST',
      body: JSON.stringify({
        upload_id: uploadId,
        build_command: buildCommand,
        output_directory: outputDirectory,
      }),
    });
  }

  async getBuilds(projectId: string): Promise<Build[]> {
    return this.request<Build[]>(`/api/v1/projects/${projectId}/builds`);
  }

  async getBuild(buildId: string): Promise<Build> {
    return this.request<Build>(`/api/v1/builds/${buildId}`);
  }

  async getBuildLogs(buildId: string): Promise<{ build_id: string; events: any[] }> {
    return this.request(`/api/v1/builds/${buildId}/logs`);
  }

  async retryBuild(buildId: string): Promise<Build> {
    return this.request<Build>(`/api/v1/builds/${buildId}/retry`, {
      method: 'POST',
    });
  }

  async cancelBuild(buildId: string): Promise<{ message: string; build_id: string }> {
    return this.request(`/api/v1/builds/${buildId}/cancel`, {
      method: 'POST',
    });
  }

  async getBuildDiagnosis(buildId: string): Promise<any> {
    return this.request(`/api/v1/builds/${buildId}/diagnosis`);
  }

  streamBuildLogs(
    buildId: string,
    onMessage: (event: { timestamp: string; stage: string; level: string; message: string }) => void,
    onComplete?: () => void
  ): () => void {
    const es = new EventSource(`${API_BASE}/api/v1/builds/${buildId}/logs/stream`);
    es.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data);
        if (parsed.stage === 'done' || parsed.stage === 'completed' || parsed.message === '[STREAM_CLOSED]') {
          es.close();
          if (onComplete) onComplete();
          return;
        }
        onMessage(parsed);
      } catch (_) {}
    };
    es.onerror = () => {
      es.close();
      if (onComplete) onComplete();
    };
    return () => es.close();
  }

  // ==========================================
  // Deployments API
  // ==========================================
  async getDeployments(projectId: string): Promise<Deployment[]> {
    return this.request<Deployment[]>(`/api/v1/projects/${projectId}/deployments`);
  }

  async getDeployment(deploymentId: string): Promise<Deployment> {
    return this.request<Deployment>(`/api/v1/deployments/${deploymentId}`);
  }

  async rollback(projectId: string, deploymentId: string): Promise<Deployment> {
    return this.request<Deployment>(`/api/v1/projects/${projectId}/rollback`, {
      method: 'POST',
      body: JSON.stringify({ deployment_id: deploymentId }),
    });
  }

  // ==========================================
  // Environment Variables API
  // ==========================================
  async getEnvVars(projectId: string): Promise<EnvVar[]> {
    return this.request<EnvVar[]>(`/api/v1/projects/${projectId}/env`);
  }

  async createEnvVar(projectId: string, key: string, value: string, isSecret: boolean = true): Promise<EnvVar> {
    return this.request<EnvVar>(`/api/v1/projects/${projectId}/env`, {
      method: 'POST',
      body: JSON.stringify({ key, value, is_secret: isSecret }),
    });
  }

  async deleteEnvVar(projectId: string, key: string): Promise<void> {
    return this.request<void>(`/api/v1/projects/${projectId}/env/${key}`, {
      method: 'DELETE',
    });
  }

  // ==========================================
  // Mobile / Appify API
  // ==========================================
  async getMobileApps(projectId: string): Promise<MobileApp[]> {
    return this.request<MobileApp[]>(`/api/v1/projects/${projectId}/apps`);
  }

  async createMobileApp(
    projectId: string,
    config: {
      app_name: string;
      package_id: string;
      version?: string;
      version_code?: number;
      theme?: string;
      orientation?: string;
      permissions?: string[];
      icon_base64?: string;
    }
  ): Promise<MobileApp> {
    return this.request<MobileApp>(`/api/v1/projects/${projectId}/apps`, {
      method: 'POST',
      body: JSON.stringify(config),
    });
  }

  async triggerMobileBuild(appId: string): Promise<MobileBuild> {
    return this.request<MobileBuild>(`/api/v1/apps/${appId}/build`, {
      method: 'POST',
    });
  }

  async getMobileBuild(buildId: string): Promise<MobileBuild> {
    return this.request<MobileBuild>(`/api/v1/mobile-builds/${buildId}`);
  }

  getPreviewUrl(slug: string): string {
    return `${DEPLOY_BASE}/sites/${slug}/`;
  }

  getMobileApkDownloadUrl(buildId: string): string {
    return `${API_BASE}/api/v1/mobile-builds/${buildId}/download`;
  }

  getMobileSourceDownloadUrl(buildId: string): string {
    return `${API_BASE}/api/v1/mobile-builds/${buildId}/download/source`;
  }

  streamMobileLogs(
    buildId: string,
    onMessage: (event: any) => void,
    onComplete?: () => void
  ): () => void {
    const es = new EventSource(`${API_BASE}/api/v1/mobile-builds/${buildId}/logs/stream`);
    es.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data);
        if (parsed.stage === 'done' || parsed.stage === 'completed' || parsed.message === '[STREAM_CLOSED]') {
          es.close();
          if (onComplete) onComplete();
          return;
        }
        onMessage(parsed);
      } catch (_) {}
    };
    es.onerror = () => {
      es.close();
      if (onComplete) onComplete();
    };
    return () => es.close();
  }

  // ==========================================
  // Custom Domains API
  // ==========================================
  async getDomains(projectId: string): Promise<any[]> {
    return this.request(`/api/v1/projects/${projectId}/domains`);
  }

  async addDomain(projectId: string, domain: string): Promise<any> {
    return this.request(`/api/v1/projects/${projectId}/domains`, {
      method: 'POST',
      body: JSON.stringify({ domain }),
    });
  }

  async verifyDomain(projectId: string, domainId: string): Promise<any> {
    return this.request(`/api/v1/projects/${projectId}/domains/${domainId}/verify`, {
      method: 'POST',
    });
  }

  async deleteDomain(projectId: string, domainId: string): Promise<void> {
    return this.request(`/api/v1/projects/${projectId}/domains/${domainId}`, {
      method: 'DELETE',
    });
  }

  // ==========================================
  // Runtime Logs API
  // ==========================================
  async getRuntimeLogs(projectId: string): Promise<any[]> {
    return this.request(`/api/v1/projects/${projectId}/runtime-logs`);
  }

  streamRuntimeLogs(
    projectId: string,
    onMessage: (event: any) => void
  ): () => void {
    const es = new EventSource(`${API_BASE}/api/v1/projects/${projectId}/runtime-logs/stream`);
    es.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data);
        onMessage(parsed);
      } catch (_) {}
    };
    return () => es.close();
  }

  // ==========================================
  // Webhooks & Analytics API
  // ==========================================
  async getWebhooks(projectId: string): Promise<any[]> {
    return this.request(`/api/v1/projects/${projectId}/webhooks`);
  }

  async createWebhook(projectId: string, url: string, description?: string, events?: string[]): Promise<any> {
    return this.request(`/api/v1/projects/${projectId}/webhooks`, {
      method: 'POST',
      body: JSON.stringify({ url, description, events }),
    });
  }

  async deleteWebhook(projectId: string, webhookId: string): Promise<void> {
    return this.request(`/api/v1/projects/${projectId}/webhooks/${webhookId}`, {
      method: 'DELETE',
    });
  }

  async testWebhook(projectId: string, webhookId: string): Promise<any> {
    return this.request(`/api/v1/projects/${projectId}/webhooks/${webhookId}/test`, {
      method: 'POST',
    });
  }

  async getProjectAnalytics(projectId: string): Promise<any> {
    return this.request(`/api/v1/projects/${projectId}/analytics`);
  }

  // ==========================================
  // System & Worker Status API
  // ==========================================
  async getSystemStatus(): Promise<SystemStatus> {
    return this.request<SystemStatus>('/api/v1/system/status');
  }

  async getDashboardMetrics(): Promise<DashboardMetrics> {
    return this.request<DashboardMetrics>('/api/v1/dashboard/metrics');
  }
}

export { type DashboardMetrics };

export const api = new ApiClient();
