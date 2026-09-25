import json
from datetime import datetime, timezone
from bson import ObjectId
from typing import List, Dict, Any, Optional
import asyncio

import os
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import StreamingResponse, FileResponse

from services.api.core.datetime_util import utc_now_iso
from services.api.core.config import settings
from services.api.core.database import get_database
from services.api.core.security import get_current_user_token
from services.api.core.models import BuildStatus, ProjectStatus, BuildLogEvent
from services.api.core.redis_client import push_job, subscribe_events
from services.api.schemas.builds import BuildTriggerRequest, BuildResponse, BuildLogsResponse, BuildDiagnosisResponse

router = APIRouter(tags=["Builds"])

@router.post("/projects/{project_id}/builds", response_model=BuildResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_build(
    project_id: str,
    payload: BuildTriggerRequest,
    token_data: Dict[str, Any] = Depends(get_current_user_token)
):
    db = get_database()
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid project ID")

    project = await db.projects.find_one({"_id": ObjectId(project_id), "user_id": token_data["sub"]})
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    upload = await db.uploads.find_one({"_id": ObjectId(payload.upload_id), "project_id": project_id})
    if not upload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload record not found")

    now_str = utc_now_iso()
    build_command = payload.build_command if payload.build_command is not None else project.get("build_command")
    output_directory = payload.output_directory if payload.output_directory is not None else (project.get("output_directory") or ".")

    build_doc = {
        "project_id": project_id,
        "upload_id": payload.upload_id,
        "user_id": token_data["sub"],
        "status": BuildStatus.QUEUED.value,
        "framework": project.get("framework"),
        "package_manager": project.get("package_manager"),
        "build_command": build_command,
        "output_directory": output_directory,
        "exit_code": None,
        "started_at": None,
        "completed_at": None,
        "duration_seconds": None,
        "error_message": None,
        "created_at": now_str
    }

    res = await db.builds.insert_one(build_doc)
    build_id = str(res.inserted_id)

    # Update project status
    await db.projects.update_one(
        {"_id": ObjectId(project_id)},
        {"$set": {
            "status": ProjectStatus.BUILD_QUEUED.value,
            "build_command": build_command,
            "output_directory": output_directory
        }}
    )

    # Enqueue background build job to Redis
    await push_job("build", {
        "build_id": build_id,
        "project_id": project_id,
        "upload_id": payload.upload_id,
        "package_manager": project.get("package_manager"),
        "build_command": build_command,
        "output_directory": output_directory
    })

    return BuildResponse(
        id=build_id,
        project_id=project_id,
        upload_id=payload.upload_id,
        status=BuildStatus.QUEUED,
        framework=project.get("framework"),
        build_command=build_command,
        output_directory=output_directory,
        created_at=now_str
    )

@router.get("/projects/{project_id}/builds", response_model=List[BuildResponse])
async def list_project_builds(
    project_id: str,
    token_data: Dict[str, Any] = Depends(get_current_user_token)
):
    db = get_database()
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid project ID")

    project = await db.projects.find_one({"_id": ObjectId(project_id), "user_id": token_data["sub"]})
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    cursor = db.builds.find({"project_id": project_id}).sort("created_at", -1)
    results = []
    async for b in cursor:
        results.append(BuildResponse(
            id=str(b["_id"]),
            project_id=b["project_id"],
            upload_id=b["upload_id"],
            status=b["status"],
            framework=b.get("framework"),
            build_command=b.get("build_command"),
            output_directory=b.get("output_directory"),
            exit_code=b.get("exit_code"),
            started_at=b.get("started_at"),
            completed_at=b.get("completed_at"),
            duration_seconds=b.get("duration_seconds"),
            error_message=b.get("error_message"),
            diagnosis=b.get("diagnosis"),
            created_at=b.get("created_at", "")
        ))
    return results

@router.get("/builds/{build_id}", response_model=BuildResponse)
async def get_build(build_id: str, token_data: Dict[str, Any] = Depends(get_current_user_token)):
    db = get_database()
    b = None
    if ObjectId.is_valid(build_id):
        b = await db.builds.find_one({"_id": ObjectId(build_id)})
    if not b:
        b = await db.builds.find_one({"_id": build_id})
    if not b or (b.get("user_id") and b.get("user_id") != token_data["sub"]):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Build not found")

    return BuildResponse(
        id=str(b["_id"]),
        project_id=b["project_id"],
        upload_id=b["upload_id"],
        status=b["status"],
        framework=b.get("framework"),
        build_command=b.get("build_command"),
        output_directory=b.get("output_directory"),
        exit_code=b.get("exit_code"),
        started_at=b.get("started_at"),
        completed_at=b.get("completed_at"),
        duration_seconds=b.get("duration_seconds"),
        error_message=b.get("error_message"),
        diagnosis=b.get("diagnosis"),
        created_at=b.get("created_at", "")
    )

@router.get("/builds/{build_id}/diagnosis", response_model=BuildDiagnosisResponse)
async def get_build_diagnosis(build_id: str, token_data: Dict[str, Any] = Depends(get_current_user_token)):
    db = get_database()
    if not ObjectId.is_valid(build_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid build ID")

    b = await db.builds.find_one({"_id": ObjectId(build_id), "user_id": token_data["sub"]})
    if not b:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Build not found")

    diag = b.get("diagnosis")
    if not diag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No diagnosis available for this build")

    return BuildDiagnosisResponse(
        build_id=build_id,
        category=diag.get("category", "UNKNOWN"),
        summary=diag.get("summary", ""),
        root_cause=diag.get("root_cause", ""),
        confidence=diag.get("confidence", 0.0),
        actionable_fix=diag.get("actionable_fix", ""),
        detected_snippet=diag.get("detected_snippet")
    )

@router.post("/builds/{build_id}/cancel", status_code=status.HTTP_200_OK)
async def cancel_build(build_id: str, token_data: Dict[str, Any] = Depends(get_current_user_token)):
    db = get_database()
    if not ObjectId.is_valid(build_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid build ID")

    b = await db.builds.find_one({"_id": ObjectId(build_id), "user_id": token_data["sub"]})
    if not b:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Build not found")

    if b.get("status") in [BuildStatus.BUILT.value, BuildStatus.FAILED.value, BuildStatus.CANCELLED.value]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Build is already {b.get('status')}")

    now_str = utc_now_iso()
    await db.builds.update_one(
        {"_id": ObjectId(build_id)},
        {"$set": {
            "status": BuildStatus.CANCELLED.value,
            "completed_at": now_str,
            "error_message": "Build cancelled by user."
        }}
    )

    await db.projects.update_one(
        {"_id": ObjectId(b["project_id"])},
        {"$set": {"status": ProjectStatus.BUILD_FAILED.value}}
    )

    return {"message": "Build cancelled successfully", "build_id": build_id}

@router.post("/builds/{build_id}/retry", response_model=BuildResponse, status_code=status.HTTP_202_ACCEPTED)
async def retry_build(build_id: str, token_data: Dict[str, Any] = Depends(get_current_user_token)):
    db = get_database()
    if not ObjectId.is_valid(build_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid build ID")

    b = await db.builds.find_one({"_id": ObjectId(build_id), "user_id": token_data["sub"]})
    if not b:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Build not found")

    project = await db.projects.find_one({"_id": ObjectId(b["project_id"])})
    now_str = utc_now_iso()

    new_build_doc = {
        "project_id": b["project_id"],
        "upload_id": b["upload_id"],
        "user_id": token_data["sub"],
        "status": BuildStatus.QUEUED.value,
        "framework": b.get("framework"),
        "package_manager": b.get("package_manager"),
        "build_command": b.get("build_command"),
        "output_directory": b.get("output_directory"),
        "exit_code": None,
        "started_at": None,
        "completed_at": None,
        "duration_seconds": None,
        "error_message": None,
        "created_at": now_str
    }
    res = await db.builds.insert_one(new_build_doc)
    new_build_id = str(res.inserted_id)

    await db.projects.update_one(
        {"_id": ObjectId(b["project_id"])},
        {"$set": {"status": ProjectStatus.BUILD_QUEUED.value}}
    )

    await push_job("build", {
        "build_id": new_build_id,
        "project_id": b["project_id"],
        "upload_id": b["upload_id"],
        "package_manager": b.get("package_manager"),
        "build_command": b.get("build_command"),
        "output_directory": b.get("output_directory")
    })

    return BuildResponse(
        id=new_build_id,
        project_id=b["project_id"],
        upload_id=b["upload_id"],
        status=BuildStatus.QUEUED,
        framework=b.get("framework"),
        build_command=b.get("build_command"),
        output_directory=b.get("output_directory"),
        created_at=now_str
    )

@router.get("/builds/{build_id}/artifact")
async def download_build_artifact(build_id: str, token_data: Dict[str, Any] = Depends(get_current_user_token)):
    db = get_database()
    if not ObjectId.is_valid(build_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid build ID")

    b = await db.builds.find_one({"_id": ObjectId(build_id), "user_id": token_data["sub"]})
    if not b:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Build not found")

    artifact_rel = b.get("artifact_path")
    if not artifact_rel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not available for this build")

    artifact_abs = os.path.join(settings.STORAGE_PATH, artifact_rel)
    if not os.path.exists(artifact_abs):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact file missing on server")

    return FileResponse(
        artifact_abs,
        media_type="application/gzip",
        filename=f"artifact-{build_id}.tar.gz"
    )

@router.get("/builds/{build_id}/logs", response_model=BuildLogsResponse)
async def get_build_logs(build_id: str, token_data: Dict[str, Any] = Depends(get_current_user_token)):
    db = get_database()
    if not ObjectId.is_valid(build_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid build ID")

    b = await db.builds.find_one({"_id": ObjectId(build_id), "user_id": token_data["sub"]})
    if not b:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Build not found")

    cursor = db.build_events.find({"build_id": build_id}).sort("timestamp", 1)
    events = []
    async for evt in cursor:
        events.append(BuildLogEvent(
            timestamp=evt["timestamp"],
            stage=evt["stage"],
            level=evt["level"],
            message=evt["message"]
        ))

    return BuildLogsResponse(build_id=build_id, events=events)

@router.get("/builds/{build_id}/logs/stream")
async def stream_build_logs(build_id: str):
    """Server-Sent Events (SSE) live log stream."""
    async def event_generator():
        # First yield existing logs from database
        db = get_database()
        cursor = db.build_events.find({"build_id": build_id}).sort("timestamp", 1)
        async for evt in cursor:
            data = json.dumps({
                "timestamp": evt["timestamp"],
                "stage": evt["stage"],
                "level": evt["level"],
                "message": evt["message"]
            })
            yield f"data: {data}\n\n"

        # Check if build is already finished
        build = await db.builds.find_one({"_id": ObjectId(build_id)})
        if build and build.get("status") in [BuildStatus.BUILT.value, BuildStatus.FAILED.value, BuildStatus.CANCELLED.value]:
            yield f"data: {json.dumps({'stage': 'done', 'level': 'info', 'message': '[STREAM_CLOSED]'})}\n\n"
            return

        # Otherwise subscribe to Redis live channel
        try:
            async for live_evt in subscribe_events(f"build:{build_id}:logs"):
                yield f"data: {json.dumps(live_evt)}\n\n"
                if live_evt.get("stage") in [BuildStatus.BUILT.value, "done", "completed"] or "Build failed" in live_evt.get("message", ""):
                    break
        except asyncio.CancelledError:
            pass

    return StreamingResponse(event_generator(), media_type="text/event-stream")
