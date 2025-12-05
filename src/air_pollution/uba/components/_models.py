from typing import Any, Self
from pydantic import BaseModel
from .._models import BaseParams, BaseResponse
from .._typing import Index, Language


class ComponentsGetParams(BaseParams):
    lang: Language
    index: Index


class Component(BaseModel):
    id: int
    code: str
    symbol: str
    unit: str
    name: str

    @classmethod
    def from_list_item(cls, item: list[str]) -> Self:
        return cls(**dict(zip(cls.model_fields.keys(), item)))


class _BaseComponentsGetResponse(BaseResponse):
    count: int
    indices: list[str]


class ComponentsGetResponse(BaseResponse):
    indices: list[str]
    data: list[Component]

    @classmethod
    def from_response(cls, response: dict[str, Any]) -> Self:
        components: list[Component] = []
        for key, val in response.items():
            try:
                int(key)
            except ValueError:
                continue
            components.append(Component.from_list_item(val))
        return cls(indices=response['indices'], data=components)

