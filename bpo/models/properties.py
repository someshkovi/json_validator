

from dataclasses import dataclass
from typing import Optional

from bpo.datamodel import datamodel


@datamodel
class ServiceAdditionalAttributes:
    token: Optional[str]


@dataclass
class ErrorResponse:
    attributeName: Optional[str] = None
    errorMessage: Optional[str] = None