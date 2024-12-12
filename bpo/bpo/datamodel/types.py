from typing import Dict, List, Optional, Callable, Tuple
from abc import ABC, abstractmethod
from collections import defaultdict


class BaseModel(ABC):
    _parent_ref: Optional["BaseModel"] = None
    _parent_path: str = ""
    _validators: Optional[Dict[str, List]] = None
    _critical_validators: Optional[Dict[str, List]] = None
    
    @abstractmethod
    def dump(self) -> dict: ...
    
    @classmethod
    @abstractmethod
    def load(cls, input_dict: dict, parent_path="root") -> "BaseModel": ...
    
    @classmethod
    def add_validator(cls, field: str, validator_func: Callable, critical:bool=False, when: Optional[Callable]=None):
        if critical:
            if cls._critical_validators is None:
                cls._critical_validators = defaultdict(list)
            cls._critical_validators[field].append(dict(func=validator_func, when=when))
        else:
            if cls._validators is None:
                cls._validators = defaultdict(list)
            cls._validators[field].append(dict(func=validator_func, when=when))

    @abstractmethod
    def validate(self) -> Tuple[Dict[str, List], List[Exception]]: ...