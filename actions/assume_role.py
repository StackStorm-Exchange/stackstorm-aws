from datetime import date, datetime
import json

import boto3

from st2actions.runners.pythonrunner import Action


# pylint: disable=too-few-public-methods
def json_serial(obj):
    if isinstance(obj, (datetime, date)):
        serial = obj.isoformat()
        return serial
    raise TypeError("Type %s not serializable" % type(obj))


# pylint: disable=too-few-public-methods
class Boto3AssumeRoleRunner(Action):
    def run(
            self, role_arn, role_session_name, policy,
            duration, external_id, serial_number, token_code):
        client = boto3.client('sts')
        kwargs = {}
        kwargs['RoleArn'] = role_arn
        kwargs['RoleSessionName'] = role_session_name
        kwargs['DurationSeconds'] = duration
        if policy is not None:
            kwargs['Policy'] = policy

        if external_id is not None:
            kwargs['ExternalId'] = external_id

        if serial_number is not None:
            kwargs['SerialNumber'] = serial_number

        if token_code is not None:
            kwargs['TokenCode'] = token_code

        response = client.assume_role(**kwargs)
        response = json.loads(json.dumps(response, default=json_serial))
        return (True, response)
