from typing import Any, Self

from pydantic import BaseModel

from .._models import BaseParams, BaseResponse
from .._typing import Language


class UBAComponentsGetParams(BaseParams):
    lang: Language


class UBAComponent(BaseModel):
    id: int
    code: str
    symbol: str
    unit: str
    name: str

    @classmethod
    def from_list_item(cls, item: list[str]) -> Self:
        data = dict(zip(cls.model_fields.keys(), item, strict=True))
        return cls(**data)


class UBAComponentsGetResponse(BaseResponse):
    indices: list[str]
    data: list[UBAComponent]

    @classmethod
    def from_response(cls, response: dict[str, Any]) -> Self:
        components: list[UBAComponent] = []
        for key, val in response.items():
            try:
                int(key)
            except ValueError:
                continue
            components.append(UBAComponent.from_list_item(val))
        return cls(indices=response["indices"], data=components)
