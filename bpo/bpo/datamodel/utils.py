import inspect
import enum
from typing import Callable, TypeVar, Optional, Any, Type
from functools import wraps
from typing import Any, Union, Dict, List, get_origin, get_args

from bpo.datamodel.types import BaseModel


def get_attr_by_dot_notation(model: BaseModel, dot_notation: str, traverse_parents:bool=False):
    """Get attribute by dot notation.

    if traverse_parents is True it will try looking back in parents whether a part exists.

    Raises:
        AttributeError
        IndexError
    
    Example:
        class C:
            x: int

        class B:
            c_obj: C
            c_objs: List[C]

        class A:
            b_obj: B

        a_obj = A()

        For x the dot_notation => "b_obj.c_obj.x"
        For x on 3rd index of c_objs list => "b_obj.c_objs.3.x"
        For all xs on all c_objs => "b_obj.c_objs.*.x"
    """
    def helper(curr_value, parts):
        if not parts:
            return curr_value
        
        if curr_value is None:
            return 

        curr_part = parts[0]
        prev_value = curr_value
        if isinstance(curr_value, list):
            if curr_part == "*":
                return [helper(v, parts[1:]) for v in curr_value]
            else:
                curr_value = curr_value[int(curr_part)]
        else:
            try:
                curr_value = getattr(curr_value, curr_part)
            except AttributeError as aex:
                if traverse_parents:
                    # try seeing if any parent name matches
                    value = prev_value
                    while value is not None:
                        if curr_part in value.__annotations__:
                            curr_value = getattr(value, curr_part)
                            break
                        value = value._parent_ref
                else:
                    raise aex
        return helper(curr_value, parts[1:])
    return helper(model, dot_notation.split("."))


def get_attr_path(model: BaseModel, attr: str):
    attr_path = model._parent_path + f".{attr}"
    attr_path_parts = model._parent_path.split(".") + [ attr ]
    attr_path = '.'.join(attr_path_parts)
    return attr_path


def get_root_ref(node: BaseModel):
    while node._parent_ref:
        node = node._parent_ref
    return node


def merge_list_dicts(d1: Dict[str, List], d2: Dict[str, List]):
    for key in d1:
        d1[key] += d2.get(key, [])
    
    for key, value in d2.items():
        if key not in d1:
            d1[key] = value

    return d1


def validate(
        model: Type[Union[BaseModel, Any]],
        field: str,
        critical:bool=False,
        when: Optional[Callable[..., bool]]=None
    ):
    """Sets validator on "field" of "model".

    Raises:
        AttributeError: if field does not exist on model. 
    """
    T = TypeVar("T")
    def get_all_properties(obj):
        res = []
        res.extend(obj.__annotations__.keys())
        for var, var_val in inspect.getmembers(obj):
            if var.startswith("_") or inspect.ismethod(var_val) or inspect.isfunction(var_val):
                continue
            res.append(var)
        return res

    def inner(callable: T) -> T:
        model.add_validator(field=field, validator_func=callable, critical=critical, when=when)
        if field not in get_all_properties(model):
            raise AttributeError(f"Field: {field}, does not exist on model: {model}")
        return callable
    return inner

T = TypeVar("T")

def cast_args(function: T) -> T:
    """Casts Model and Enum arguments ( handles lists as well )
    """
    def _cast_to_enum_or_model(annot, value):
        if issubclass(annot, BaseModel) and isinstance(value, dict):
            return annot.load(value)
        elif issubclass(annot, enum.Enum):
            return annot(value)

    @wraps(function)
    def inner(*args, **kwargs):
        # convert all to kwargs
        arg_names = list(inspect.signature(function).parameters)[:len(args)]
        pw_as_kw = dict(zip(arg_names, args))
        all_args = {**pw_as_kw, **kwargs}

        for attr, annot in function.__annotations__.items():
            if attr == "return":
                continue

            if inspect.isclass(annot):
                res = _cast_to_enum_or_model(annot, all_args[attr])
                if res is not None:
                    all_args[attr] = res
            elif get_origin(annot) == list:
                annot_args = get_args(annot)
                if annot_args:
                    element_type = annot_args[0]
                    for i, v in enumerate(all_args[attr]):
                        res = _cast_to_enum_or_model(element_type, v)
                        if res is not None:
                            all_args[attr][i] = res
        return function(**all_args)
    return inner


def skip_validation(func):
    def inner(*args, **kwargs):
        return None
    return inner