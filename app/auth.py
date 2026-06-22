"""JWT 认证模块 — v4.0.0

提供 JWT token 生成、验证、刷新功能。
用于保护远程 API 访问安全。
"""

import os
import time
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path

# JWT 实现（不依赖 PyJWT，纯 Python 轻量实现）
import base64
import json
import hmac


# ── 配置 ──────────────────────────────────────────────────

# JWT 密钥：从环境变量读取，或自动生成并持久化
_jwt_secret: Optional[str] = None

# Token 有效期
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7

# 用户存储文件
_users_file: Optional[Path] = None


def _get_jwt_secret() -> str:
    """获取 JWT 密钥（懒加载，首次使用时生成）"""
    global _jwt_secret
    if _jwt_secret is None:
        _jwt_secret = os.environ.get("NEXUS_JWT_SECRET")
        if not _jwt_secret:
            # 自动生成并持久化到 data/.jwt_secret
            secret_file = _get_data_dir() / ".jwt_secret"
            if secret_file.exists():
                _jwt_secret = secret_file.read_text().strip()
            else:
                _jwt_secret = secrets.token_hex(32)
                secret_file.write_text(_jwt_secret)
    return _jwt_secret


def _get_data_dir() -> Path:
    """获取数据目录"""
    if _users_file:
        return _users_file.parent
    return Path("data")


def _get_users_file() -> Path:
    """获取用户存储文件路径"""
    if _users_file:
        return _users_file
    return _get_data_dir() / "users.json"


def init_auth(data_dir: Path):
    """初始化认证模块（在 server.py 启动时调用）"""
    global _users_file
    _users_file = data_dir / "users.json"
    # 确保默认用户存在
    _ensure_default_user()


def _ensure_default_user():
    """确保默认管理员用户存在"""
    users = _load_users()
    if "admin" not in users:
        # 默认密码: nexus2024（首次登录后应提示修改）
        _create_user("admin", "nexus2024", role="admin")


def _load_users() -> dict:
    """加载用户数据"""
    users_file = _get_users_file()
    if users_file.exists():
        try:
            return json.loads(users_file.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_users(users: dict):
    """保存用户数据"""
    users_file = _get_users_file()
    users_file.parent.mkdir(parents=True, exist_ok=True)
    users_file.write_text(json.dumps(users, ensure_ascii=False, indent=2), encoding="utf-8")


def _hash_password(password: str, salt: str = None) -> tuple[str, str]:
    """哈希密码（PBKDF2-SHA256）"""
    if salt is None:
        salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
    return base64.b64encode(hashed).decode(), salt


def _verify_password(password: str, hashed: str, salt: str) -> bool:
    """验证密码"""
    new_hash, _ = _hash_password(password, salt)
    return hmac.compare_digest(new_hash, hashed)


def _create_user(username: str, password: str, role: str = "user") -> bool:
    """创建用户"""
    users = _load_users()
    if username in users:
        return False
    hashed, salt = _hash_password(password)
    users[username] = {
        "password_hash": hashed,
        "salt": salt,
        "role": role,
        "created_at": datetime.now().isoformat(),
    }
    _save_users(users)
    return True


def authenticate_user(username: str, password: str) -> Optional[dict]:
    """验证用户名密码，返回用户信息或 None"""
    users = _load_users()
    user = users.get(username)
    if not user:
        return None
    if not _verify_password(password, user["password_hash"], user["salt"]):
        return None
    return {"username": username, "role": user.get("role", "user")}


# ── JWT 实现（纯 Python，无外部依赖）───────────────────────

def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _base64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)


def create_token(payload: dict, expires_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES) -> str:
    """创建 JWT token"""
    secret = _get_jwt_secret()
    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    token_payload = {
        **payload,
        "iat": now,
        "exp": now + expires_minutes * 60,
        "jti": secrets.token_hex(8),  # 唯一标识，防重放
    }
    header_b64 = _base64url_encode(json.dumps(header).encode())
    payload_b64 = _base64url_encode(json.dumps(token_payload).encode())
    signing_input = f"{header_b64}.{payload_b64}"
    signature = hmac.new(secret.encode(), signing_input.encode(), hashlib.sha256).digest()
    sig_b64 = _base64url_encode(signature)
    return f"{header_b64}.{payload_b64}.{sig_b64}"


def verify_token(token: str) -> Optional[dict]:
    """验证 JWT token，返回 payload 或 None"""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header_b64, payload_b64, sig_b64 = parts
        secret = _get_jwt_secret()
        # 验证签名
        signing_input = f"{header_b64}.{payload_b64}"
        expected_sig = hmac.new(secret.encode(), signing_input.encode(), hashlib.sha256).digest()
        actual_sig = _base64url_decode(sig_b64)
        if not hmac.compare_digest(expected_sig, actual_sig):
            return None
        # 解析 payload
        payload = json.loads(_base64url_decode(payload_b64))
        # 检查过期
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None


def create_access_token(username: str, role: str = "user") -> str:
    """创建 access token"""
    return create_token({"sub": username, "role": role, "type": "access"}, ACCESS_TOKEN_EXPIRE_MINUTES)


def create_refresh_token(username: str, role: str = "user") -> str:
    """创建 refresh token"""
    return create_token({"sub": username, "role": role, "type": "refresh"}, REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60)


def refresh_access_token(refresh_token: str) -> Optional[str]:
    """用 refresh token 获取新的 access token"""
    payload = verify_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        return None
    return create_access_token(payload["sub"], payload.get("role", "user"))
