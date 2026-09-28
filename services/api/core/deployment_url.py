"""
DeploymentUrlService — Single source of truth for all deployment URL generation.

Rules:
  - Development: http://localhost:8000/sites/{slug}/
  - Production:  https://ziref.app/sites/{slug}/  OR  https://{slug}.ziref.app/
  - The frontend NEVER invents URLs. The API always returns a resolved, stored URL.
  - localhost / 127.0.0.1 must never appear in a production APK.
"""

import re
import urllib.request
import logging
from typing import Optional
from services.api.core.config import settings

logger = logging.getLogger("ziref.deployment_url")


class DeploymentUrlService:
    def generate_public_url(self, slug: str) -> str:
        """
        Generate the canonical public URL for a deployment.

        Uses PUBLIC_SITE_BASE_URL from config so that:
          - Development: http://localhost:8000/sites/{slug}/
          - Production:  https://ziref.app/sites/{slug}/
        """
        base = settings.PUBLIC_SITE_BASE_URL.rstrip("/")
        return f"{base}/{slug}/"

    def resolve_deployment_url(self, slug: str, deployment_id: str) -> str:
        """
        Returns the canonical URL for a specific deployment (same as project URL in current model).
        In an immutable-deployment model this could include the deployment_id path.
        """
        return self.generate_public_url(slug)

    def resolve_project_url(self, slug: str) -> str:
        """Returns the live production URL for a project (points to current deployment)."""
        return self.generate_public_url(slug)

    def validate_public_url(self, url: str) -> tuple[bool, str]:
        """
        Validates that a URL is suitable for use as a deployment or APK target URL.
        Returns (is_valid, reason).
        """
        if not url:
            return False, "URL is empty"

        lower = url.lower()

        # Reject localhost variants
        localhost_patterns = [
            "localhost",
            "127.0.0.1",
            "0.0.0.0",
            "::1",
        ]
        for pat in localhost_patterns:
            if pat in lower:
                return False, f"URL contains local address '{pat}' — not reachable from an Android device or public internet"

        # Must start with http:// or https://
        if not (lower.startswith("http://") or lower.startswith("https://")):
            return False, "URL must use http:// or https://"

        return True, "ok"

    def is_localhost_url(self, url: str) -> bool:
        """Returns True if the URL targets a local/non-public address."""
        valid, _ = self.validate_public_url(url)
        return not valid

    def check_url_reachable(self, url: str, timeout: int = 5) -> tuple[bool, int]:
        """
        Attempts an HTTP HEAD request to verify the URL is reachable.
        Returns (is_reachable, http_status_code).
        """
        try:
            req = urllib.request.Request(url, method="HEAD")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return True, resp.status
        except Exception as e:
            logger.debug(f"URL reachability check failed for {url}: {e}")
            return False, 0

    def sanitize_package_id(self, package_id: str) -> tuple[bool, str]:
        """
        Validates an Android package identifier.
        Valid: com.example.myapp  (lowercase segments, no spaces, at least 2 segments)
        Returns (is_valid, reason).
        """
        if not package_id:
            return False, "Package ID is empty"
        # Must have at least 2 segments separated by dots
        segments = package_id.split(".")
        if len(segments) < 2:
            return False, "Package ID must have at least two segments (e.g. com.myapp)"
        # Each segment must be a valid Java identifier
        id_pattern = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')
        for seg in segments:
            if not seg:
                return False, f"Package ID has empty segment: '{package_id}'"
            if not id_pattern.match(seg):
                return False, f"Segment '{seg}' contains invalid characters (use only letters, digits, underscores)"
        # Warn about uppercase (not invalid but unconventional)
        if package_id != package_id.lower():
            logger.warning(f"Package ID '{package_id}' uses uppercase — Android convention is all-lowercase")
        return True, "ok"

    def sanitize_app_name(self, app_name: str) -> tuple[bool, str]:
        """
        Validates an Android app name.
        """
        if not app_name or not app_name.strip():
            return False, "App name is empty"
        if len(app_name.strip()) > 50:
            return False, "App name must be 50 characters or fewer"
        # Check for characters that break XML/filesystem
        forbidden = ['<', '>', '"', '&', '\0', '\n', '\r']
        for ch in forbidden:
            if ch in app_name:
                return False, f"App name contains forbidden character: {repr(ch)}"
        return True, "ok"

    def apk_filename(self, slug: str, version_name: str, version_code: int) -> str:
        """Returns a standardized APK filename: {slug}-{versionName}-{versionCode}.apk"""
        safe_slug = re.sub(r'[^a-z0-9\-]', '-', slug.lower()).strip('-')
        safe_version = re.sub(r'[^0-9a-zA-Z.\-]', '', version_name)
        return f"{safe_slug}-{safe_version}-{version_code}.apk"


deployment_url_service = DeploymentUrlService()
