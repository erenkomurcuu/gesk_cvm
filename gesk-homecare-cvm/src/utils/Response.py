import json
import decimal
import datetime
from ..utils.Constants import DEBUG

# Supports Decimal In JSON
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, decimal.Decimal):
            return {'__Decimal__': str(obj)}
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        # Let the base class default method raise the TypeError
        return super().default(obj)


def make_response(payload: list or dict, status_code=200, extra=None) -> dict:

    base_body = {
        "status": True if 200 <= status_code < 300 else False,
        "payload": payload,
        "created_at": datetime.datetime.now(),
        "extra": extra if extra else {}
    }

    return {
        "statusCode": status_code,
        "body": json.dumps(base_body, cls=DecimalEncoder)
    }

def error_response(payload: list or dict, status_code=400, extra=None) -> dict:

    base_body = {
        "status": True if 200 <= status_code < 300 else False,
        "error": payload,
        "created_at": datetime.datetime.now(),
        "extra": extra if DEBUG else {}
    }

    return {
        "statusCode": status_code,
        "body": json.dumps(base_body, cls=DecimalEncoder)
    }


def lambda_response(message) -> dict:
    return {"message": message}


