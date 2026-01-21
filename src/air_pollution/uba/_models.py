from typing import Any, Self

from pydantic import BaseModel

from ._typing import Language


class BaseParams(BaseModel):
    pass


class BaseResponse(BaseModel):
    pass


class ItemListModel(BaseModel):
    @classmethod
    def from_response(cls, result: list[Any]) -> list[Self]:
        return [cls(**item) for item in result]


class UBAResponseRequest(BaseModel):
    recent: bool
    index: str
    lang: Language
