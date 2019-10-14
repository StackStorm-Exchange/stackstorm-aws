import mock

from boto3.session import Session
from boto.connection import AWSQueryConnection

from run import ActionManager
from aws_base_action_test_case import AWSBaseActionTestCase

DUMMY_RAW_RESPONSE = """
<DescribeSubnetsResponse xmlns="http://ec2.amazonaws.com/doc/2014-10-01/">
    <requestId>xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx</requestId>
    <subnetSet>
        <item>
            <subnetId>subnet-foo</subnetId>
            <state>available</state>
            <vpcId>vpc-hoge</vpcId>
            <cidrBlock>10.0.0.0/24</cidrBlock>
        </item>
        <item>
            <subnetId>subnet-bar</subnetId>
            <state>available</state>
            <vpcId>vpc-fuga</vpcId>
            <cidrBlock>172.30.0.0/24</cidrBlock>
        </item>
        <item>
            <subnetId>subnet-baz</subnetId>
            <state>available</state>
            <vpcId>vpc-fuga</vpcId>
            <cidrBlock>172.30.2.0/24</cidrBlock>
        </item>
    </subnetSet>
</DescribeSubnetsResponse>
"""

MOCK_RESPONSE = mock.Mock()
MOCK_RESPONSE.status = 200
MOCK_RESPONSE.read = mock.Mock(return_value=DUMMY_RAW_RESPONSE)


@mock.patch.object(Session, 'client', mock.Mock(return_value=AWSBaseActionTestCase.MockStsClient()))
@mock.patch.object(AWSQueryConnection, 'make_request', mock.Mock(return_value=MOCK_RESPONSE))
class VPCGetAllSubnetsTestCase(AWSBaseActionTestCase):
    __test__ = True
    action_cls = ActionManager

    def setUp(self):
        super(VPCGetAllSubnetsTestCase, self).setUp()
        self._params = {
            'module_path': 'boto.vpc',
            'cls': 'VPCConnection',
            'action': 'get_all_subnets',
        }

    def _get_subnets(self, config, additional_params):
        self._params.update(additional_params)
        action = self.get_action_instance(config)
        result = action.run(**self._params)

        self.assertTrue(isinstance(result, list))
        self.assertEqual(len(result), 3)

    def test_get_subnets_full_config(self):
        self._get_subnets(self.full_config, {})

    def test_get_subnets_multiaccount_config(self):
        params = {
            'account_id': '345678901223',
            'region': 'us-east-1'
        }
        self._get_subnets(self.multiaccount_config, params)

    def _get_subnets_with_filter(self, config, additional_params):
        self._params['filters'] = {'hoge': 'fuga'}
        self._params.update(additional_params)
        action = self.get_action_instance(config)
        result = action.run(**self._params)

        self.assertTrue(isinstance(result, list))

    def test_get_subnets_with_filter_full_config(self):
        self._get_subnets_with_filter(self.full_config, {})

    def test_get_subnets_with_filter_multiaccount_config(self):
        params = {
            'account_id': '345678901223',
            'region': 'us-east-1'
        }
        self._get_subnets_with_filter(self.multiaccount_config, params)
