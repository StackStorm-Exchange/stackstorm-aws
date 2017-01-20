import mock

from run import ActionManager
from aws_base_action_test_case import AWSBaseActionTestCase

from boto.cloudformation.connection import CloudFormationConnection


class CloudFormationTestCase(AWSBaseActionTestCase):
    __test__ = True
    action_cls = ActionManager

    def setUp(self):
        super(CloudFormationTestCase, self).setUp()
        self._params = {
            'module_path': 'boto.cloudformation.connection',
            'cls': 'CloudFormationConnection',
        }

    @mock.patch.object(CloudFormationConnection, 'get_path', mock.Mock(return_value='hoge'))
    def test_connection(self):
        self._params['action'] = 'get_path'

        action = self.get_action_instance(self.full_config)
        result = action.run(**self._params)

        self.assertEqual(result, ['hoge'])
