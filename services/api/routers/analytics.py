from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from bson import ObjectId

from services.api.core.database import get_database
from services.api.core.security import get_current_user_token

router = APIRouter(tags=["Analytics"])

class PathStat(BaseModel):
    path: str
    count: int
    avg_latency_ms: float

class StatusBreakdown(BaseModel):
    status_2xx: int
    status_3xx: int
    status_4xx: int
    status_5xx: int

class DeviceBreakdown(BaseModel):
    desktop: int
    mobile: int
    bot_or_other: int

class TrafficBucket(BaseModel):
    time: str
    requests: int

class AnalyticsSummary(BaseModel):
    project_id: str
    total_requests: int
    unique_visitors: int
    avg_latency_ms: float
    p95_latency_ms: float
    status_codes: StatusBreakdown
    device_breakdown: DeviceBreakdown
    top_paths: List[PathStat]
    traffic_series: List[TrafficBucket]

@router.get("/projects/{project_id}/analytics", response_model=AnalyticsSummary)
async def get_project_analytics(project_id: str, token_data: Dict[str, Any] = Depends(get_current_user_token)):
    db = get_database()
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid project ID")

    project = await db.projects.find_one({"_id": ObjectId(project_id), "user_id": token_data["sub"]})
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    cursor = db.runtime_logs.find({"project_id": project_id}).sort("timestamp", -1).limit(1000)
    logs: List[Dict[str, Any]] = []
    async for entry in cursor:
        logs.append(entry)

    if not logs:
        return AnalyticsSummary(
            project_id=project_id,
            total_requests=0,
            unique_visitors=0,
            avg_latency_ms=0.0,
            p95_latency_ms=0.0,
            status_codes=StatusBreakdown(status_2xx=0, status_3xx=0, status_4xx=0, status_5xx=0),
            device_breakdown=DeviceBreakdown(desktop=0, mobile=0, bot_or_other=0),
            top_paths=[],
            traffic_series=[]
        )

    total_requests = len(logs)
    unique_ips = len(set(log.get("client_ip", "") for log in logs if log.get("client_ip")))

    s2 = sum(1 for log in logs if 200 <= log.get("status_code", 0) < 300)
    s3 = sum(1 for log in logs if 300 <= log.get("status_code", 0) < 400)
    s4 = sum(1 for log in logs if 400 <= log.get("status_code", 0) < 500)
    s5 = sum(1 for log in logs if 500 <= log.get("status_code", 0) < 600)

    latencies = sorted([float(log.get("duration_ms", 0.0)) for log in logs])
    avg_latency = round(sum(latencies) / len(latencies), 2) if latencies else 0.0
    p95_idx = int(len(latencies) * 0.95)
    p95_latency = round(latencies[p95_idx], 2) if latencies else 0.0

    # Device breakdown
    desktop = 0
    mobile = 0
    bot = 0
    for log in logs:
        ua = log.get("user_agent", "").lower()
        if "mobile" in ua or "android" in ua or "iphone" in ua:
            mobile += 1
        elif "bot" in ua or "spider" in ua or "curl" in ua or "python" in ua:
            bot += 1
        else:
            desktop += 1

    # Top paths
    path_counts: Dict[str, List[float]] = {}
    for log in logs:
        p = log.get("path", "/")
        path_counts.setdefault(p, []).append(float(log.get("duration_ms", 0.0)))

    top_paths = []
    for p, l_list in sorted(path_counts.items(), key=lambda item: len(item[1]), reverse=True)[:5]:
        top_paths.append(PathStat(
            path=p,
            count=len(l_list),
            avg_latency_ms=round(sum(l_list) / len(l_list), 2)
        ))

    # Traffic timeseries (minute / hourly buckets)
    bucket_counts: Dict[str, int] = {}
    for log in logs:
        ts = log.get("timestamp", "")
        # Use HH:MM format
        if len(ts) >= 16:
            bucket_key = ts[11:16]
            bucket_counts[bucket_key] = bucket_counts.get(bucket_key, 0) + 1

    traffic_series = [
        TrafficBucket(time=k, requests=v)
        for k, v in sorted(bucket_counts.items())[-12:]
    ]

    return AnalyticsSummary(
        project_id=project_id,
        total_requests=total_requests,
        unique_visitors=unique_ips,
        avg_latency_ms=avg_latency,
        p95_latency_ms=p95_latency,
        status_codes=StatusBreakdown(status_2xx=s2, status_3xx=s3, status_4xx=s4, status_5xx=s5),
        device_breakdown=DeviceBreakdown(desktop=desktop, mobile=mobile, bot_or_other=bot),
        top_paths=top_paths,
        traffic_series=traffic_series
    )
