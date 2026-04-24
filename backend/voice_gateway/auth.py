"""语音网关短期 token 签发与校验。"""

from datetime import timedelta
from typing import Any, Dict

import jwt

from backend.config import config
from backend.utils.datetime_utils import get_now

from .config import VoiceGatewayAuthConfig


class VoiceTokenError(Exception):
    """语音 token 错误。"""


class VoiceTokenManager:
    """语音会话 token 管理器。"""

    def __init__(self, auth_config: VoiceGatewayAuthConfig):
        self.auth_config = auth_config
        self.secret_key = config.get("jwt_secret_key", "your-secret-key-change-this-in-production")
        self.algorithm = "HS256"

    def create_token(
        self,
        session_id: str,
        user_id: str,
        chat_id: str,
        device_id: str = "",
        platform: str = "",
    ) -> str:
        now = get_now()
        exp = now + timedelta(seconds=self.auth_config.token_ttl_seconds)
        payload: Dict[str, Any] = {
            "typ": "voice_session",
            "iss": self.auth_config.issuer,
            "iat": now,
            "exp": exp,
            "session_id": session_id,
            "user_id": user_id,
            "chat_id": chat_id,
            "device_id": device_id,
            "platform": platform,
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def decode_token(self, token: str) -> Dict[str, Any]:
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
        except jwt.ExpiredSignatureError as exc:
            raise VoiceTokenError("token expired") from exc
        except jwt.InvalidTokenError as exc:
            raise VoiceTokenError("invalid token") from exc

        if payload.get("typ") != "voice_session":
            raise VoiceTokenError("invalid token type")

        return payload

