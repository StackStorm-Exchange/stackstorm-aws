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
from boto3.session import Session
from botocore.exceptions import ClientError
from botocore.exceptions import NoRegionError
from botocore.exceptions import NoCredentialsError
from botocore.exceptions import EndpointConnectionError

from st2reactor.sensor.base import Sensor


class AWSSQSServiceSensor(Sensor):
    def __init__(self, sensor_service, config=None):
        super(AWSSQSServiceSensor, self).__init__(sensor_service=sensor_service, config=config)

    def setup(self):
        self._logger = self._sensor_service.get_logger(name=self.__class__.__name__)

        self.session = None
        self.sqs_res = None

    def run(self):
        # setting SQS ServiceResource object from the parameter of datastore or configuration file
        self._may_setup_sqs()

        while True:
            for queue in self.input_queues:
                msgs = self._receive_messages(queue=self._get_queue_by_name(queue),
                                            num_messages=self.max_number_of_messages)
                for msg in msgs:
                    if msg:
                        payload = {"queue": queue, "body": json.loads(msg.body)}
                        self._sensor_service.dispatch(trigger="aws.sqs_new_message",
                                                      payload=payload)
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
            config = self._config.get(prefix, {})

        value = self._sensor_service.get_value('aws.%s' % (key), local=False)
        if not value:
            value = config.get(key, None)

        if not value and config.get('setup', None):
            value = config['setup'].get(key, None)

        return value

    def _may_setup_sqs(self):
        queues = self._get_config_entry(key='input_queues', prefix='sqs_sensor')

        # XXX: This is a hack as from datastore we can only receive a string while
        # from config.yaml we can receive a list
        if isinstance(queues, six.string_types):
            self.input_queues = [x.strip() for x in queues.split(',')]
        elif isinstance(queues, list):
            self.input_queues = queues
        else:
            self.input_queues = []

        self.aws_access_key = self._get_config_entry('aws_access_key_id')
        self.aws_secret_key = self._get_config_entry('aws_secret_access_key')
        self.aws_region = self._get_config_entry('region')

        self.max_number_of_messages = self._get_config_entry('max_number_of_messages',
                                                             prefix='sqs_other')

        # checker configuration is update, or not
        def _is_same_credentials():
            c = self.session.get_credentials()
            return c is not None and \
                c.access_key == self.aws_access_key and \
                c.secret_key == self.aws_secret_key and \
                self.session.region_name == self.aws_region

        if self.session is None or not _is_same_credentials():
            self._setup_sqs()

    def _setup_sqs(self):
        ''' Setup Boto3 structures '''
        self._logger.debug('Setting up SQS resources')
        self.session = Session(aws_access_key_id=self.aws_access_key,
                               aws_secret_access_key=self.aws_secret_key,
                               region_name=self.aws_region)

        try:
            self.sqs_res = self.session.resource('sqs')
        except NoRegionError:
            self._logger.warning("The specified region '%s' is invalid", self.aws_region)

    def _get_queue_by_name(self, queueName):
        ''' Fetch QUEUE by it's name create new one if queue doesn't exist '''
        try:
            return self.sqs_res.get_queue_by_name(QueueName=queueName)
        except ClientError as e:
            if e.response['Error']['Code'] == 'AWS.SimpleQueueService.NonExistentQueue':
                self._logger.warning("SQS Queue: %s doesn't exist, creating it.", queueName)
                return self.sqs_res.create_queue(QueueName=queueName)
            elif e.response['Error']['Code'] == 'InvalidClientTokenId':
                self._logger.warning("Cloudn't operate sqs because of invalid credential config")
            else:
                raise
        except NoCredentialsError as e:
            self._logger.warning("Cloudn't operate sqs because of invalid credential config")
        except EndpointConnectionError as e:
            self._logger.warning(e)

    def _receive_messages(self, queue, num_messages, wait_time=2):
        ''' Receive a message from queue and return it. '''
        if queue:
            return queue.receive_messages(WaitTimeSeconds=wait_time,
                                          MaxNumberOfMessages=num_messages)
        else:
            return []
