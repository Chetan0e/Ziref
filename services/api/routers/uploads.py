import os
import shutil
import hashlib
from datetime import datetime, timezone
from bson import ObjectId
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, status, UploadFile, File, Depends
from services.api.core.datetime_util import utc_now_iso
from services.api.core.config import settings
from services.api.core.database import get_database
from services.api.core.security import get_current_user_token
from services.api.core.models import ProjectStatus
from services.api.schemas.projects import UploadResponse
from services.analyzer.archive_validator import archive_validator, ArchiveSecurityError
from services.analyzer.detector import project_detector

router = APIRouter(tags=["Uploads & Analysis"])

@router.post("/projects/{project_id}/uploads", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_project_archive(
    project_id: str,
    file: UploadFile = File(...),
    token_data: Dict[str, Any] = Depends(get_current_user_token)
):
    db = get_database()
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid project ID")

    project = await db.projects.find_one({"_id": ObjectId(project_id), "user_id": token_data["sub"]})
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    filename = file.filename or "project.zip"
    if not filename.lower().endswith(".zip"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only standard .zip archives are accepted."
        )

    # Read and validate content size
    content = await file.read()
    file_size = len(content)
    if file_size > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Uploaded archive exceeds limit of {settings.MAX_UPLOAD_SIZE_BYTES // (1024*1024)} MB."
        )

    checksum = hashlib.sha256(content).hexdigest()

    # Generate upload ID and save to storage
    upload_id = str(ObjectId())
    storage_rel_path = os.path.join("uploads", f"{upload_id}_{filename}")
    storage_abs_path = os.path.join(settings.STORAGE_PATH, storage_rel_path)
    os.makedirs(os.path.dirname(storage_abs_path), exist_ok=True)

    with open(storage_abs_path, "wb") as f:
        f.write(content)

    # Validate and perform automated project analysis
    analysis_dir = os.path.join(settings.STORAGE_PATH, "workspaces", f"analysis_{upload_id}")
    try:
        success, msg, files = archive_validator.validate_and_extract(storage_abs_path, analysis_dir)
        analysis = project_detector.analyze(analysis_dir)

        now_str = utc_now_iso()

        # Update Project record with detected framework info
        await db.projects.update_one(
            {"_id": ObjectId(project_id)},
            {"$set": {
                "framework": analysis.framework,
                "language": analysis.language,
                "package_manager": analysis.packageManager,
                "runtime": analysis.runtime,
                "build_command": analysis.buildCommand,
                "start_command": analysis.startCommand,
                "output_directory": analysis.outputDirectory,
                "status": ProjectStatus.ANALYZED.value,
                "updated_at": now_str
            }}
        )

        # Store upload document
        upload_doc = {
            "_id": ObjectId(upload_id),
            "project_id": project_id,
            "user_id": token_data["sub"],
            "filename": filename,
            "file_size": file_size,
            "checksum": checksum,
            "storage_path": storage_rel_path,
            "analysis": analysis.model_dump(),
            "created_at": now_str
        }
        await db.uploads.insert_one(upload_doc)

        return UploadResponse(
            id=upload_id,
            project_id=project_id,
            filename=filename,
            file_size=file_size,
            checksum=checksum,
            analysis=analysis,
            created_at=now_str
        )

    except ArchiveSecurityError as ase:
        # Clean up dangerous file
        if os.path.exists(storage_abs_path):
            os.remove(storage_abs_path)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ase))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Analysis failed: {str(e)}")
    finally:
        if os.path.exists(analysis_dir):
            shutil.rmtree(analysis_dir, ignore_errors=True)
