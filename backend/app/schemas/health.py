from pydantic import BaseModel


class HealthRead(BaseModel):
    status: str
    database: str
    vector_store: str

