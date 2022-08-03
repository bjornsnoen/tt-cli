import secrets

import keyring

from ttcli.utils import typed_cache


@typed_cache
def get_key() -> str:
    key = keyring.get_password("ttcli", "sqlite")

    if key is not None:
        return key

    key = secrets.token_urlsafe()
    keyring.set_password("ttcli", "sqlite", key)

    return key
