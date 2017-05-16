import re
import sys

from aws_base_action_test_case import AWSBaseActionTestCase
from run import ActionManager


class MockStderr(object):
    def __init__(self):
        self.messages = []

    def write(self, output):
        self.messages.append(output)

    def flush(self):
        pass


class ActionInitializationTestCase(AWSBaseActionTestCase):
    __test__ = True
    action_cls = ActionManager

    def test_get_action_with_full_config(self):
        action = self.get_action_instance(self.full_config)

        self.assertEqual(action.credentials['region'], 'us-west-1')

    def test_get_action_with_old_config(self):
        action = self.get_action_instance(self.load_yaml('old.yaml'))

        self.assertEqual(action.credentials['region'], 'us-east-1')

    def test_get_action_with_blank_config(self):
        action = self.get_action_instance({})

        self.assertEqual(action.credentials['region'], None)

    def test_get_action_with_invalid_config(self):
        config = self.full_config
        mock_stderr = MockStderr()

        # set invalid parameter
        config['st2_user_data'] = 'hogefuga'

        # save stderr object
        stderr_orig = sys.stderr
        sys.stderr = mock_stderr

        action = self.get_action_instance(config)

        # retrieve original stderr object
        sys.stderr = stderr_orig

        self.assertTrue(len(mock_stderr.messages) > 0)
        self.assertTrue(re.match(r".*No such file or directory.*hogefuga", mock_stderr.messages[0]))
        self.assertEqual(action.credentials['region'], 'us-west-1')
