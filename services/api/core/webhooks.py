import hmac
import hashlib
import json
import logging
import asyncio
import urllib.request
from datetime import datetime, timezone
from typing import Dict, Any, List
from bson import ObjectId

from services.api.core.database import get_database

logger = logging.getLogger("ziref.webhooks")

class WebhookDispatcher:
    """
    Dispatches outbound webhook events to external systems (Slack, Discord, custom endpoints)
    with HMAC-SHA256 signature verification.
    """

    async def dispatch_event(self, project_id: str, event_type: str, data: Dict[str, Any]) -> None:
        try:
            db = get_database()
            cursor = db.webhooks.find({"project_id": project_id, "is_active": True})
            webhooks: List[Dict[str, Any]] = []
            async for wh in cursor:
                webhooks.append(wh)

            if not webhooks:
                return

            payload = {
                "event": event_type,
                "project_id": project_id,
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                "data": data
            }
            payload_bytes = json.dumps(payload, default=str).encode("utf-8")

            # Fire webhook deliveries concurrently
            tasks = [self._deliver(wh, payload_bytes) for wh in webhooks]
            await asyncio.gather(*tasks, return_exceptions=True)

        except Exception as e:
            logger.warning(f"Error dispatching webhooks for project {project_id}: {e}")

    async def _deliver(self, webhook: Dict[str, Any], payload_bytes: bytes) -> bool:
        url = webhook["url"]
        secret = webhook.get("secret", "")
        signature = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Ziref-Webhook/1.0",
            "X-Ziref-Signature": signature
        }

        def _send():
            req = urllib.request.Request(url, data=payload_bytes, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status

        try:
            status_code = await asyncio.to_thread(_send)
            logger.info(f"Delivered webhook to {url} [status {status_code}]")
            return status_code in (200, 201, 202, 204)
        except Exception as e:
            logger.warning(f"Failed to deliver webhook to {url}: {e}")
            return False

webhook_dispatcher = WebhookDispatcher()
