from ..utils.Request import validate_request
from ..utils.Response import error_response
from ..modules import cvm
import json


def activate_device(event, context):
    error = validate_request(event, {"body": ["device_serial", "device_token"], "query": []})
    if error:
        return error_response(error, 400)

    event['body'] = json.loads(event['body'])
    return cvm.activate_device(event['body']['device_serial'], event['body']['device_token'])


def renew_device_certificates(event, context):
    error = validate_request(event, {"body": ["device_serial", "device_token"], "query": []})
    if error:
        return error_response(error, 400)

    event['body'] = json.loads(event['body'])

    return cvm.renew_device_certificates(event['body']['device_serial'], event['body']['device_token'])
