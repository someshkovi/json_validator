
from typing import Optional
from bpo.datamodel import datamodel
from bpo.models.properties import ServiceAdditionalAttributes

@datamodel
class GenericInputs:
    name: Optional[str]
    userLabel: Optional[str]
    description: Optional[str]
    customerName: Optional[str]
    note: Optional[str]
    serviceAdditionalAttributes: Optional[ServiceAdditionalAttributes] 

