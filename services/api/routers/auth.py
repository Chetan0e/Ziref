from fastapi import APIRouter, HTTPException, status, Depends
from datetime import datetime, timezone
from bson import ObjectId
from typing import Dict, Any

from services.api.core.database import get_database
from services.api.core.security import hash_password, verify_password, create_access_token, get_current_user_token
from services.api.schemas.auth import UserRegister, UserLogin, TokenResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: UserRegister):
    db = get_database()
    existing = await db.users.find_one({"email": payload.email.lower()})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists."
        )

    now_str = datetime.now(timezone.utc).isoformat() + "Z"
    user_doc = {
        "email": payload.email.lower(),
        "password_hash": hash_password(payload.password),
        "name": payload.name.strip(),
        "created_at": now_str,
        "updated_at": now_str
    }

    result = await db.users.insert_one(user_doc)
    user_id = str(result.inserted_id)

    token = create_access_token({"sub": user_id, "email": user_doc["email"]})

    return TokenResponse(
        token=token,
        user=UserResponse(
            id=user_id,
            email=user_doc["email"],
            name=user_doc["name"],
            created_at=user_doc["created_at"]
        )
    )

@router.post("/login", response_model=TokenResponse)
async def login(payload: UserLogin):
    db = get_database()
    user = await db.users.find_one({"email": payload.email.lower()})
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    user_id = str(user["_id"])
    token = create_access_token({"sub": user_id, "email": user["email"]})

    return TokenResponse(
        token=token,
        user=UserResponse(
            id=user_id,
            email=user["email"],
            name=user["name"],
            created_at=user.get("created_at", "")
        )
    )

@router.get("/me", response_model=UserResponse)
async def get_current_user(token_data: Dict[str, Any] = Depends(get_current_user_token)):
    db = get_database()
    user = await db.users.find_one({"_id": ObjectId(token_data["sub"])})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return UserResponse(
        id=str(user["_id"]),
        email=user["email"],
        name=user["name"],
        created_at=user.get("created_at", "")
    )

@router.post("/logout")
async def logout():
    return {"message": "Logged out successfully"}
