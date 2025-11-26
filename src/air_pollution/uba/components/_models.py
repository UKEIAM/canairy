from typing import cast
from pydantic import BaseModel, create_model
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


class _BaseComponentsGetResponse(BaseResponse):
    count: int
    indices: list[str]


def create_components_get_response_model(
    res: dict[str, int | str | list[str]],
) -> BaseResponse:
    specs = {k: list[str] for k in res.keys() if k not in ["count", "indices"]}
    model = create_model(
        "ComponentsGetResponse", **specs, __base__=_BaseComponentsGetResponse
    )  # type: ignore
    return cast(BaseResponse, model)
