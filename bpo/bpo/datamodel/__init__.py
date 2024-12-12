from dataclasses import dataclass
from typing import TypeVar

from bpo.datamodel.model import Model

T = TypeVar('T')


# BaseModel attributes arent static checkable as base class Model is assigned dynamically by the decorator
# TODO: once Intersection type is availeble this can be fixed: https://github.com/python/typing/issues/213
def datamodel(cls: T) -> T:
    cls_dict = dict(cls.__dict__)
    cls_dict.pop('__dict__', None)
    class_new = type(cls.__name__, (Model,), cls_dict)
    return dataclass(class_new)