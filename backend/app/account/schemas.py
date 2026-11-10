from typing import Annotated, Literal

from pydantic import BaseModel, Field, SecretStr

from ..schemas import Input


class PasswordChange(Input):
    current_password: Annotated[SecretStr, Field(min_length=1, max_length=128)]
    new_password: Annotated[SecretStr, Field(min_length=12, max_length=128)]


class PasswordChanged(BaseModel):
    ok: Literal[True] = True
    reauthentication_required: Literal[True] = True
