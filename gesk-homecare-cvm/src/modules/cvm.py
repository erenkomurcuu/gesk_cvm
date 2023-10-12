from botocore.exceptions import ClientError
import boto3
import requests
import json
from ..utils import Constants
from ..utils.Response import make_response, error_response
import hashlib
import decimal

dynamodb = boto3.resource('dynamodb', region_name=Constants.AWS_REGION)
iot_data = boto3.client('iot-data', region_name=Constants.AWS_REGION, endpoint_url="https://"+Constants.IOT_CONNECTION_ENDPOINT)
iot = boto3.client('iot', region_name=Constants.AWS_REGION)


class DownloadError(BaseException):
    pass


def _retreive_device_information(device_serial):
    table = dynamodb.Table(Constants.DEVICE_TABLE)

    return table.query(
        KeyConditionExpression="deviceSerial = :a",
        ExpressionAttributeValues={
            ":a": device_serial
        }
    )


def _update_certificate_information(device_serial, certificate):
    table = dynamodb.Table(Constants.DEVICE_TABLE)
    return table.update_item(
        Key={"deviceSerial": device_serial},
        UpdateExpression="set certInfo = :r, isActivated = :t, allowGetCerts = :a ",
        ExpressionAttributeValues={
            ":r": certificate,
            ":t": 1,
            ":a": 0,
        },
        ReturnValues="UPDATED_NEW"
    )


def _renew_certificate_information(device_serial, certificate):
    table = dynamodb.Table(Constants.DEVICE_TABLE)
    return table.update_item(
        Key={"deviceSerial": device_serial},
        UpdateExpression="set certInfo = :r, allowGetCerts = :a",
        ExpressionAttributeValues={
            ":r": certificate,
            ":a": 0
        },
        ReturnValues="UPDATED_NEW"
    )


def _download_root_ca():
    response = requests.get(Constants.IOT_ROOT_CA_ENDPOINT)
    if response.status_code == 200:
        return response.text
    else:
        raise DownloadError("Unable to download RootCa")
def decimal_default(obj):
    if isinstance(obj, decimal.Decimal):
        return int(obj)
    raise TypeError


def activate_device(device_serial, device_token):
    try:
        # Retrieve Device & Check For Status
        try:
            device = _retreive_device_information(device_serial)

        except ClientError:
            return error_response("")
        if len(device['Items']) <= 0:
            return error_response({"message": "Device Not Found"}, 400)
        else:
            if device['Items'][0]['isActivated'] == 1:
                return error_response({"message": "Device Already Activated"}, 400)
            if device['Items'][0]['isEnabled'] == 0:
                return error_response({"message": "Device Disabled"}, 400)
            if device['Items'][0]['deviceToken'] != device_token:
                return error_response({"message": "Invalid Token"}, 400)

            # Create Certificates For Device
            certificate = iot.create_keys_and_certificate(setAsActive=True or False)
            if certificate:

                iot.attach_policy(policyName=Constants.IOT_DEVICE_POLICY, target=certificate['certificateArn'])
                device_policy = iot.create_policy(
                    policyName=f'PairingPolicy_{device_serial}',
                    policyDocument=json.dumps(Constants.device_cognito_policy(device_serial)),
                )

                attribute_payload = {
                    "attributes": {
                        "PairingPolicy": device_policy['policyName']
                    },
                    "merge": True or False
                }

                thing = iot.create_thing(thingName=device_serial, attributePayload=attribute_payload)
                iot.attach_thing_principal(principal=certificate['certificateArn'], thingName=device_serial)


                root_certificate = _download_root_ca()

                if certificate and root_certificate:
                    return_values = certificate
                    return_values['rootCa'] = root_certificate

                    _update_certificate_information(device_serial, certificate)
                    
                    # apply initial shadow
                    if 'initialShadow' in device['Items'][0]:
                        if type(device['Items'][0])=="str":
                            desired_shadow = json.loads(device['Items'][0]['initialShadow'])
                        else:
                            desired_shadow = json.loads(json.dumps(device['Items'][0]['initialShadow'], default=decimal_default))
                
                        iot_data.update_thing_shadow(
                            thingName=device_serial,
                            payload=json.dumps({
                                "state": {
                                    "desired": desired_shadow
                                }
                            })
                        )

                    response = {
                        "endpoint": Constants.IOT_CONNECTION_ENDPOINT,
                        "certificates": {
                            "certificatePem": return_values['certificatePem'],
                            "rootCa": return_values['rootCa']
                        },
                        "keyPair": {
                            "publicKey": return_values['keyPair']['PublicKey'],
                            "privateKey": return_values['keyPair']['PrivateKey']
                        }
                    }

                    return make_response(response)

            else:
                return error_response({"message": "Unable To Create Device Certificates"}, 400)

    except ClientError as err:
        return error_response({"message": "Internal AWS Service Error"}, 500, {"exc_info": str(err)})
    except DownloadError as err:
        return error_response({"message": "Unable to Download AWS Root Certificate"}, 400, {"exc_info": str(err)})
    except Exception as global_exception:
        return error_response({"message": "Internal Service Error"}, 500, {"exc_info": str(global_exception)})


def renew_device_certificates(device_serial, device_token):
    try:
        device = _retreive_device_information(device_serial)
        if device['Items'][0]['allowGetCerts'] == 0:
            return error_response({"message": "Device Not Allowed To Renew Certificates"}, 400)
        if device['Items'][0]['deviceToken'] != device_token:
            return error_response({"message": "Invalid Token"}, 400)

        thing_principal = iot.list_thing_principals(
            thingName=device_serial
        )

        if len(thing_principal['principals']) > 0:
            old_certificate_arn = thing_principal['principals'][0]
            old_certificate_id = thing_principal['principals'][0].split('/')[1]

            new_certificate = iot.create_keys_and_certificate(setAsActive=True)
            if new_certificate:
                target = new_certificate['certificateArn']

                iot.update_certificate(
                    certificateId=old_certificate_id,
                    newStatus='INACTIVE'
                )
                iot.detach_thing_principal(principal=old_certificate_arn, thingName=device_serial)

                iot.delete_certificate(
                    certificateId=old_certificate_id,
                    forceDelete=True
                )

                iot.attach_policy(policyName=Constants.IOT_DEVICE_POLICY, target=target)
                iot.attach_thing_principal(principal=new_certificate['certificateArn'], thingName=device_serial)

        else:
            return error_response({"message": "Internal AWS Service Error"}, 500)

        _renew_certificate_information(device_serial, new_certificate)
        root_certificate = _download_root_ca()

        response = {
            "endpoint": Constants.IOT_CONNECTION_ENDPOINT,
            "certificates": {
                "certificatePem": new_certificate['certificatePem'],
                "rootCa": root_certificate
            },
            "keyPair": {
                "publicKey": new_certificate['keyPair']['PublicKey'],
                "privateKey": new_certificate['keyPair']['PrivateKey'],
            }
        }

        return make_response(response)

    except ClientError as exc:
        return error_response({"message": "Internal AWS Service Error"}, 500, {"exc_info": str(exc)})
    except Exception as global_exception:
        return error_response({"message": "Internal Service Error"}, 500, {"exc_info": str(global_exception)})