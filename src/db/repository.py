from abc import ABC, abstractmethod
from typing import Generic, TypeVar, List, Optional
from sqlalchemy.orm import Session
from src.db.base import Base

ModelType = TypeVar("ModelType", bound=Base)

class Repository(Generic[ModelType], ABC):
    def __init__(self, db: Session):
        self.db = db

    @abstractmethod
    def get(self, id: int) -> Optional[ModelType]:
        pass

    @abstractmethod
    def get_all(self) -> List[ModelType]:
        pass

    @abstractmethod
    def add(self, entity: ModelType) -> ModelType:
        pass

    @abstractmethod
    def delete(self, entity: ModelType):
        pass
