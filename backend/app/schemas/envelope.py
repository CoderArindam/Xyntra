from typing import TypeVar, Generic, Optional
from pydantic import BaseModel

DataT = TypeVar('DataT')

class MetaResponse(BaseModel):
    cursor: Optional[str] = None
    has_more: Optional[bool] = None
    total_count: Optional[int] = None

class DataEnvelope(BaseModel, Generic[DataT]):
    data: DataT
    meta: Optional[MetaResponse] = None
