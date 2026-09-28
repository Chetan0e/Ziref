#!/usr/bin/env python3
"""
migrate_active_urls.py — Fix all existing projects with broken active_url values.

Run this script once after deploying the URL architecture fix.

What it does:
1. Finds all projects where active_url contains 'localhost:8080' (the old broken format)
2. Replaces them with the canonical path-based URL: http://localhost:8000/sites/{slug}/
3. Fixes all corresponding deployment records (url field)
4. Reports what was changed

Usage:
    python scripts/migrate_active_urls.py

    # With custom API URL:
    PUBLIC_SITE_BASE_URL=http://localhost:8000/sites python scripts/migrate_active_urls.py
"""

import asyncio
import os
import sys
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("migrate_urls")

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


async def run_migration():
    from services.api.core.database import connect_to_database, get_database
    from services.api.core.deployment_url import deployment_url_service

    await connect_to_database()
    db = get_database()

    projects_fixed = 0
    deployments_fixed = 0

    logger.info("Starting URL architecture migration...")

    # Fix projects
    cursor = db.projects.find({})
    async for project in cursor:
        slug = project.get("slug", "")
        current_url = project.get("active_url")

        if not current_url:
            continue

        # Detect broken URL patterns
        is_broken = (
            "localhost:8080" in current_url or
            (slug and current_url == f"http://{slug}.localhost:8080") or
            ".localhost:" in current_url
        )

        if not is_broken:
            continue

        canonical_url = deployment_url_service.generate_public_url(slug)
        logger.info(f"  Project '{project['name']}' ({slug}): {current_url!r} → {canonical_url!r}")

        await db.projects.update_one(
            {"_id": project["_id"]},
            {"$set": {"active_url": canonical_url}}
        )
        # Remove legacy preview_url field if present
        await db.projects.update_one(
            {"_id": project["_id"]},
            {"$unset": {"preview_url": ""}}
        )
        projects_fixed += 1

    # Fix deployment records
    dep_cursor = db.deployments.find({})
    async for dep in dep_cursor:
        current_url = dep.get("url", "")
        slug = dep.get("subdomain", "")

        is_broken = (
            "localhost:8080" in current_url or
            ".localhost:" in current_url
        )

        if not is_broken or not slug:
            continue

        canonical_url = deployment_url_service.generate_public_url(slug)
        logger.info(f"  Deployment {dep['_id']} ({slug}): {current_url!r} → {canonical_url!r}")

        update_fields = {"url": canonical_url}
        unset_fields = {}

        # Remove legacy preview_url from deployments
        if "preview_url" in dep:
            unset_fields["preview_url"] = ""

        update_op = {"$set": update_fields}
        if unset_fields:
            update_op["$unset"] = unset_fields

        await db.deployments.update_one({"_id": dep["_id"]}, update_op)
        deployments_fixed += 1

    logger.info(f"\n✅ Migration complete.")
    logger.info(f"   Projects fixed:    {projects_fixed}")
    logger.info(f"   Deployments fixed: {deployments_fixed}")

    if projects_fixed == 0 and deployments_fixed == 0:
        logger.info("   No broken URLs found — all records already use canonical URL format.")


if __name__ == "__main__":
    asyncio.run(run_migration())
