# Licensed to the StackStorm, Inc ('StackStorm') under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and

import mock
import yaml

from st2tests.base import BaseActionTestCase
from botocore.exceptions import ClientError


class AWSBaseActionTestCase(BaseActionTestCase):
    __test__ = False

    class MockStsClient(object):
        def __init__(self):
            self.meta = mock.Mock(service_model={})

        def get_caller_identity(self):
            ci = mock.Mock()
            ci.get = lambda attribute: '111222333444' if attribute == 'Account' else None
            return ci

        def assume_role(self, RoleArn, RoleSessionName):
            return {
                'Credentials': {
                    'AccessKeyId': 'access_key_id_example',
                    'SecretAccessKey': 'secret_access_key_example',
                    'SessionToken': 'session_token_example'
                }
            }

    class MockStsClientRaiseClientError(MockStsClient):
        def assume_role(self, RoleArn, RoleSessionName):
            raise ClientError({'Error': {'Code': 'AccessDenied'}}, 'sqs_test')

    def setUp(self):
        super(AWSBaseActionTestCase, self).setUp()

        self._full_config = self.load_yaml('full.yaml')
        self._multiaccount_config = self.load_yaml('multiaccount.yaml')

    def load_yaml(self, filename):
        return yaml.safe_load(self.get_fixture_content(filename))

    @property
    def full_config(self):
        return self._full_config

    @property
    def multiaccount_config(self):
        return self._multiaccount_config
