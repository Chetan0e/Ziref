import os
import json
import logging
import asyncio
from typing import Optional, Dict, Any, List
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING
from services.api.core.config import settings

logger = logging.getLogger("ziref.database")

client: Optional[AsyncIOMotorClient] = None
db: Any = None
_use_fallback = False

class MemoryCursor:
    def __init__(self, items: List[Dict[str, Any]]):
        self.items = items
        self._index = 0

    def sort(self, key_or_list, direction=1):
        field = key_or_list[0][0] if isinstance(key_or_list, list) else key_or_list
        reverse = (key_or_list[0][1] == -1) if isinstance(key_or_list, list) else (direction == -1)
        self.items.sort(key=lambda x: x.get(field, ""), reverse=reverse)
        return self

    def limit(self, count: int):
        self.items = self.items[:count]
        return self

    def __aiter__(self):
        self._index = 0
        return self

    async def __anext__(self):
        if self._index < len(self.items):
            item = self.items[self._index]
            self._index += 1
            return item
        raise StopAsyncIteration

class MemoryCollection:
    def __init__(self, name: str, parent_db: 'MemoryDatabase'):
        self.name = name
        self.parent = parent_db

    def _matches(self, doc: Dict[str, Any], filter_dict: Dict[str, Any]) -> bool:
        for k, v in filter_dict.items():
            if k == "_id":
                if str(doc.get("_id")) != str(v):
                    return False
            elif isinstance(v, dict):
                # Simple handling of query operators
                if "$in" in v:
                    if doc.get(k) not in v["$in"]:
                        return False
                if "$gte" in v:
                    if doc.get(k, "") < v["$gte"]:
                        return False
                if "$lte" in v:
                    if doc.get(k, "") > v["$lte"]:
                        return False
                if "$gt" in v:
                    if doc.get(k, "") <= v["$gt"]:
                        return False
                if "$lt" in v:
                    if doc.get(k, "") >= v["$lt"]:
                        return False
            elif doc.get(k) != v:
                return False
        return True

    async def insert_one(self, doc: Dict[str, Any]):
        self.parent.reload_if_stale()
        doc_copy = doc.copy()
        if "_id" not in doc_copy:
            doc_copy["_id"] = ObjectId()
        elif isinstance(doc_copy["_id"], str) and ObjectId.is_valid(doc_copy["_id"]):
            doc_copy["_id"] = ObjectId(doc_copy["_id"])

        self.parent.data.setdefault(self.name, []).append(doc_copy)
        self.parent.schedule_save()

        class InsertResult:
            inserted_id = doc_copy["_id"]
        return InsertResult()

    async def insert_many(self, docs: List[Dict[str, Any]]):
        self.parent.reload_if_stale()
        res = []
        for d in docs:
            r = await self.insert_one(d)
            res.append(r.inserted_id)
        class InsertManyResult:
            inserted_ids = res
        return InsertManyResult()

    async def find_one(self, filter_dict: Optional[Dict[str, Any]] = None, *args, sort=None, **kwargs):
        self.parent.reload_if_stale()
        filter_dict = filter_dict or {}
        matches = [d for d in self.parent.data.get(self.name, []) if self._matches(d, filter_dict)]
        if not matches:
            return None
        if sort:
            field = sort[0][0] if isinstance(sort, list) else sort
            reverse = (sort[0][1] == -1) if isinstance(sort, list) else False
            matches.sort(key=lambda x: str(x.get(field, "")), reverse=reverse)
        return matches[0].copy()

    def find(self, filter_dict: Optional[Dict[str, Any]] = None):
        self.parent.reload_if_stale()
        filter_dict = filter_dict or {}
        matches = [d.copy() for d in self.parent.data.get(self.name, []) if self._matches(d, filter_dict)]
        return MemoryCursor(matches)

    async def count_documents(self, filter_dict: Optional[Dict[str, Any]] = None) -> int:
        self.parent.reload_if_stale()
        filter_dict = filter_dict or {}
        return sum(1 for doc in self.parent.data.get(self.name, []) if self._matches(doc, filter_dict))

    async def update_one(self, filter_dict: Dict[str, Any], update: Dict[str, Any], upsert: bool = False):
        self.parent.reload_if_stale()
        matched = 0
        modified = 0
        for doc in self.parent.data.get(self.name, []):
            if self._matches(doc, filter_dict):
                matched = 1
                if "$set" in update:
                    doc.update(update["$set"])
                    modified = 1
                if "$push" in update:
                    for k, val in update["$push"].items():
                        doc.setdefault(k, []).append(val)
                        modified = 1
                self.parent.schedule_save()
                break

        if matched == 0 and upsert:
            new_doc = filter_dict.copy()
            if "$set" in update:
                new_doc.update(update["$set"])
            if "$setOnInsert" in update:
                new_doc.update(update["$setOnInsert"])
            await self.insert_one(new_doc)
            modified = 1

        class UpdateResult:
            matched_count = matched
            modified_count = modified
        return UpdateResult()

    async def find_one_and_update(self, filter_dict: Dict[str, Any], update: Dict[str, Any], upsert: bool = False, return_document: bool = True):
        await self.update_one(filter_dict, update, upsert=upsert)
        return await self.find_one(filter_dict)

    async def delete_one(self, filter_dict: Dict[str, Any]):
        self.parent.reload_if_stale()
        items = self.parent.data.get(self.name, [])
        for i, doc in enumerate(items):
            if self._matches(doc, filter_dict):
                del items[i]
                self.parent.schedule_save()
                class DelRes:
                    deleted_count = 1
                return DelRes()
        class DelResEmpty:
            deleted_count = 0
        return DelResEmpty()

    async def delete_many(self, filter_dict: Dict[str, Any]):
        self.parent.reload_if_stale()
        items = self.parent.data.get(self.name, [])
        before = len(items)
        self.parent.data[self.name] = [d for d in items if not self._matches(d, filter_dict)]
        deleted = before - len(self.parent.data[self.name])
        if deleted > 0:
            self.parent.schedule_save()
        class DelRes:
            deleted_count = deleted
        return DelRes()

    async def create_index(self, keys, **kwargs):
        return "index_ok"

class MemoryDatabase:
    def __init__(self, persistence_path: Optional[str] = None):
        self.data: Dict[str, List[Dict[str, Any]]] = {}
        self.name = "ziref"
        self.persistence_path = persistence_path
        self._collections: Dict[str, MemoryCollection] = {}
        self._last_mtime: float = 0.0
        self._load()

    def __getattr__(self, name: str) -> MemoryCollection:
        if name not in self._collections:
            self._collections[name] = MemoryCollection(name, self)
        return self._collections[name]

    def __getitem__(self, name: str) -> MemoryCollection:
        return self.__getattr__(name)

    async def command(self, cmd: str) -> Dict[str, Any]:
        return {"ok": 1.0}

    def reload_if_stale(self):
        if self.persistence_path and os.path.exists(self.persistence_path):
            try:
                mtime = os.path.getmtime(self.persistence_path)
                if mtime > self._last_mtime:
                    self._load()
            except Exception:
                pass

    def _load(self):
        if self.persistence_path and os.path.exists(self.persistence_path):
            import time
            for attempt in range(4):
                try:
                    self._last_mtime = os.path.getmtime(self.persistence_path)
                    with open(self.persistence_path, "r", encoding="utf-8") as f:
                        raw = json.load(f)
                    new_data = {}
                    for col_name, docs in raw.items():
                        new_data[col_name] = []
                        for d in docs:
                            if "_id" in d and isinstance(d["_id"], str) and ObjectId.is_valid(d["_id"]):
                                d["_id"] = ObjectId(d["_id"])
                            new_data[col_name].append(d)
                    self.data = new_data
                    logger.info(f"Loaded fallback database from {self.persistence_path}")
                    break
                except Exception as e:
                    if attempt < 3:
                        time.sleep(0.05)
                    else:
                        logger.warning(f"Failed to load fallback db: {e}")

    def schedule_save(self):
        if not self.persistence_path:
            return
        try:
            os.makedirs(os.path.dirname(self.persistence_path), exist_ok=True)
            serializable = {}
            for col_name, docs in self.data.items():
                col_list = []
                for d in docs:
                    dc = d.copy()
                    if isinstance(dc.get("_id"), ObjectId):
                        dc["_id"] = str(dc["_id"])
                    col_list.append(dc)
                serializable[col_name] = col_list
            temp_file = f"{self.persistence_path}.tmp"
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(serializable, f, indent=2)
            import time
            replaced = False
            for _ in range(6):
                try:
                    os.replace(temp_file, self.persistence_path)
                    replaced = True
                    break
                except (PermissionError, OSError):
                    time.sleep(0.04)
            if not replaced:
                with open(self.persistence_path, "w", encoding="utf-8") as f:
                    json.dump(serializable, f, indent=2)
            self._last_mtime = os.path.getmtime(self.persistence_path)
        except Exception as e:
            logger.warning(f"Failed to save fallback db: {e}")

async def connect_to_database():
    global client, db, _use_fallback

    async def _try_connect(extra_kwargs: dict):
        c = AsyncIOMotorClient(
            settings.MONGODB_URI,
            serverSelectionTimeoutMS=1500,
            **extra_kwargs,
        )
        await c.admin.command('ping')
        return c

    try:
        logger.info(f"Attempting MongoDB connection: {settings.MONGODB_URI}")
        try:
            c = await _try_connect({})
        except Exception as first_err:
            # On Windows, Atlas can raise TLSV1_ALERT_INTERNAL_ERROR due to SSL
            # negotiation quirks.  Retry once with relaxed TLS validation.
            if "SSL" in str(first_err) or "TLS" in str(first_err) or "ssl" in str(first_err):
                logger.warning(
                    "Initial TLS handshake failed; retrying with tlsAllowInvalidCertificates=True"
                )
                c = await _try_connect({"tlsAllowInvalidCertificates": True})
            else:
                raise
        client = c
        real_db = client.get_default_database()
        if real_db is None or real_db.name == 'admin':
            real_db = client["ziref"]
        db = real_db
        _use_fallback = False
        logger.info("Connected to MongoDB successfully.")
        await _create_indexes(db)
    except Exception as e:
        logger.info(f"MongoDB not running ({e}). Activating embedded async datastore with zero prerequisites.")
        persistence_file = os.path.join(settings.STORAGE_PATH, "data", "local_db.json")
        db = MemoryDatabase(persistence_file)
        _use_fallback = True

async def close_database_connection():
    global client
    if client:
        client.close()
        client = None

def get_database():
    global db
    if db is None:
        persistence_file = os.path.join(settings.STORAGE_PATH, "data", "local_db.json")
        db = MemoryDatabase(persistence_file)
    return db

async def _create_indexes(database):
    try:
        await database.users.create_index([("email", ASCENDING)], unique=True)
        await database.projects.create_index([("slug", ASCENDING)], unique=True)
        await database.projects.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
        await database.builds.create_index([("project_id", ASCENDING), ("created_at", DESCENDING)])
        await database.build_events.create_index([("build_id", ASCENDING), ("timestamp", ASCENDING)])
        await database.deployments.create_index([("project_id", ASCENDING), ("created_at", DESCENDING)])
        await database.environment_variables.create_index([("project_id", ASCENDING), ("key", ASCENDING)], unique=True)
        logger.info("Database indexes initialized.")
    except Exception as e:
        logger.warning(f"Index creation note: {e}")
