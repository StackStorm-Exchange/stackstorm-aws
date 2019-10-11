import mock
import yaml

from boto3.session import Session
from botocore.exceptions import ClientError
from botocore.exceptions import NoCredentialsError
from botocore.exceptions import NoRegionError
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

        def Queue(self, queue):
            return SQSSensorTestCase.MockQueue(self.msgs)

    class MockResourceNonExistentQueue(object):
        def __init__(self, msgs=[]):
            self.msgs = msgs

        def get_queue_by_name(self, **kwargs):
            raise ClientError({'Error': {'Code': 'AWS.SimpleQueueService.NonExistentQueue'}}, 'sqs_test')

        def Queue(self, queue):
            raise ClientError({'Error': {'Code': 'AWS.SimpleQueueService.NonExistentQueue'}}, 'sqs_test')

        def create_queue(self, **kwargs):
            return SQSSensorTestCase.MockQueue(self.msgs)

    class MockResourceRaiseClientError(object):
        def __init__(self, error_code=''):
            self.error_code = error_code

        def get_queue_by_name(self, **kwargs):
            raise ClientError({'Error': {'Code': self.error_code}}, 'sqs_test')

        def Queue(self, queue):
            raise ClientError({'Error': {'Code': self.error_code}}, 'sqs_test')

    class MockResourceRaiseNoCredentialsError(object):
        def get_queue_by_name(self, **kwargs):
            raise NoCredentialsError()

        def Queue(self, queue):
            raise NoCredentialsError()

    class MockResourceRaiseEndpointConnectionError(object):
        def get_queue_by_name(self, **kwargs):
            raise EndpointConnectionError(endpoint_url='')

        def Queue(self, queue):
            raise EndpointConnectionError(endpoint_url='')

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
        self.multiaccount_config = self.load_yaml('multiaccount.yaml')
        self.mixed_config = self.load_yaml('mixed.yaml')

    def load_yaml(self, filename):
        return yaml.safe_load(self.get_fixture_content(filename))

    @mock.patch.object(Session, 'client', mock.Mock(return_value=MockStsClient()))
    def test_poll_with_blank_config(self):
        sensor = self.get_sensor_instance(config=self.blank_config)

        sensor.setup()
        sensor.poll()

        self.assertEqual(self.get_dispatched_triggers(), [])

    @mock.patch.object(Session, 'client', mock.Mock(return_value=MockStsClient()))
    @mock.patch.object(Session, 'resource', mock.Mock(return_value=MockResource()))
    def _poll_without_message(self, config):
        sensor = self.get_sensor_instance(config=config)

        sensor.setup()
        sensor.poll()

        self.assertEqual(self.get_dispatched_triggers(), [])

    def test_poll_without_message_full_config(self):
        self._poll_without_message(self.full_config)

    def test_poll_without_message_multiaccount_config(self):
        self._poll_without_message(self.multiaccount_config)

    def test_poll_without_message_mixed_config(self):
        self._poll_without_message(self.mixed_config)

    @mock.patch.object(Session, 'client', mock.Mock(return_value=MockStsClient()))
    @mock.patch.object(Session, 'resource', mock.Mock(return_value=MockResource(['{"foo":"bar"}'])))
    def _poll_with_message(self, config):
        sensor = self.get_sensor_instance(config=config)

        sensor.setup()
        sensor.poll()

        self.assertTriggerDispatched(trigger='aws.sqs_new_message')
        self.assertNotEqual(self.get_dispatched_triggers(), [])

    def test_poll_with_message_full_config(self):
        self._poll_with_message(self.full_config)

    def test_poll_with_message_multiaccount_config(self):
        self._poll_with_message(self.multiaccount_config)

    @mock.patch.object(Session, 'client', mock.Mock(return_value=MockStsClient()))
    @mock.patch.object(Session, 'resource', mock.Mock(return_value=MockResourceNonExistentQueue(['{"foo":"bar"}'])))
    def _poll_with_non_existent_queue(self, config):
        sensor = self.get_sensor_instance(config=config)

        sensor.setup()
        sensor.poll()

        contexts = self.get_dispatched_triggers()
        self.assertNotEqual(contexts, [])
        self.assertTriggerDispatched(trigger='aws.sqs_new_message')

    def test_poll_with_non_existent_queue_full_config(self):
        self._poll_with_non_existent_queue(self.full_config)

    def test_poll_with_non_existent_queue_multiaccount_config(self):
        self._poll_with_non_existent_queue(self.multiaccount_config)

    @mock.patch.object(Session, 'client', mock.Mock(return_value=MockStsClient()))
    @mock.patch.object(Session, 'resource', mock.Mock(return_value=MockResource(['{"foo":"bar"}'])))
    def test_set_input_queues_config_dynamically(self):
        sensor = self.get_sensor_instance(config=self.blank_config)
        sensor._sensor_service.set_value('aws.roles_arns', ['arn:aws:iam::123456789098:role/rolename1'], local=False)
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

        # update input_queues to check this is reflected
        sensor._sensor_service.set_value('aws.input_queues',
                                         'https://sqs.us-west-2.amazonaws.com/123456789098/queue_name_3',
                                         local=False)
        sensor.poll()

        contexts = self.get_dispatched_triggers()
        self.assertNotEqual(contexts, [])
        self.assertTriggerDispatched(trigger='aws.sqs_new_message')

        # get message from queue 'hoge', 'fuga' then 'puyo'
        self.assertEqual([x['payload']['queue'] for x in contexts],
                         ['hoge', 'fuga', 'puyo', 'https://sqs.us-west-2.amazonaws.com/123456789098/queue_name_3'])

    @mock.patch.object(Session, 'client', mock.Mock(return_value=MockStsClient()))
    @mock.patch.object(Session, 'resource', mock.Mock(return_value=MockResource(['{"foo":"bar"}'])))
    def test_set_input_queues_config_with_list(self):
        # set 'input_queues' config with list type
        config = self.full_config
        config['sqs_sensor']['input_queues'] = ['foo', 'bar',
                                                'https://sqs.us-west-2.amazonaws.com/123456789098/queue_name_3']
        config['sqs_sensor']['roles_arns'] = ['arn:aws:iam::123456789098:role/rolename1']

        sensor = self.get_sensor_instance(config=config)
        sensor.setup()
        sensor.poll()

        contexts = self.get_dispatched_triggers()
        self.assertNotEqual(contexts, [])
        self.assertTriggerDispatched(trigger='aws.sqs_new_message')
        self.assertEqual([x['payload']['queue'] for x in contexts],
                         ['foo', 'bar', 'https://sqs.us-west-2.amazonaws.com/123456789098/queue_name_3'])

    @mock.patch.object(Session, 'client', mock.Mock(return_value=MockStsClient()))
    @mock.patch.object(Session, 'resource',
                       mock.Mock(return_value=MockResourceRaiseClientError('InvalidClientTokenId')))
    def _fails_with_invalid_token(self, config):
        sensor = self.get_sensor_instance(config=config)

        sensor.setup()
        sensor.poll()

        self.assertEqual(self.get_dispatched_triggers(), [])

    def test_fails_with_invalid_token_full_config(self):
        self._fails_with_invalid_token(self.full_config)

    def test_fails_with_invalid_token_multiaccount_config(self):
        self._fails_with_invalid_token(self.multiaccount_config)

    @mock.patch.object(Session, 'client', mock.Mock(return_value=MockStsClient()))
    @mock.patch.object(Session, 'resource',
                       mock.Mock(return_value=MockResourceRaiseNoCredentialsError()))
    def _fails_without_credentials(self, config):
        sensor = self.get_sensor_instance(config=config)

        sensor.setup()
        sensor.poll()

        self.assertEqual(self.get_dispatched_triggers(), [])

    def test_fails_without_credentials_full_config(self):
        self._fails_without_credentials(self.full_config)

    def test_fails_without_credentials_multiaccount_config(self):
        self._fails_without_credentials(self.multiaccount_config)

    @mock.patch.object(Session, 'client', mock.Mock(return_value=MockStsClient()))
    @mock.patch.object(Session, 'resource',
                       mock.Mock(return_value=MockResourceRaiseEndpointConnectionError()))
    def _fails_with_invalid_region(self, config):
        sensor = self.get_sensor_instance(config=config)

        sensor.setup()
        sensor.poll()

        self.assertEqual(self.get_dispatched_triggers(), [])

    def test_fails_with_invalid_region_full_config(self):
        self._fails_with_invalid_region(self.full_config)

    def test_fails_with_invalid_region_multiaccount_config(self):
        self._fails_with_invalid_region(self.multiaccount_config)

    @mock.patch.object(Session, 'client', mock.Mock(return_value=MockStsClientRaiseClientError()))
    @mock.patch.object(Session, 'resource', mock.Mock(return_value=MockResource(['{"foo":"bar"}'])))
    def _fails_assuming_role(self, config):
        sensor = self.get_sensor_instance(config=config)

        sensor.setup()
        sensor.poll()

    def test_fails_assuming_role_full_config(self):
        self._fails_assuming_role(self.full_config)

        self.assertTriggerDispatched(trigger='aws.sqs_new_message')
        self.assertNotEqual(self.get_dispatched_triggers(), [])

    def test_fails_assuming_role_multiaccount_config(self):
        self._fails_assuming_role(self.multiaccount_config)
        self.assertEqual(self.get_dispatched_triggers(), [])

    @mock.patch.object(Session, 'client', mock.Mock(return_value=MockStsClient()))
    @mock.patch.object(Session, 'resource',
                       mock.Mock(side_effect=NoRegionError(service_name='sqs', region_name='us-east-1')))
    def test_fails_creating_sqs_resource(self):
        sensor = self.get_sensor_instance(config=self.mixed_config)

        sensor.setup()
        sensor.poll()

        self.assertEqual(self.get_dispatched_triggers(), [])

    @mock.patch.object(Session, 'client', mock.Mock(return_value=MockStsClient()))
    @mock.patch.object(Session, 'resource', mock.Mock(return_value=MockResource(['{"foo":"bar"}'])))
    def _poll_with_missing_arn(self, config):
        config['sqs_sensor']['roles_arns'] = []

        sensor = self.get_sensor_instance(config=config)
        sensor.setup()
        sensor.poll()

    def test_poll_with_missing_arn_full_config(self):
        self._poll_with_missing_arn(self.full_config)

        self.assertNotEqual(self.get_dispatched_triggers(), [])
        self.assertTriggerDispatched(trigger='aws.sqs_new_message')

    def test_poll_with_missing_arn_multiaccount_config(self):
        self._poll_with_missing_arn(self.multiaccount_config)

        self.assertEqual(self.get_dispatched_triggers(), [])

    def test_poll_with_missing_arn_mixed_config(self):
        self._poll_with_missing_arn(self.mixed_config)

        self.assertNotEqual(self.get_dispatched_triggers(), [])
        self.assertTriggerDispatched(trigger='aws.sqs_new_message')

