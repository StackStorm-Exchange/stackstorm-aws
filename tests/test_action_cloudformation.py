import mock

from aws_base_action_test_case import AWSBaseActionTestCase

from boto.cloudformation.connection import CloudFormationConnection


class CloudFormationTestCase(AWSBaseActionTestCase):
    action_cls = CloudFormationConnection

    @mock.patch.object(CloudFormationConnection, 'get_path', mock.Mock(return_value='hoge'))
    def test_connect(self):
        self._params['action'] = 'get_path'

        action = self.get_action_instance(self.full_config)
        result = action.run(**self._params)

        self.assertEqual(result, 'hoge')
