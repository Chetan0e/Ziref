import { Project, Build, Deployment, MobileApp, MobileBuild, EnvVar, User, AnalysisResult } from '@ziref/types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

class ApiClient {
  private getToken(): string | null {
    if (typeof window === 'undefined') return null;
    return localStorage.getItem('ziref_token');
  }

  setToken(token: string) {
    if (typeof window !== 'undefined') {
      localStorage.setItem('ziref_token', token);
    }
  }

  clearToken() {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('ziref_token');
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

    const res = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers,
    });

    if (!res.ok) {
      let errMsg = `Request failed: ${res.status} ${res.statusText}`;
      try {
        const errorData = await res.json();
        if (errorData.error?.message) {
          errMsg = errorData.error.message;
        } else if (errorData.detail) {
          errMsg = typeof errorData.detail === 'string' ? errorData.detail : JSON.stringify(errorData.detail);
        }
      } catch (_) {}
      throw new Error(errMsg);
    }

    if (res.status === 204) {
      return {} as T;
    }

    return res.json();
  }

  // --- Auth ---
  async register(email: string, password: string, name: string) {
    const data = await this.request<{ token: string; user: User }>('/api/v1/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, name }),
    });
    this.setToken(data.token);
    return data;
  }

  async login(email: string, password: string) {
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

  logout() {
    this.clearToken();
  }

  // --- Projects ---
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

  async updateProject(id: string, updates: { name?: string; build_command?: string; output_directory?: string }): Promise<Project> {
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

  // --- Upload & Analyzer ---
  async uploadZip(projectId: string, file: File): Promise<{
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

  // --- Builds ---
  async triggerBuild(projectId: string, uploadId: string, buildCommand?: string, outputDirectory?: string): Promise<Build> {
    return this.request<Build>(`/api/v1/projects/${projectId}/builds`, {
      method: 'POST',
      body: JSON.stringify({
        upload_id: uploadId,
        build_command: buildCommand,
        output_directory: outputDirectory,
      }),
    });
  }

  async getBuild(buildId: string): Promise<Build> {
    return this.request<Build>(`/api/v1/builds/${buildId}`);
  }

  async getBuildLogs(buildId: string): Promise<{ build_id: string; events: any[] }> {
    return this.request(`/api/v1/builds/${buildId}/logs`);
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
        if (parsed.stage === 'done' || parsed.message === '[STREAM_CLOSED]') {
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

  // --- Deployments ---
  async getDeployments(projectId: string): Promise<Deployment[]> {
    return this.request<Deployment[]>(`/api/v1/projects/${projectId}/deployments`);
  }

  async rollback(projectId: string, deploymentId: string): Promise<Deployment> {
    return this.request<Deployment>(`/api/v1/projects/${projectId}/rollback`, {
      method: 'POST',
      body: JSON.stringify({ deployment_id: deploymentId }),
    });
  }

  // --- Environment Variables ---
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

  // --- Appify ---
  async getMobileApps(projectId: string): Promise<MobileApp[]> {
    return this.request<MobileApp[]>(`/api/v1/projects/${projectId}/apps`);
  }

  async createMobileApp(projectId: string, config: {
    app_name: string;
    package_id: string;
    version?: string;
    version_code?: number;
    theme?: string;
    orientation?: string;
  }): Promise<MobileApp> {
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

  // --- Demo Project ---
  async createDemoProject(): Promise<{ project_id: string; slug: string; build_id: string; message: string }> {
    return this.request('/api/v1/projects/create-demo', {
      method: 'POST',
    });
  }

  // --- Custom Domains ---
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

  // --- Runtime Logs ---
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

  // --- Git Import ---
  async importGitProject(name: string, repoUrl: string, branch?: string, slug?: string): Promise<{
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

  // --- Redeploy & Builds Control ---
  async redeployProject(projectId: string): Promise<{ project_id: string; build_id: string; status: string; message: string }> {
    return this.request(`/api/v1/projects/${projectId}/redeploy`, {
      method: 'POST',
    });
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

  // --- Analytics ---
  async getProjectAnalytics(projectId: string): Promise<any> {
    return this.request(`/api/v1/projects/${projectId}/analytics`);
  }

  // --- Webhooks ---
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
}

export const api = new ApiClient();

