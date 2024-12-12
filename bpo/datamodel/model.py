import enum
import traceback
import inspect
from collections import defaultdict, deque
from dataclasses import asdict
from typing import (
    get_args, get_origin,
    Union, Dict, List, Any, Tuple, Callable, Type, Optional )

from bpo.datamodel.types import BaseModel
from bpo.datamodel.utils import get_attr_path, get_root_ref
from bpo.utils.common_utils import DEBUG, WARN, log


class ModelParsingException(Exception):
    def __init__(self, attr_path: str, type: Type, attr_value: Any, *args, **kwargs):
        self.attr_path = attr_path
        self.type = type
        self.attr_value = attr_value

        self._message = f"""Input parsing failed.
        Failed attribute path: {self.attr_path}
        Failed attribute expected type: {self.type}
        Failed attribute input value: {self.attr_value})
        """
        super().__init__(*args, **kwargs)
    
    def __repr__(self):
        return f"{self.__class__.__name__}({self._message})"
    
    def __str__(self):
        return self._message


class ModelValidationException(Exception):
    def __init__(self, attr_path: str, validation_func: Callable, *args, **kwargs):
        self.attr_path = attr_path
        self.validation_func = validation_func

        self._message = f"""Input validation failed.
        Failed attribute path: {self.attr_path}
        Failed in validation function: {validation_func.__name__} 
        """
        super().__init__(*args, **kwargs)
    
    def __repr__(self):
        return f"{self.__class__.__name__}({self._message})"
    
    def __str__(self):
        return self._message


class Model(BaseModel):
    """BaseModel class for augmenting dataclass functionality with dump/load from dict and validation.
    """
    _PARENT_PATH_ARG_NAME = "parent_path"
    _ATTR_PATH_ARG_NAME = "attr_path"
    _ROOT_REF_ARG_NAME = "root_ref"
    _PARENT_REF_ARG_NAME = "parent_ref"

    @classmethod
    def _parse_value(cls, value: Any, annotation: Type, attribute_path:str=""):
        origin_type = get_origin(annotation)
        annotation_args = get_args(annotation)
        if annotation is type(None) or value is None:
            return
        elif inspect.isclass(annotation):
            if issubclass(annotation, BaseModel):
                return annotation.load(value, attribute_path)
            else:
                return annotation(value)
        elif origin_type is Union:
            for annotation_arg in annotation_args:
                parsed_value = cls._parse_value(
                    value=value,
                    annotation=annotation_arg,
                    attribute_path=attribute_path
                )
                if parsed_value is not None:
                    return parsed_value
        elif origin_type is list:
            parsed_list = []
            for index, v in enumerate(value):
                parsed_item = cls._parse_value(
                    value=v,
                    annotation=annotation_args[0],
                    attribute_path=f"{attribute_path}.{index}"
                )
                parsed_list.append(parsed_item)
            return parsed_list

    def dump(self):
        """convert object to a dict.

        should handle enums gracefully.
        """
        dict_repr = asdict(self)
        stack = [dict_repr]
        while stack:
            node = stack.pop()
            for key, value in node.items():
                if isinstance(value, enum.Enum):
                    node[key] = value.value
                elif isinstance(value, dict):
                    stack.append(value)
                elif isinstance(value, list):
                    for v in value:
                        if isinstance(v, dict):
                            stack.append(v)
        return dict_repr
    
    @classmethod
    def load(cls, input_dict: dict, parent_path="root"):
        """convert dict to an object.

        1. handle nested dicts.
        2. print parsing exceptions neatly.
        3. have references to parents.
        4. able to retrieve attribute path in model tree.
        """
        processed_input = {}
        for attribute, annotation in cls.__annotations__.items():
            attr_value = input_dict.get(attribute)
            attribute_path = f"{parent_path}.{attribute}"
            try:
                processed_input[attribute] = cls._parse_value(
                    value=attr_value,
                    annotation=annotation,
                    attribute_path=attribute_path
                )
            except Exception as e:
                raise ModelParsingException(
                    attr_path=attribute_path,
                    type=annotation,
                    attr_value=attr_value
                ) from e

        # Model is adds support on "top" of datalcass/
        # it is assumed that the class takes input args
        parsed_root = cls(**processed_input) # type: ignore 
        parsed_root._parent_path = parent_path

        for key, value in processed_input.items():
            if issubclass(type(value), BaseModel):
                value._parent_ref = parsed_root
            elif isinstance(value, list):
                for el in value:
                    if issubclass(type(el), BaseModel):
                        el._parent_ref = parsed_root

        return parsed_root
    
    def _get_extra_validate_args(self, validator_func: Callable, field: str) -> Dict[str, Any]:
        """Pass extras / parent_path / attr_path ONLY if required.

        Avoid unnecessary parsing of extra args.
        """
        validation_function_args = dict()
        validation_function_params = tuple(inspect.signature(validator_func).parameters)
        for v_func_param in validation_function_params[1:]:
            if v_func_param == self._PARENT_PATH_ARG_NAME:
                validation_function_args[v_func_param] = self._parent_path
            elif v_func_param == self._ATTR_PATH_ARG_NAME:
                validation_function_args[v_func_param] = self._parent_path + f".{field}"
            elif v_func_param == self._ROOT_REF_ARG_NAME:
                validation_function_args[v_func_param] = get_root_ref(self)
            elif v_func_param == self._PARENT_REF_ARG_NAME:
                validation_function_args[v_func_param] = self
        return validation_function_args
    
    def _bfs(self) -> dict:
        """Collect return values for attributes in self model.
        """
        q = deque([self])
        while q:
            node = q.popleft()
            yield node

            for field in node.__annotations__:
                field_value = getattr(node, field)
                if issubclass(type(field_value), BaseModel):
                    q.append(field_value)
                elif isinstance(field_value, list):
                    for attribute_el in field_value:
                        if issubclass(type(attribute_el), BaseModel):
                            q.append(attribute_el)
    
    def _call_validators(self, validators_map: Optional[Dict[str, List]], stop_on_error: bool=False):
        result = defaultdict(list)
        if validators_map is None:
            return result

        for field, validators in validators_map.items():
            field_value = getattr(self, field)
            member_path = get_attr_path(self, field)

            for validator_data in validators:
                validator = validator_data["func"]

                try:
                    log(log_id=DEBUG, message=f"Validating field: {member_path} - validator function - {validator.__name__}")
                    res = validator(field_value, **self._get_extra_validate_args(validator, field))
                    if res is not None:
                        log(log_id=WARN, message=f"Validation ERROR for: {member_path}, ErrorResponse: {res}")
                        result[member_path].append(res)
                        if stop_on_error:
                            return result
                    else:
                        log(log_id=DEBUG, message=f"Validation OK for: {member_path}")
                except Exception as ex:
                    raise ModelValidationException(
                        attr_path = member_path,
                        validation_func=validator
                    ) from ex
        return result
    
    def _call_critical_validations(self):
        return self._call_validators(self._critical_validators, stop_on_error=True)
    
    def _call_normal_validations(self):
        return self._call_validators(self._validators)

    def validate(self) -> Tuple[Dict[str, List], List[Exception]]:
        """First performs critical and then normal validations.

        If any critical validation fails returns immediately.
        """
        exceptions = []
        for node in self._bfs():
            try:
                critical_errors = node._call_critical_validations()
                if critical_errors:
                    return critical_errors, exceptions
            except Exception as ex:
                exceptions.append(traceback.format_exc())
            
        result = {}
        for node in self._bfs():
            try:
                errors = node._call_normal_validations()
                result.update(errors)
            except Exception as ex:
                exceptions.append(traceback.format_exc())
        return result, exceptions