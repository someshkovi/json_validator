from dataclasses import dataclass, fields, is_dataclass, Field
from typing import Any, Type, TypeVar, get_type_hints, Optional, List, Callable, Dict
import json

T = TypeVar('T')

class ValidationError(Exception):
    def __init__(self, errors: Dict[str, str]):
        self.errors = errors
        super().__init__(self._format_errors())

    def _format_errors(self) -> str:
        return "; ".join(f"{field}: {error}" for field, error in self.errors.items())

def from_dict(cls: Type[T], data: dict) -> T:
    if not is_dataclass(cls):
        raise TypeError(f"{cls.__name__} is not a dataclass")

    field_types = get_type_hints(cls)
    init_kwargs = {}

    for field_name, field_type in field_types.items():
        if field_name in data:
            field_value = data[field_name]
            if is_dataclass(field_type):
                init_kwargs[field_name] = from_dict(field_type, field_value)
            else:
                init_kwargs[field_name] = field_value
        elif hasattr(field_type, '__origin__') and field_type.__origin__ is Optional:
            init_kwargs[field_name] = None

    return cls(**init_kwargs)

def dataclass_with_from_dict(cls: Type[T]) -> Type[T]:
    cls = dataclass(cls)
    cls.from_dict = classmethod(from_dict)
    cls.validate = validate
    return cls

def validate(instance: Any) -> None:
    errors = {}
    for field_info in fields(instance):
        value = getattr(instance, field_info.name)
        validators = field_info.metadata.get('validators', [])
        for validator in validators:
            if not validator(value):
                errors[field_info.name] = f"Validation failed for value: {value}"
    if errors:
        raise ValidationError(errors)

# Example validators
def is_positive(value: int) -> bool:
    return value > 0

def is_non_empty_string(value: str) -> bool:
    return bool(value)

def is_email(value: str) -> bool:
    import re
    email_regex = r'^\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    return re.match(email_regex, value) is not None

# Example dataclasses
@dataclass_with_from_dict
class Address:
    street: str
    city: str
    zipcode: str

@dataclass_with_from_dict
class User:
    name: str = field(metadata={'validators': [is_non_empty_string]})
    age: Optional[int] = field(default=None, metadata={'validators': [is_positive]})
    email: str = field(metadata={'validators': [is_email]})
    address: Optional[Address] = None

# Example usage
json_data = '''
{
    "name": "John Doe",
    "age": 30,
    "email": "john.doe@example.com",
    "address": {
        "street": "123 Main St",
        "city": "Anytown",
        "zipcode": "12345"
    },
    "extra_field": "this will be ignored"
}
'''

data_dict = json.loads(json_data)
try:
    user = User.from_dict(data_dict)
    user.validate()
    print(user)
except ValidationError as e:
    print("Validation errors:", e.errors)