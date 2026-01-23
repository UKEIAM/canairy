from typing import Any, Iterable, Literal, Self

from pydantic import BaseModel

from .._models import BaseParams, BaseResponse


class UBAThresholdsGetParams(BaseParams):
    use: Literal["airquality", "measure"]
    component: int
    scope: int


class UBAThreshold(BaseModel):
    id: int
    component_id: int
    scope_id: int
    type: str
    min: int
    max: int
    index: int

    @classmethod
    def from_item(cls, item: Iterable[Any]) -> Self:
        zipper = zip(UBAThreshold.model_fields.keys(), item, strict=True)
        return cls(**dict(zipper))


class UBAThresholdsGetResponse(BaseResponse):
    indices: list[str]
    data: list[UBAThreshold]

    @classmethod
    def from_response(cls, response: dict[str, Any]) -> Self:
        thresholds: list[UBAThreshold] = []
        for key, item in response.items():
            try:
                int(key)
            except ValueError:
                continue
            thresholds.append(UBAThreshold.from_item(item))
        return cls(indices=response["indices"], data=thresholds)
