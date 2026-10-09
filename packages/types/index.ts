export type ProjectStatus =
  | 'CREATED'
  | 'UPLOADING'
  | 'UPLOADED'
  | 'ANALYZING'
  | 'ANALYZED'
  | 'BUILD_QUEUED'
  | 'BUILDING'
  | 'BUILD_FAILED'
  | 'BUILT'
  | 'DEPLOY_QUEUED'
  | 'DEPLOYING'
  | 'DEPLOYED'
  | 'DEPLOY_FAILED'
  | 'ARCHIVED';

export type BuildStatus =
  | 'QUEUED'
  | 'PREPARING'
  | 'BUILDING'
  | 'BUILT'
  | 'FAILED'
  | 'CANCELLED';

export type DeploymentStatus =
  | 'QUEUED'
  | 'DEPLOYING'
  | 'READY'
  | 'FAILED'
  | 'CANCELLED';

export type MobileAppStatus =
  | 'APP_CREATED'
  | 'APP_QUEUED'
  | 'APP_CONFIGURING'
  | 'APP_BUILDING'
  | 'APP_READY'
  | 'APP_FAILED';

export interface AnalysisResult {
  projectType: string;
  framework: string;
  frameworkVersion?: string;
  language: string;
  packageManager: string;
  runtime: string;
  buildCommand?: string;
  startCommand?: string;
  outputDirectory: string;
  port?: number;
  confidence: number;
  warnings: string[];
}

export interface Project {
  id: string;
  name: string;
  slug: string;
  status: ProjectStatus;
  framework?: string;
  language?: string;
  package_manager?: string;
  build_command?: string;
  output_directory?: string;
  active_deployment_id?: string;
  active_url?: string;
  created_at: string;
  updated_at: string;
}

export interface BuildLogEvent {
  timestamp: string;
  stage: string;
  level: 'debug' | 'info' | 'warning' | 'error';
  message: string;
}

export interface Build {
  id: string;
  project_id: string;
  upload_id: string;
  status: BuildStatus;
  framework?: string;
  build_command?: string;
  output_directory?: string;
  exit_code?: number;
  started_at?: string;
  completed_at?: string;
  duration_seconds?: number;
  error_message?: string;
  created_at: string;
}

export interface Deployment {
  id: string;
  project_id: string;
  build_id: string;
  status: DeploymentStatus;
  url: string;
  subdomain: string;
  runtime: string;
  created_at: string;
  completed_at?: string;
}

export interface MobileApp {
  id: string;
  project_id: string;
  app_name: string;
  package_id: string;
  version: string;
  version_code: number;
  theme: string;
  orientation: string;
  permissions?: string[];
  icon_base64?: string;
  website_url: string;
  website_url_is_localhost?: boolean;
  latest_build?: MobileBuild;
  updated_at?: string;
  created_at: string;
}

export interface NetworkInfo {
  lan_ip: string;
  port: number;
  lan_url: string;
  localhost_url: string;
  active_url?: string;
}

export interface MobileBuild {
  id: string;
  mobile_app_id: string;
  project_id: string;
  status: MobileAppStatus;
  build_target: string;
  apk_artifact_id?: string;
  source_artifact_id?: string;
  apk_download_url?: string;
  source_download_url?: string;
  apk_filename?: string;
  apk_sha256?: string;
  apk_size_bytes?: number;
  apk_package_name?: string;
  apk_version_name?: string;
  apk_version_code?: number;
  apk_signed?: boolean;
  apk_verified?: boolean;
  apk_target_url?: string;
  apk_url_is_localhost?: boolean;
  error_message?: string;
  started_at?: string;
  completed_at?: string;
  created_at: string;
}

export interface DashboardMetrics {
  projects: number;
  live_deployments: number;
  active_builds: number;
  total_deployments: number;
  failed_deployments: number;
  storage_bytes: number;
}

export interface EnvVar {
  id: string;
  key: string;
  value: string;
  is_secret: boolean;
  created_at: string;
  updated_at: string;
}

export interface User {
  id: string;
  email: string;
  name: string;
  role?: string;
  created_at: string;
}
