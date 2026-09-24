import os
import json
import urllib.request
import urllib.parse
import urllib.error
import mimetypes
import uuid
import time
from typing import Dict, Any, List, Optional
from packages.cli.config import cli_config

class ZirefCliError(Exception):
    pass

class ZirefApiClient:
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or cli_config.get_api_url()).rstrip("/")

    def _headers(self, content_type: Optional[str] = "application/json") -> Dict[str, str]:
        headers = {"User-Agent": "Ziref-CLI/1.0"}
        if content_type:
            headers["Content-Type"] = content_type
        token = cli_config.get_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def _request(self, method: str, endpoint: str, data: Optional[Dict[str, Any]] = None, raw_body: Optional[bytes] = None, content_type: Optional[str] = "application/json") -> Any:
        url = f"{self.base_url}{endpoint}"
        body_bytes = None
        if data is not None:
            body_bytes = json.dumps(data).encode("utf-8")
        elif raw_body is not None:
            body_bytes = raw_body

        req = urllib.request.Request(
            url,
            data=body_bytes,
            headers=self._headers(content_type),
            method=method
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                if resp.status == 204:
                    return {}
                resp_body = resp.read().decode("utf-8")
                if resp_body:
                    return json.loads(resp_body)
                return {}
        except urllib.error.HTTPError as e:
            err_msg = f"HTTP {e.code}: {e.reason}"
            try:
                err_data = json.loads(e.read().decode("utf-8"))
                if "error" in err_data and "message" in err_data["error"]:
                    err_msg = err_data["error"]["message"]
                elif "detail" in err_data:
                    err_msg = err_data["detail"]
            except Exception:
                pass
            raise ZirefCliError(err_msg)
        except urllib.error.URLError as e:
            raise ZirefCliError(f"Could not connect to Ziref API at {self.base_url}: {e.reason}")

    # --- Authentication ---
    def login(self, email: str, password: str) -> Dict[str, Any]:
        data = self._request("POST", "/api/v1/auth/login", {"email": email, "password": password})
        cli_config.save({"token": data["token"], "user": data.get("user")})
        return data

    def get_me(self) -> Dict[str, Any]:
        return self._request("GET", "/api/v1/auth/me")

    # --- Projects ---
    def list_projects(self) -> List[Dict[str, Any]]:
        return self._request("GET", "/api/v1/projects")

    def create_project(self, name: str, slug: Optional[str] = None) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"name": name}
        if slug:
            payload["slug"] = slug
        return self._request("POST", "/api/v1/projects", payload)

    def get_project(self, id_or_slug: str) -> Dict[str, Any]:
        return self._request("GET", f"/api/v1/projects/{id_or_slug}")

    # --- Multipart Upload ---
    def upload_zip(self, project_id: str, zip_path: str) -> Dict[str, Any]:
        boundary = f"----ZirefBoundary{uuid.uuid4().hex}"
        filename = os.path.basename(zip_path)

        with open(zip_path, "rb") as f:
            file_bytes = f.read()

        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            f"Content-Type: application/zip\r\n\r\n"
        ).encode("utf-8") + file_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")

        return self._request(
            "POST",
            f"/api/v1/projects/{project_id}/uploads",
            raw_body=body,
            content_type=f"multipart/form-data; boundary={boundary}"
        )

    # --- Builds ---
    def trigger_build(self, project_id: str, upload_id: str, build_command: Optional[str] = None, output_directory: Optional[str] = None) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"upload_id": upload_id}
        if build_command:
            payload["build_command"] = build_command
        if output_directory:
            payload["output_directory"] = output_directory
        return self._request("POST", f"/api/v1/projects/{project_id}/builds", payload)

    def get_build(self, build_id: str) -> Dict[str, Any]:
        return self._request("GET", f"/api/v1/builds/{build_id}")

    def get_build_logs(self, build_id: str) -> Dict[str, Any]:
        return self._request("GET", f"/api/v1/builds/{build_id}/logs")

    # --- Environment ---
    def list_env(self, project_id: str) -> List[Dict[str, Any]]:
        return self._request("GET", f"/api/v1/projects/{project_id}/env")

    def set_env(self, project_id: str, key: str, value: str) -> Dict[str, Any]:
        return self._request("POST", f"/api/v1/projects/{project_id}/env", {"key": key, "value": value, "is_secret": True})

    # --- Appify ---
    def create_mobile_app(self, project_id: str, app_name: str, package_id: str) -> Dict[str, Any]:
        return self._request("POST", f"/api/v1/projects/{project_id}/apps", {
            "app_name": app_name,
            "package_id": package_id
        })

    def trigger_mobile_build(self, app_id: str) -> Dict[str, Any]:
        return self._request("POST", f"/api/v1/apps/{app_id}/build")

    def get_mobile_build(self, mobile_build_id: str) -> Dict[str, Any]:
        return self._request("GET", f"/api/v1/mobile-builds/{mobile_build_id}")

    def download_apk(self, mobile_build_id: str, target_file: str) -> None:
        url = f"{self.base_url}/api/v1/mobile-builds/{mobile_build_id}/download/apk"
        req = urllib.request.Request(url, headers={"User-Agent": "Ziref-CLI/1.0"})
        with urllib.request.urlopen(req, timeout=60) as resp, open(target_file, "wb") as out:
            out.write(resp.read())
