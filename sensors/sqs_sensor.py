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
# limitations under the License.
"""
This is generic SQS Sensor using boto3 api to fetch messages from sqs queue.
After receiving a message it's content is passed as payload to a trigger 'aws.sqs_new_message'
This sensor can be configured either by using config.yaml within a pack or by creating
following values in datastore:
    - aws.input_queues (list queues as comma separated string: first_queue,second_queue)
    - aws.aws_access_key_id
    - aws.aws_secret_access_key
    - aws.region
    - aws.max_number_of_messages (must be between 1 - 10)
For configuration in config.yaml with config like this
    setup:
      aws_access_key_id:
      aws_access_key_id:
      region:
    sqs_sensor:
      input_queues:
        - first_queue
        - second_queue
    sqs_other:
        max_number_of_messages: 1
If any value exist in datastore it will be taken instead of any value in config.yaml
"""

import six
import json
import sys

from boto3.session import Session
from botocore.exceptions import ClientError
from botocore.exceptions import NoRegionError
from botocore.exceptions import NoCredentialsError
from botocore.exceptions import EndpointConnectionError
from collections import defaultdict

from st2reactor.sensor.base import PollingSensor


class AWSSQSSensor(PollingSensor):
    def __init__(self, sensor_service, config=None, poll_interval=5):
        super(AWSSQSSensor, self).__init__(sensor_service=sensor_service, config=config,
                                           poll_interval=poll_interval)

    def setup(self):
        self._logger = self._sensor_service.get_logger(name=self.__class__.__name__)

        self.account_id = None
        self.default_session = None
        self.default_credentials = ()
        self.credentials = {}
        self.sessions = {}
        self.cross_roles = {}
        self.sqs_res = defaultdict(dict)

    def poll(self):
        # setting SQS ServiceResource object from the parameter of datastore or configuration file
        self._may_setup_sqs()

        for queue in self.input_queues:
            account_id, region = self._get_info(queue)

            while True:
                try:
                    msgs = self._receive_messages(queue=self._get_queue(queue, account_id, region),
                                                  num_messages=self.max_number_of_messages)
                except ClientError as e:
                    if e.response['Error']['Code'] == 'ExpiredToken':
                        self._setup_multiaccount_session(account_id)
                        continue
                    raise
                break

            for msg in msgs:
                if msg:
                    payload = {"queue": six.moves.urllib.parse.urlunparse(queue),
                               "account_id": account_id,
                               "region": region,
                               "body": json.loads(msg.body)}
                    self._sensor_service.dispatch(trigger="aws.sqs_new_message", payload=payload)
                    msg.delete()

    def cleanup(self):
        pass

    def add_trigger(self, trigger):
        # This method is called when trigger is created
        pass

    def update_trigger(self, trigger):
        # This method is called when trigger is updated
        pass

    def remove_trigger(self, trigger):
        pass

    def _get_config_entry(self, key, prefix=None):
        ''' Get configuration values either from Datastore or config file. '''
        config = self.config
        if prefix:
            config = self.config.get(prefix, {})

        value = self._sensor_service.get_value('aws.%s' % (key), local=False)
        if not value:
            value = config.get(key, None)

        if not value and config.get('setup', None):
            value = config['setup'].get(key, None)

        return value

    def _may_setup_sqs(self):
        self.access_key_id = self._get_config_entry('aws_access_key_id')
        self.secret_access_key = self._get_config_entry('aws_secret_access_key')
        self.aws_region = self._get_config_entry('region')
        self.max_number_of_messages = self._get_config_entry('max_number_of_messages',
                                                             prefix='sqs_other')

        if not self.account_id:
            self._setup_session()

        queues = self._get_config_entry(key='input_queues', prefix='sqs_sensor')
        # XXX: This is a hack as from datastore we can only receive a string while
        # from config.yaml we can receive a list
        if isinstance(queues, six.string_types):
            self.input_queues = [six.moves.urllib.parse.urlparse(x.strip()) for x in
                                 queues.split(',')]
        elif isinstance(queues, list):
            self.input_queues = [six.moves.urllib.parse.urlparse(queue) for queue in queues]
        else:
            self.input_queues = []

        # checker configuration is update, or not
        def _is_same_credentials(session, account_id, credentials):
            if not session:
                return False

            c = session.get_credentials()
            return c is not None and \
                c.access_key == credentials[0] and \
                c.secret_key == credentials[1] and \
                (account_id == self.account_id or c.token == credentials[2])

        # Build a map between 'account_id' and its 'role arn' by parsing the matching config entry
        self.cross_roles = {
            arn.split(':')[4]: arn
            for arn in self._get_config_entry('roles', 'sqs_sensor') or []
        }
        required_accounts = {self._get_info(queue)[0] for queue in self.input_queues}

        if not self.default_session or \
                not _is_same_credentials(self.default_session, self.account_id,
                                         self.default_credentials):
            self._setup_session()

        for account_id in required_accounts:
            if account_id != self.account_id and account_id not in self.cross_roles:
                continue

            session = self.sessions.get(account_id)
            if account_id == self.account_id and self.account_id not in self.cross_roles:
                if not _is_same_credentials(session, account_id, self.default_credentials):
                    self._setup_session()
                    self.sessions[self.account_id] = self.default_session
            elif account_id not in self.credentials or \
                    not _is_same_credentials(session, account_id, self.credentials[account_id]):
                self._setup_multiaccount_session(account_id)

    def _setup_session(self):
        ''' Setup Boto3 session '''
        session = Session(aws_access_key_id=self.access_key_id,
                          aws_secret_access_key=self.secret_access_key)

        if not self.account_id:
            # pylint: disable=no-member
            self.account_id = session.client('sts').get_caller_identity().get('Account')
            self.default_credentials = (self.access_key_id, self.secret_access_key, None)

        self.default_session = session
        self.sqs_res.pop(self.account_id, None)

    def _setup_multiaccount_session(self, account_id):
        ''' Assume role and setup session for the cross-account capability'''
        try:
            # pylint: disable=no-member
            assumed_role = self.default_session.client('sts').assume_role(
                RoleArn=self.cross_roles[account_id],
                RoleSessionName='StackStormEvents'
            )
        except ClientError:
            self._logger.error('Could not assume role on %s', account_id)
            return

        self.credentials[account_id] = (assumed_role["Credentials"]["AccessKeyId"],
                                        assumed_role["Credentials"]["SecretAccessKey"],
                                        assumed_role["Credentials"]["SessionToken"])

        session = Session(
            aws_access_key_id=self.credentials[account_id][0],
            aws_secret_access_key=self.credentials[account_id][1],
            aws_session_token=self.credentials[account_id][2]
        )
        self.sessions[account_id] = session
        self.sqs_res.pop(account_id, None)

    def _setup_sqs(self, session, account_id, region):
        ''' Setup SQS resources'''
        if region in self.sqs_res[account_id]:
            return self.sqs_res[account_id][region]

        try:
            self.sqs_res[account_id][region] = session.resource('sqs', region_name=region)
            return self.sqs_res[account_id][region]
        except NoRegionError:
            self._logger.error("The specified region '%s' for account %s is invalid.",
                               region, account_id)

    def _get_info(self, queue):
        ''' Retrieve the account ID and region from the queue URL '''
        # Pull default values from previous configuration
        account_id = self.account_id
        aws_region = self.aws_region

        # Netloc will be empty if the queue is just a name
        if queue.netloc:
            try:
                account_id = queue.path.split('/')[1]
            except IndexError as e:
                six.reraise(type(e), type(e)(
                    "Queue URL must contain the account ID as the first part of the path, "
                    "eg: https://sqs.<aws_region>.amazonaws.com/<account_id>/<queue_name>"),
                    sys.exc_info()[2])
            else:
                self._logger.debug("Using %s as account_id", account_id)

            try:
                aws_region = queue.netloc.split('.')[1]
            except IndexError as e:
                six.reraise(type(e), type(e)(
                    "Queue URL must contain the AWS region, "
                    "eg: https://sqs.<aws_region>.amazonaws.com/..."),
                    sys.exc_info()[2])
            else:
                self._logger.debug("Using %s as the AWS region", aws_region)

        return account_id, aws_region

    def _get_queue(self, queue, account_id, region):
        ''' Fetch QUEUE by its name or URL and create new one if queue doesn't exist '''
        if account_id not in self.sessions:
            self._logger.error('Session for account id %s does not exist', account_id)
            return None

        sqs_res = self._setup_sqs(self.sessions[account_id], account_id, region)
        if sqs_res is None:
            return None

        try:
            if queue.netloc:
                return sqs_res.Queue(six.moves.urllib.parse.urlunparse(queue))
            return sqs_res.get_queue_by_name(QueueName=queue.path.split('/')[-1])
        except ClientError as e:
            if e.response['Error']['Code'] == 'AWS.SimpleQueueService.NonExistentQueue':
                self._logger.warning("SQS Queue: %s doesn't exist, creating it.", queue)
                return sqs_res.create_queue(QueueName=queue.path.split('/')[-1])
            elif e.response['Error']['Code'] == 'InvalidClientTokenId':
                self._logger.warning("Couldn't operate sqs because of invalid credential config")
            else:
                raise
        except NoCredentialsError:
            self._logger.warning("Couldn't operate sqs because of invalid credential config")
        except EndpointConnectionError as e:
            self._logger.warning(e)

    def _receive_messages(self, queue, num_messages, wait_time=2):
        ''' Receive a message from queue and return it. '''
        if queue:
            return queue.receive_messages(WaitTimeSeconds=wait_time,
                                          MaxNumberOfMessages=num_messages)
        else:
            return []
