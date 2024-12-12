

from bpo.validation import validate_common_attr


if __name__ == '__main__':
    arch = {
        'name': 'escape',
        'description': 'elas'*100
    }
    errors = validate_common_attr(arch)
    print(errors)