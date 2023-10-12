import os

AWS_REGION = os.getenv("AWS_SERVICE_REGION", "us-east-1")
IOT_DEVICE_POLICY = os.getenv("IOT_DEVICE_POLICY", "IoTSingleDevicePolicy")
IOT_ROOT_CA_ENDPOINT = os.getenv("IOT_ROOT_CA_ENDPOINT")
IOT_CONNECTION_ENDPOINT = os.getenv("IOT_CONNECTION_ENDPOINT")
DEBUG = os.getenv("DEBUG", False)
DEVICE_TABLE = os.getenv("DEVICE_TABLE")


def device_cognito_policy(device_serial):
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "iot:Connect"
                ],
                "Resource": [
                    "*"
                ],
                "Condition": {
                    "Bool": {
                        "iot:Connection.Thing.IsAttached": [
                            "true"
                        ]
                    }
                }
            },
            {
                "Effect": "Allow",
                "Action": [
                    "iot:Publish"
                ],
                "Resource": [
                    f"arn:aws:iot:eu-west-1:376652500674:topic/sub/{device_serial}/*",
                    f"arn:aws:iot:eu-west-1:376652500674:topic/$aws/things/{device_serial}/shadow/*"
                ]
            },
            {
                "Effect": "Allow",
                "Action": [
                    "iot:Subscribe"
                ],
                "Resource": [
                    f"arn:aws:iot:eu-west-1:376652500674:topicfilter/pub/{device_serial}/*",
                    f"arn:aws:iot:eu-west-1:376652500674:topicfilter/$aws/things/{device_serial}/shadow/*"
                ]
            },
            {
                "Effect": "Allow",
                "Action": [
                    "iot:Receive"
                ],
                "Resource": [
                    f"arn:aws:iot:eu-west-1:376652500674:topic/pub/{device_serial}/*",
                    f"arn:aws:iot:eu-west-1:376652500674:topic/$aws/things/{device_serial}/shadow/*"
                ]
            }
        ]
    }
