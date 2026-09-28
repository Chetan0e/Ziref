#!/usr/bin/env python3
"""
deduplicate_deployments.py — Remove duplicate deployment records.

For each project, keeps only:
1. The deployment the project currently points to (active_deployment_id)
2. The most recent deployment per unique build_id

Extra deployment records created by the old missing idempotency guard are removed.

Usage:
    python scripts/deduplicate_deployments.py
    DRY_RUN=true python scripts/deduplicate_deployments.py
"""

import asyncio
import os
import sys
import logging
from collections import defaultdict

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("dedup_deployments")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

DRY_RUN = os.environ.get("DRY_RUN", "false").lower() == "true"


async def run_deduplication():
    from bson import ObjectId
    from services.api.core.database import connect_to_database, get_database

    await connect_to_database()
    db = get_database()

    logger.info(f"Starting deployment deduplication (dry_run={DRY_RUN})...")

    # Load all deployments
    all_deployments = []
    async for dep in db.deployments.find({}):
        all_deployments.append(dep)

    # Group by project_id
    by_project = defaultdict(list)
    for dep in all_deployments:
        by_project[dep.get("project_id", "__none__")].append(dep)

    # Sort each group by created_at descending (most recent first)
    for pid in by_project:
        by_project[pid].sort(key=lambda d: d.get("created_at", ""), reverse=True)

    total_deleted = 0
    projects_affected = 0

    for project_id, deps in by_project.items():
        if len(deps) <= 1:
            continue

        # Get the project's active deployment
        active_dep_id = None
        project_name = project_id
        slug = "?"
        try:
            if project_id and ObjectId.is_valid(project_id):
                project = await db.projects.find_one({"_id": ObjectId(project_id)})
            else:
                project = await db.projects.find_one({"_id": project_id})
            if project:
                active_dep_id = project.get("active_deployment_id")
                project_name = project.get("name", project_id)
                slug = project.get("slug", "?")
        except Exception:
            pass

        # Determine which to keep
        keep_ids = set()
        if active_dep_id:
            keep_ids.add(str(active_dep_id))

        # Keep first (most recent) deployment per unique build_id
        seen_build_ids = set()
        for dep in deps:
            dep_id = str(dep["_id"])
            build_id = dep.get("build_id")
            dep_status = dep.get("status", "")
            if dep_status == "READY":
                keep_ids.add(dep_id)
            if build_id not in seen_build_ids:
                keep_ids.add(dep_id)
                seen_build_ids.add(build_id)

        to_delete = [dep for dep in deps if str(dep["_id"]) not in keep_ids]

        if not to_delete:
            continue

        projects_affected += 1
        logger.info(
            f"  Project '{project_name}' ({slug}): {len(deps)} deployments → "
            f"keeping {len(deps) - len(to_delete)}, deleting {len(to_delete)}"
        )

        for dep in to_delete:
            dep_id = dep["_id"]
            logger.info(
                f"    {'[DRY RUN] ' if DRY_RUN else ''}Delete deployment {dep_id} "
                f"(status={dep.get('status')}, build={str(dep.get('build_id','?'))[:12]}...)"
            )
            if not DRY_RUN:
                await db.deployments.delete_one({"_id": dep_id})
                total_deleted += 1
            else:
                total_deleted += 1

    prefix = "[DRY RUN] Would delete" if DRY_RUN else "Deleted"
    logger.info(f"\n✅ Deduplication complete.")
    logger.info(f"   Projects affected: {projects_affected}")
    logger.info(f"   {prefix}: {total_deleted} duplicate deployment records.")

    if total_deleted == 0:
        logger.info("   No duplicates found.")


if __name__ == "__main__":
    asyncio.run(run_deduplication())
