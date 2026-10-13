from typing import Any, Self

from pydantic import BaseModel

from .._models import BaseParams, BaseResponse
from .._typing import Language


class UBAScopesGetParams(BaseParams):
    lang: Language


class UBAScope(BaseModel):
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


EXPECTED_SCOPE_INDICES = [
    "scope id",
    "scope code",
    "scope time base",
    "scope time scope",
    "scope time is max",
    "scope name",
]


class UBAScopesGetResponse(BaseResponse):
    indices: list[str]
    data: list[UBAScope]

    @classmethod
    def from_response(cls, response: dict[str, Any]) -> Self:
        if response["indices"] != EXPECTED_SCOPE_INDICES:
            raise ValueError(
                "Unexpected column order in UBA scopes response: "
                f"got {response['indices']!r}, expected {EXPECTED_SCOPE_INDICES!r}"
            )
        scopes: list[UBAScope] = []
        for key, val in response.items():
            try:
                int(key)
            except ValueError:
                continue
            scopes.append(UBAScope.from_list_item(val))
        return cls(indices=response["indices"], data=scopes)
