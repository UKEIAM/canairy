from pydantic import BaseModel


class Network(BaseModel):
    id: int
    code: str
    name: str
