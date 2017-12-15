import re
import sys

from aws_base_action_test_case import AWSBaseActionTestCase
from run import ActionManager


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
