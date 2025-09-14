from abc import ABC, abstractmethod
from typing import Any, Optional


class AbstractAuthService(ABC):
    """
    抽象認證服務介面，定義了認證服務需要實現的功能。
    """

    @abstractmethod
    async def authenticate_user(self, username: str, password: str) -> Optional[Any]:
        """
        驗證用戶憑證。
        Args:
            username (str): 用戶名。
            password (str): 密碼。
        Returns:
            Optional[Any]: 如果驗證成功則返回用戶對象，否則返回 None。
        """
        pass

    @abstractmethod
    async def get_current_user(self, token: str) -> Optional[Any]:
        """
        根據令牌獲取當前用戶資訊。
        Args:
            token (str): 用戶的認證令牌。
        Returns:
            Optional[Any]: 如果令牌有效則返回用戶對象，否則返回 None。
        """
        pass

    @abstractmethod
    async def create_access_token(self, data: dict, expires_delta: Optional[int] = None) -> str:
        """
        為用戶創建一個新的訪問令牌。
        """
        pass
