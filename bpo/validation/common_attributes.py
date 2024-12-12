


from bpo.datamodel.utils import validate
from bpo.models.common import GenericInputs
from bpo.models.properties import ErrorResponse


@validate(model=GenericInputs, field="description")
def validate_evpn_svc_description(service_desc: str, root_ref: GenericInputs):
    if len(service_desc)>50:
        return ErrorResponse(
            attributeName="description",
            errorMessage='description length too long'
        )