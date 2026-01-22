from typing import Any, Iterable, Self

from pydantic import BaseModel

from .._models import BaseParams, BaseResponse
from .._typing import Language


class Network(BaseModel):
    id: int
    code: str
    name: str

    @classmethod
    def from_item(cls, item: Iterable[Any]) -> Self:
        foo = dict(zip(Network.model_fields.keys(), item, strict=True))
        return cls(**foo)


class UBANetworksGetParams(BaseParams):
    lang: Language | None


class UBANetworksGetResponse(BaseResponse):
    indices: list[str]
    count: int
    data: list[Network]

    @classmethod
    def from_response(cls, response: dict[str, dict[str, Any]]) -> Self:
        data = (Network.from_item(val) for val in cls.iter_response_data(response))
        return cls(
            indices=response.get("indices"), count=response.get("count"), data=data
        )
