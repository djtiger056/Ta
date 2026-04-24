"""用户认证工具类"""
import hashlib
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from backend.config import config
from backend.utils.datetime_utils import get_now


class AuthManager:
    """认证管理器"""
    
    # JWT 配置
    SECRET_KEY = config.get('jwt_secret_key', 'your-secret-key-change-this-in-production')
    ALGORITHM = 'HS256'
    TOKEN_EXPIRE_HOURS = 24 * 7  # 7天过期
    
    @staticmethod
    def hash_password(password: str) -> str:
        """密码哈希"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """验证密码"""
        return AuthManager.hash_password(password) == password_hash
    
    @staticmethod
    def create_token(user_id: int, username: str, qq_user_id: Optional[str] = None) -> str:
        """创建访问令牌"""
        payload = {
            'user_id': user_id,
            'username': username,
            'qq_user_id': qq_user_id,
            'exp': get_now() + timedelta(hours=AuthManager.TOKEN_EXPIRE_HOURS),
            'iat': get_now()
        }
        return jwt.encode(payload, AuthManager.SECRET_KEY, algorithm=AuthManager.ALGORITHM)
    
    @staticmethod
    def decode_token(token: str) -> Optional[Dict[str, Any]]:
        """解码访问令牌"""
        try:
            payload = jwt.decode(token, AuthManager.SECRET_KEY, algorithms=[AuthManager.ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError as e:
            # 记录错误以便调试
            print(f"[DEBUG] Token decode error: {e}")
            return None
    
    @staticmethod
    def get_user_from_token(token: str) -> Optional[Dict[str, Any]]:
        """从令牌获取用户信息"""
        payload = AuthManager.decode_token(token)
        if payload:
            return {
                'user_id': payload.get('user_id'),
                'username': payload.get('username'),
                'qq_user_id': payload.get('qq_user_id')
            }
        return None


# 全局认证管理器实例
auth_manager = AuthManager()