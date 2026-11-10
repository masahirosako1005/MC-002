"""Screen new credentials locally; never apply a new policy during login.

Only screening uses case folding. Password storage and authentication retain the
exact string. This fixed historical list is not an exhaustive breach database.
"""

import hashlib
import re
from pathlib import Path

from fastapi import HTTPException

_BLOCKLIST_SHA256 = "466d943ca1e1a67b32cff070a41a4d99bee8db86347ad422cbae1ed976b7cd7c"


def _load_blocklist():
    raw = (Path(__file__).parent / "account" / "data" / "common-passwords.sha256").read_bytes()
    if hashlib.sha256(raw).hexdigest() != _BLOCKLIST_SHA256:
        raise RuntimeError("Local password screening list integrity check failed")
    entries = frozenset(raw.decode("ascii").splitlines())
    if len(entries) != 46825 or any(not re.fullmatch(r"[a-f0-9]{64}", entry) for entry in entries):
        raise RuntimeError("Local password screening list format is invalid")
    return entries


_COMMON_PASSWORDS = _load_blocklist()
_SITE_TERMS = ("konotabijitaku", "講の旅じたく", "nishicity", "n西市")


def validate_new_password(password: str, username: str) -> None:
    """Raise a value-free validation message for registration or password change."""
    if not 12 <= len(password) <= 128:
        raise HTTPException(422, "パスワードは12〜128文字で入力してください。")
    screened = password.casefold()
    if hashlib.sha256(screened.encode("utf-8")).hexdigest() in _COMMON_PASSWORDS:
        raise HTTPException(422, "よく使われるパスワードです。別の長い言葉の組み合わせにしてください。")
    # Reject an account/site name with only separators, a common label, or
    # trailing digits. A longer unrelated phrase containing the name is allowed.
    compact = "".join(char for char in screened if char.isalnum())
    account = "".join(char for char in username.casefold() if char.isalnum())
    terms = (*_SITE_TERMS, account, account + "local", account + "password")
    if any(term and re.fullmatch(re.escape(term) + r"\d{0,12}", compact) for term in terms):
        raise HTTPException(422, "アカウントIDやサービス名をもとにしたパスワードは使えません。")
