import mock
import yaml

from boto3.session import Session
from botocore.exceptions import ClientError
from botocore.exceptions import NoCredentialsError
from botocore.exceptions import EndpointConnectionError
from st2tests.base import BaseSensorTestCase

from sqs_sensor import AWSSQSSensor


class SQSSensorTestCase(BaseSensorTestCase):
    sensor_cls = AWSSQSSensor

    class MockResource(object):
        def __init__(self, msgs=[]):
            self.msgs = msgs

        def get_queue_by_name(self, **kwargs):
            return SQSSensorTestCase.MockQueue(self.msgs)

    class MockResourceRaiseClientError(object):
        def __init__(self, error_code=''):
            self.error_code = error_code

        def get_queue_by_name(self, **kwargs):
            raise ClientError({'Error': {'Code': self.error_code}}, 'sqs_test')

    class MockResourceRaiseNoCredentialsError(object):
        def get_queue_by_name(self, **kwargs):
            raise NoCredentialsError()

    class MockResourceRaiseEndpointConnectionError(object):
        def get_queue_by_name(self, **kwargs):
            raise EndpointConnectionError(endpoint_url='')

    class MockQueue(object):
        def __init__(self, msgs=[]):
            self.dummy_messages = [SQSSensorTestCase.MockMessage(x) for x in msgs]

        def receive_messages(self, **kwargs):
            return self.dummy_messages

    class MockMessage(object):
        def __init__(self, body=None):
            self.body = body

        def delete(self):
            return mock.MagicMock(return_value=None)

    def setUp(self):
        super(SQSSensorTestCase, self).setUp()

        self.full_config = self.load_yaml('full.yaml')
        self.blank_config = self.load_yaml('blank.yaml')

    def load_yaml(self, filename):
        return yaml.safe_load(self.get_fixture_content(filename))

    def test_poll_with_blank_config(self):
        sensor = self.get_sensor_instance(config=self.blank_config)

        sensor.setup()
        sensor.poll()

        self.assertEqual(self.get_dispatched_triggers(), [])

    @mock.patch.object(Session, 'resource', mock.Mock(return_value=MockResource()))
    def test_poll_without_message(self):
        sensor = self.get_sensor_instance(config=self.full_config)

        sensor.setup()
        sensor.poll()

        self.assertEqual(self.get_dispatched_triggers(), [])

    @mock.patch.object(Session, 'resource', mock.Mock(return_value=MockResource(['foo'])))
    def test_poll_with_message(self):
        sensor = self.get_sensor_instance(config=self.full_config)

        sensor.setup()
        sensor.poll()

        self.assertTriggerDispatched(trigger='aws.sqs_new_message')
        self.assertNotEqual(self.get_dispatched_triggers(), [])

    @mock.patch.object(Session, 'resource', mock.Mock(return_value=MockResource(['foo'])))
    def test_set_input_queues_config_dynamically(self):
        sensor = self.get_sensor_instance(config=self.blank_config)
        sensor.setup()

        # set credential mock to prevent sending request to AWS
        mock_credentials = mock.Mock()
        mock_credentials.access_key = sensor._get_config_entry('aws_access_key_id')
        mock_credentials.secret_key = sensor._get_config_entry('aws_secret_access_key')
        Session.get_credentials = mock_credentials

        # set test value to datastore
        sensor._sensor_service.set_value('aws.input_queues', 'hoge', local=False)
        sensor.poll()

        # update input_queues to check this is reflected
        sensor._sensor_service.set_value('aws.input_queues', 'fuga,puyo', local=False)
        sensor.poll()

        contexts = self.get_dispatched_triggers()
        self.assertNotEqual(contexts, [])
        self.assertTriggerDispatched(trigger='aws.sqs_new_message')

        # get message from queue 'hoge', 'fuga' then 'puyo'
        self.assertEqual([x['payload']['queue'] for x in contexts], ['hoge', 'fuga', 'puyo'])

    @mock.patch.object(Session, 'resource', mock.Mock(return_value=MockResource(['foo'])))
    def test_set_input_queues_config_with_list(self):
        # set 'input_queues' config with list type
        config = self.full_config
        config['sqs_sensor']['input_queues'] = ['foo', 'bar']

        sensor = self.get_sensor_instance(config=config)
        sensor.setup()
        sensor.poll()

        contexts = self.get_dispatched_triggers()
        self.assertNotEqual(contexts, [])
        self.assertTriggerDispatched(trigger='aws.sqs_new_message')
        self.assertEqual([x['payload']['queue'] for x in contexts], ['foo', 'bar'])

    @mock.patch.object(Session, 'resource',
                       mock.Mock(return_value=MockResourceRaiseClientError('InvalidClientTokenId')))
    def test_fails_with_invalid_token(self):
        sensor = self.get_sensor_instance(config=self.full_config)

        sensor.setup()
        sensor.poll()

        self.assertEqual(self.get_dispatched_triggers(), [])

    @mock.patch.object(Session, 'resource',
                       mock.Mock(return_value=MockResourceRaiseNoCredentialsError()))
    def test_fails_without_credentials(self):
        sensor = self.get_sensor_instance(config=self.full_config)

        sensor.setup()
        sensor.poll()

        self.assertEqual(self.get_dispatched_triggers(), [])

    @mock.patch.object(Session, 'resource',
                       mock.Mock(return_value=MockResourceRaiseEndpointConnectionError()))
    def test_fails_with_invalid_region(self):
        sensor = self.get_sensor_instance(config=self.full_config)

        sensor.setup()
        sensor.poll()

        self.assertEqual(self.get_dispatched_triggers(), [])
