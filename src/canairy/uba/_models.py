from collections.abc import Generator
from typing import Any, Self

from pydantic import BaseModel

from ._typing import Language


class BaseParams(BaseModel):
    pass


class BaseResponse(BaseModel):
    @staticmethod
    def iter_response_data[T](
        response: dict[str, dict[str, T]],
    ) -> Generator[T, None, None]:
        if data := response.get("data"):
            yield from data.values()
        else:
            raise AttributeError("Response is missing `data` attribute")


class ItemListModel(BaseModel):
    @classmethod
    def from_response(cls, result: list[Any]) -> list[Self]:
        return [cls(**item) for item in result]


class UBAResponseRequest(BaseModel):
    recent: bool
    index: str
    lang: Language
