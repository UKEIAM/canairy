from typing import Any, Self
from pydantic import BaseModel
from .._models import BaseParams, BaseResponse
from .._typing import Language


class ScopesGetParams(BaseParams):
    lang: Language

class Scope(BaseModel):
    id: int
    code: str
    time_base: str
    time_scope: str
    is_max: bool
    name: str

    @classmethod
    def from_list_item(cls, item: list[str]) -> Self:
        data = dict(zip(cls.model_fields.keys(), item, strict=False))
        return cls(**data)


class ScopesGetResponse(BaseResponse):
    indices: list[str]
    data: list[Scope]

    @classmethod
    def from_response(cls, response: dict[str, Any]) -> Self:
        scopes: list[Scope] = []
        for key, val in response.items():
            try:
                int(key)
            except ValueError:
                continue
            scopes.append(Scope.from_list_item(val))
        return cls(indices=response["indices"], data=scopes)
