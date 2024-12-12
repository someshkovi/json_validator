

from typing import Dict, List
from bpo.models.common import GenericInputs
from bpo.models.properties import ErrorResponse

from bpo.validation.common_attributes import *

def input_model_validation(inputs_model: GenericInputs,
                           context=None):
    inputs_model.context = context
    validation_error_responses, exception_tracebacks = inputs_model.validate()  # type: ignore
    errors = []

    for attribute_key, validation_errors in validation_error_responses.items():
        for validation_error in validation_errors:
            if isinstance(validation_error, ErrorResponse):
                errors.append(validation_error)

    if exception_tracebacks:
        exp_err_response = ErrorResponse(
            attributeName="Exceptions",
            errorMessage=f'\n{"-" * 50}\n'.join(exception_tracebacks),
        )
        errors.append(exp_err_response)
    return errors



def validate_common_attr(inputs: Dict, context=None) -> List[ErrorResponse]:
    inputs_model: GenericInputs = GenericInputs.load(inputs) # type: ignore
    return input_model_validation(inputs_model, context)

