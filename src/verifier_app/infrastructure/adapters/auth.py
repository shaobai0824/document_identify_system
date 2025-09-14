from typing import Optional

from pydantic import BaseModel


class User(BaseModel):
    """
    Represent a user in the system.
    """

    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: Optional[bool] = None
    permissions: list[str] = []  # 用戶權限列表

    def has_permission(self, permission: str) -> bool:
        """
        Check if the user has a specific permission.
        """
        return permission in self.permissions


# 模擬當前活躍用戶的工具函數
async def get_current_active_user() -> User:
    """
    Mimics getting the current active user, for dependency injection.
    """
    # 在實際應用中，這裡會從 token 或 session 中解析用戶資訊
    # 這裡只是一個佔位符，返回一個具有管理員權限的用戶
    return User(
        username="admin",
        email="admin@example.com",
        full_name="Admin User",
        permissions=["admin", "download", "upload", "verify", "audit"],
    )
