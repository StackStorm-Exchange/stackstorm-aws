import json
import boto3

from st2common.runners.base_action import Action
from lib.util import json_serial


# pylint: disable=too-few-public-methods
class Boto3ActionRunner(Action):
    def run(self, service, region, action_name, credentials, params):
        client = None
        response = None

        if credentials is not None:
            session = boto3.Session(
                aws_access_key_id=credentials['Credentials']['AccessKeyId'],
                aws_secret_access_key=credentials['Credentials']['SecretAccessKey'],
                aws_session_token=credentials['Credentials']['SessionToken'])
            client = session.client(service, region_name=region)
        else:
            client = boto3.client(service, region_name=region)

        if client is None:
            return (False, 'boto3 client creation failed')

        if params is not None:
            response = getattr(client, action_name)(**params)
        else:
            response = getattr(client, action_name)()

        response = json.loads(json.dumps(response, default=json_serial))
        return (True, response)
