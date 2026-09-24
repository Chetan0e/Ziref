import os
import shutil
import hashlib
from abc import ABC, abstractmethod
from typing import BinaryIO, Optional
import aiofiles
from services.api.core.config import settings

class StorageProvider(ABC):
    @abstractmethod
    async def save_file(self, content: bytes, relative_path: str) -> str:
        pass

    @abstractmethod
    async def get_file_bytes(self, relative_path: str) -> Optional[bytes]:
        pass

    @abstractmethod
    def get_absolute_path(self, relative_path: str) -> str:
        pass

    @abstractmethod
    async def delete_file(self, relative_path: str) -> bool:
        pass

    @abstractmethod
    async def file_exists(self, relative_path: str) -> bool:
        pass

class LocalStorageDriver(StorageProvider):
    def __init__(self, base_path: str):
        self.base_path = os.path.abspath(base_path)
        os.makedirs(self.base_path, exist_ok=True)

    def _resolve(self, relative_path: str) -> str:
        # Sanitize path to prevent directory traversal
        clean_rel = os.path.normpath(relative_path).lstrip("/\\")
        abs_path = os.path.abspath(os.path.join(self.base_path, clean_rel))
        if not abs_path.startswith(self.base_path):
            raise ValueError(f"Path traversal detected: {relative_path}")
        return abs_path

    async def save_file(self, content: bytes, relative_path: str) -> str:
        target_path = self._resolve(relative_path)
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        async with aiofiles.open(target_path, "wb") as f:
            await f.write(content)
        return relative_path

    async def get_file_bytes(self, relative_path: str) -> Optional[bytes]:
        target_path = self._resolve(relative_path)
        if not os.path.exists(target_path):
            return None
        async with aiofiles.open(target_path, "rb") as f:
            return await f.read()

    def get_absolute_path(self, relative_path: str) -> str:
        return self._resolve(relative_path)

    async def delete_file(self, relative_path: str) -> bool:
        target_path = self._resolve(relative_path)
        if os.path.exists(target_path):
            if os.path.isdir(target_path):
                shutil.rmtree(target_path)
            else:
                os.remove(target_path)
            return True
        return False

    async def file_exists(self, relative_path: str) -> bool:
        target_path = self._resolve(relative_path)
        return os.path.exists(target_path)

def calculate_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

# Default singleton instance
storage = LocalStorageDriver(settings.STORAGE_PATH)
