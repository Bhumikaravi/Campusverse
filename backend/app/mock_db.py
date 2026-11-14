import os
import sys
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from bson import ObjectId

logger = logging.getLogger("campusverse.mock_db")

# In-memory collections
_USERS: Dict[str, Dict[str, Any]] = {}
_MATERIALS: Dict[str, Dict[str, Any]] = {}
_CATEGORIES: Dict[str, Dict[str, Any]] = {}

def _match_doc(doc: Dict[str, Any], query: Dict[str, Any]) -> bool:
    import re
    for k, v in query.items():
        if k == "$and":
            if not all(_match_doc(doc, q) for q in v):
                return False
        elif k == "$or":
            if not any(_match_doc(doc, q) for q in v):
                return False
        elif k == "$nor":
            if any(_match_doc(doc, q) for q in v):
                return False
        elif isinstance(v, dict):
            field_val = doc.get(k)
            if "$in" in v:
                str_in = [str(item) for item in v["$in"]]
                if str(field_val) not in str_in and field_val not in v["$in"]:
                    return False
            if "$nin" in v:
                str_nin = [str(item) for item in v["$nin"]]
                if str(field_val) in str_nin or field_val in v["$nin"]:
                    return False
            if "$ne" in v:
                if field_val == v["$ne"] or str(field_val) == str(v["$ne"]):
                    return False
            if "$regex" in v:
                pattern = v["$regex"]
                if not re.search(pattern, str(field_val or ""), re.IGNORECASE):
                    return False
        else:
            if doc.get(k) != v and str(doc.get(k)) != str(v):
                return False
    return True

class MockCursor:
    def __init__(self, docs: List[Dict[str, Any]]):
        self._docs = docs

    def sort(self, *args, **kwargs):
        return self

    def skip(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    async def to_list(self, length: Optional[int] = None):
        if length is not None:
            return self._docs[:length]
        return self._docs

    def __aiter__(self):
        self._iter = iter(self._docs)
        return self

    async def __anext__(self):
        try:
            return next(self._iter)
        except StopIteration:
            raise StopAsyncIteration

class MockCollection:
    def __init__(self, name: str, store: Dict[str, Dict[str, Any]]):
        self.name = name
        self._store = store

    async def create_index(self, *args, **kwargs):
        return "mock_index"

    async def find_one(self, filter_query: Optional[Dict[str, Any]] = None, projection=None) -> Optional[Dict[str, Any]]:
        if not filter_query:
            return next((dict(d) for d in self._store.values()), None)
        for doc in self._store.values():
            if _match_doc(doc, filter_query):
                return dict(doc)
        return None

    def find(self, filter_query: Optional[Dict[str, Any]] = None, projection=None):
        if not filter_query:
            return MockCursor(list(self._store.values()))
        matched = [dict(doc) for doc in self._store.values() if _match_doc(doc, filter_query)]
        return MockCursor(matched)

    async def count_documents(self, filter_query: Optional[Dict[str, Any]] = None) -> int:
        if not filter_query:
            return len(self._store)
        return sum(1 for doc in self._store.values() if _match_doc(doc, filter_query))

    async def insert_one(self, doc: Dict[str, Any]):
        new_doc = dict(doc)
        if "_id" not in new_doc:
            new_doc["_id"] = ObjectId()
        doc_id = str(new_doc["_id"])
        self._store[doc_id] = new_doc
        class InsertResult:
            inserted_id = new_doc["_id"]
        return InsertResult()

    async def update_one(self, filter_query: Dict[str, Any], update_query: Dict[str, Any]):
        doc = await self.find_one(filter_query)
        if doc:
            doc_id = str(doc["_id"])
            if "$set" in update_query:
                self._store[doc_id].update(update_query["$set"])
        class UpdateResult:
            modified_count = 1 if doc else 0
        return UpdateResult()

    async def count_documents(self, filter_query: Optional[Dict[str, Any]] = None) -> int:
        if not filter_query:
            return len(self._store)
        count = 0
        for doc in self._store.values():
            match = True
            for k, v in filter_query.items():
                if doc.get(k) != v:
                    match = False
                    break
            if match:
                count += 1
        return count

class MockDatabase:
    def __init__(self):
        self._collections = {
            "users": MockCollection("users", _USERS),
            "materials": MockCollection("materials", _MATERIALS),
            "categories": MockCollection("categories", _CATEGORIES),
            "reviews": MockCollection("reviews", {}),
            "bookmarks": MockCollection("bookmarks", {}),
            "downloads": MockCollection("downloads", {}),
            "document_chunks": MockCollection("document_chunks", {}),
            "chapter_summaries": MockCollection("chapter_summaries", {}),
            "chat_sessions": MockCollection("chat_sessions", {}),
            "chat_messages": MockCollection("chat_messages", {}),
        }

    def __getitem__(self, name: str) -> MockCollection:
        if name not in self._collections:
            self._collections[name] = MockCollection(name, {})
        return self._collections[name]

    async def command(self, cmd, *args, **kwargs):
        return {"ok": 1.0}

mock_db_instance = MockDatabase()
