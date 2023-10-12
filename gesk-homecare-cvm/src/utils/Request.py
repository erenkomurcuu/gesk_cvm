from typing import Optional, Dict, List, Any, Union

from ..exceptions import InvalidFormatException


def validate_request(event, required) -> List:
    validate_response = []
    if required:
        if "query" in required:
            if event['queryStringParameters'] is None:
                event['queryStringParameters'] = {}

            for q_item in required['query']:
                if q_item not in event['queryStringParameters']:
                    validate_response.append({"type": "required", "path": "qString", "param": q_item, "value": None})
        if "body" in required:
            if event['body'] is None:
                event['body'] = {}

            for item in required['body']:
                if item not in event['body']:
                    validate_response.append({"type": "required", "path": "body", "param": item, "value": None})
        if "headers" in required:
            if event['headers'] is None:
                event['headers'] = {}

            for item in required['headers']:
                if item not in event['headers']:
                    validate_response.append({"type": "required", "path": "header", "param": item, "value": None})

        return validate_response
    else:
        raise InvalidFormatException("Required Parameter Cannot be None")
