
from typing import Any, Optional

from azure.core.credentials import TokenCredential, AccessToken

# Should probably migrate to this super class
#from azure.identity.aio._internal.get_token_mixin import GetTokenMixin


class AccessTokenCredential(TokenCredential):
    def __init__(self, access_token: str, refresh_token: str, expires: int):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.expires = expires

    def get_token(
        self,
        *scopes: str,
        claims: Optional[str] = None,
        tenant_id: Optional[str] = None,
        enable_cae: bool = False,
        **kwargs: Any,
    ) -> AccessToken:
        return AccessToken(self.access_token, self.expires)