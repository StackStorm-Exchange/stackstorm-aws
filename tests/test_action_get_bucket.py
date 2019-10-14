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

from aws_base_action_test_case import AWSBaseActionTestCase

from boto.s3.connection import S3Connection
from boto.s3.bucket import Bucket
from boto3.session import Session

from run import ActionManager
from datetime import datetime


class MockBucket(Bucket):
    def __init__(self, set_date=True, **kwargs):
        super(MockBucket, self).__init__(**kwargs)

        if set_date:
            self.creation_date = datetime.now().isoformat()


class GetBucketTestCase(AWSBaseActionTestCase):
    __test__ = True
    action_cls = ActionManager

    _MOCK_BUCKETS = [
        MockBucket(name='foo'),
        MockBucket(name='bar'),
    ]

    def setUp(self):
        super(GetBucketTestCase, self).setUp()

        # default params of each actions
        self._params = {
            'headers': None,
            'module_path': 'boto.s3.connection',
            'cls': 'S3Connection',
        }

    @mock.patch.object(Session, 'client',
                       mock.Mock(return_value=AWSBaseActionTestCase.MockStsClient()))
    @mock.patch.object(S3Connection, 'get_all_buckets',
                       mock.MagicMock(return_value=_MOCK_BUCKETS))
    def _get_all_buckets(self, config, additional_params):
        self._params['action'] = 'get_all_buckets'
        self._params.update(additional_params)

        action = self.get_action_instance(config)
        result = action.run(**self._params)

        self.assertIsNotNone(result)
        self.assertTrue(isinstance(result, list))
        self.assertEqual(len(result), len(self._MOCK_BUCKETS))

    def test_get_all_buckets_full_config(self):
        self._get_all_buckets(self.full_config, {})

    def test_get_all_buckets_multiaccount_config(self):
        params = {
            'account_id': '345678901223',
            'region': 'us-east-1'
        }
        self._get_all_buckets(self.multiaccount_config, params)

    @mock.patch.object(Session, 'client',
                       mock.Mock(return_value=AWSBaseActionTestCase.MockStsClient()))
    @mock.patch.object(S3Connection, 'get_bucket',
                       mock.MagicMock(return_value=MockBucket(False, name='foo')))
    def _get_bucket(self, config, additional_params):
        self._params['action'] = 'get_bucket'
        self._params['validate'] = True
        self._params.update(additional_params)

        action = self.get_action_instance(config)
        result = action.run(**self._params)

        self.assertIsNotNone(result)
        self.assertEqual(len(result), 1)
        self.assertTrue(isinstance(result[0], dict))
        self.assertEqual(result[0]['name'], 'foo')

    def test_get_bucket_full_config(self):
        self._get_bucket(self.full_config, {})

    def test_get_bucket_multiaccount_config(self):
        params = {
            'account_id': '345678901223',
            'region': 'us-east-1'
        }
        self._get_bucket(self.multiaccount_config, params)
