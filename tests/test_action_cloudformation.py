import mock

from run import ActionManager
from boto3.session import Session
from aws_base_action_test_case import AWSBaseActionTestCase

from boto.cloudformation.connection import CloudFormationConnection
from botocore.exceptions import ClientError


class CloudFormationTestCase(AWSBaseActionTestCase):
    __test__ = True
    action_cls = ActionManager

    def setUp(self):
        super(CloudFormationTestCase, self).setUp()
        self._params = {
            'module_path': 'boto.cloudformation.connection',
            'cls': 'CloudFormationConnection',
        }

    @mock.patch.object(Session, 'client',
                       mock.Mock(return_value=AWSBaseActionTestCase.MockStsClient()))
    @mock.patch.object(CloudFormationConnection, 'get_path', mock.Mock(return_value='hoge'))
    def _connection(self, config, additional_params):
        self._params['action'] = 'get_path'
        self._params.update(additional_params)

        action = self.get_action_instance(config)
        result = action.run(**self._params)

        self.assertEqual(result, ['hoge'])

    def test_connection_full_config(self):
        self._connection(self.full_config, {})

    def test_connection_multiaccount_config(self):
        params = {
            'account_id': '345678901223',
            'region': 'us-east-1'
        }
        self._connection(self.multiaccount_config, params)

    @mock.patch.object(Session, 'client', mock.Mock(
        return_value=AWSBaseActionTestCase.MockStsClientRaiseClientError()))
    @mock.patch.object(CloudFormationConnection, 'get_path', mock.Mock(return_value='hoge'))
    def test_fails_assuming_role(self):
        self._params.update({
            'action': 'get_path',
            'account_id': '345678901223',
            'region': 'us-east-1'
        })
        action = self.get_action_instance(self.multiaccount_config)
        self.assertRaises(ClientError, lambda: action.run(**self._params))

    @mock.patch.object(Session, 'client',
                       mock.Mock(return_value=AWSBaseActionTestCase.MockStsClient()))
    @mock.patch.object(CloudFormationConnection, 'get_path', mock.Mock(return_value='hoge'))
    def test_fails_with_missing_arn_multiaccount_config(self):
        self._params.update({
            'action': 'get_path',
            'account_id': '345678901223',
            'region': 'us-east-1'
        })
        action = self.get_action_instance(self.full_config)
        self.assertRaises(KeyError, lambda: action.run(**self._params))
