
from typing import Any, Optional

from azure.core.credentials import TokenCredential, AccessToken


class AccessTokenCredential(TokenCredential):
    def __init__(self, access_token, expires):
        self.access_token = access_token
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