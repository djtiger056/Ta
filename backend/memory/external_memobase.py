"""
Memobase 外部记忆系统客户端（REST API）
"""

from typing import Any, Dict, List, Optional, Tuple
import uuid
import aiohttp


class MemobaseClient:
    """Memobase REST API 客户端（异步）"""

    def __init__(self, base_url: str, api_key: Optional[str] = None, timeout: int = 30):
        self.base_url = (base_url or "").rstrip("/")
        self.api_key = api_key
        self.timeout = max(5, int(timeout or 30))

    def _build_url(self, path: str) -> str:
        path = path or ""
        if path.startswith("http://") or path.startswith("https://"):
            return path
        if not path.startswith("/"):
            path = "/" + path
        if path.startswith("/api/v1"):
            return f"{self.base_url}{path}"
        return f"{self.base_url}/api/v1{path}"

    def _normalize_user_id(self, user_id: str) -> str:
        if not user_id:
            return user_id
        try:
            u = uuid.UUID(str(user_id))
            if u.version in (4, 5):
                return str(u)
        except Exception:
            pass
        # Deterministic UUID5 to satisfy Memobase v0.0.42+ UUID requirement.
        return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{self.base_url}:{user_id}"))

    async def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
        allow_status: Optional[List[int]] = None,
        allow_errno: Optional[List[int]] = None,
        return_status: bool = False,
    ) -> Any:
        allow_status_set = set(allow_status or [])
        allow_errno_set = set(allow_errno or [])
        url = self._build_url(path)
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        timeout = aiohttp.ClientTimeout(total=self.timeout)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.request(
                method=method.upper(),
                url=url,
                params=params,
                json=json_body,
                headers=headers,
            ) as resp:
                status = resp.status
                content_type = resp.headers.get("Content-Type", "")
                if status >= 400 and status not in allow_status_set:
                    detail = await resp.text()
                    raise RuntimeError(f"Memobase请求失败: HTTP {status} - {detail}")

                if "application/json" in content_type:
                    data = await resp.json()
                else:
                    data = await resp.text()
                if isinstance(data, dict) and "errno" in data:
                    errno = data.get("errno", 0)
                    try:
                        errno_value = int(errno)
                    except Exception:
                        errno_value = errno
                    if errno_value not in (0, "0"):
                        if errno_value in allow_errno_set:
                            data = data.get("data")
                        else:
                            errmsg = data.get("errmsg", "")
                            raise RuntimeError(f"Memobase request failed: errno {errno} - {errmsg}")
                    else:
                        data = data.get("data")
                if return_status:
                    return status, data
                return data

    async def ping(self) -> bool:
        try:
            data = await self._request("GET", "/healthcheck")
            if isinstance(data, dict):
                return data.get("status") == "ok"
            return True
        except Exception:
            return False

    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        user_id = self._normalize_user_id(user_id)
        status, data = await self._request(
            "GET",
            f"/users/{user_id}",
            allow_status=[404],
            allow_errno=[404],
            return_status=True,
        )
        if status == 404:
            return None
        return data

    async def create_user(self, user_id: str, data: Optional[Dict[str, Any]] = None) -> str:
        user_id = self._normalize_user_id(user_id)
        payload = {
            "id": user_id,
            "data": data or {}
        }
        result = await self._request("POST", "/users", json_body=payload)
        if isinstance(result, dict):
            return result.get("id") or user_id
        return user_id

    async def get_or_create_user(self, user_id: str) -> str:
        user_id = self._normalize_user_id(user_id)
        existing = await self.get_user(user_id)
        if existing is not None:
            return user_id
        return await self.create_user(user_id)

    async def insert_chat_blob(self, user_id: str, messages: List[Dict[str, Any]]) -> str:
        user_id = self._normalize_user_id(user_id)
        payload = {
            "blob_type": "chat",
            "blob_data": {"messages": messages},
        }
        result = await self._request("POST", f"/blobs/insert/{user_id}", json_body=payload)
        if isinstance(result, dict):
            return result.get("id", "")
        return ""

    async def flush(self, user_id: str, blob_type: str = "chat", sync: bool = False) -> bool:
        user_id = self._normalize_user_id(user_id)
        params = {"wait_process": bool(sync)}
        await self._request("POST", f"/users/buffer/{user_id}/{blob_type}", params=params)
        return True

    async def get_profiles(self, user_id: str) -> List[Dict[str, Any]]:
        user_id = self._normalize_user_id(user_id)
        status, data = await self._request(
            "GET",
            f"/users/profile/{user_id}",
            allow_status=[404],
            allow_errno=[404],
            return_status=True
        )
        if status == 404:
            return []
        if isinstance(data, dict):
            profiles = data.get("profiles") or []
            # Normalize topic fields for compatibility.
            for profile in profiles:
                attrs = profile.get("attributes") or {}
                if "topic" not in profile and "sub_topic" not in profile:
                    profile["topic"] = attrs.get("topic") or ""
                    profile["sub_topic"] = attrs.get("sub_topic") or ""
            return profiles
        return []

    async def get_events(self, user_id: str, limit: int = 10, offset: int = 0, query: Optional[str] = None) -> List[Dict[str, Any]]:
        user_id = self._normalize_user_id(user_id)
        params: Dict[str, Any] = {
            "topk": limit,
        }
        path = f"/users/event/{user_id}"
        if query:
            path = f"/users/event/search/{user_id}"
            params["query"] = query
        status, data = await self._request(
            "GET",
            path,
            params=params,
            allow_status=[404],
            allow_errno=[404],
            return_status=True
        )
        if status == 404:
            return []
        if isinstance(data, dict):
            return data.get("events") or []
        return []

    async def get_context(
        self,
        user_id: str,
        max_token_size: int = 500,
        prefer_topics: Optional[List[str]] = None,
        customize_context_prompt: Optional[str] = None,
    ) -> str:
        user_id = self._normalize_user_id(user_id)
        params: Dict[str, Any] = {
            "max_token_size": max_token_size,
        }
        if prefer_topics:
            params["prefer_topics"] = prefer_topics
        if customize_context_prompt:
            params["customize_context_prompt"] = customize_context_prompt
        status, data = await self._request(
            "GET",
            f"/users/context/{user_id}",
            params=params,
            allow_status=[404],
            allow_errno=[404],
            return_status=True
        )
        if status == 404:
            return ""
        if isinstance(data, dict):
            return data.get("context") or ""
        return ""
