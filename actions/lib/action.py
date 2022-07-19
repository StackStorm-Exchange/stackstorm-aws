import os
import re
import eventlet
import importlib

import boto.cloudformation
import boto.ec2
import boto.route53
import boto.vpc
import boto3

from boto3.session import Session
from botocore.exceptions import ClientError
from st2common.runners.base_action import Action
from ec2parsers import ResultSets


class BaseAction(Action):

    def __init__(self, config):
        super(BaseAction, self).__init__(config)

        self.credentials = {
            'region': None,
            'aws_access_key_id': None,
            'aws_secret_access_key': None
        }
        self.debug = config.get('debug', False)

        self.userdata = None
        if config.get('st2_user_data', None):
            # Check if string "looks" like a normal absolute path
            if os.path.isabs(config['st2_user_data']) and '\n' not in config['st2_user_data']:
                # Read in default user data from file
                try:
                    with open(config['st2_user_data'], 'r') as fp:
                        self.userdata = fp.read()
                except IOError as e:
                    self.logger.error(e)
            else:
                self.userdata = config['st2_user_data']

        # Note: In old static config credentials and region are under "setup" key and with a new
        # dynamic config values are top-level
        access_key_id = config.get('aws_access_key_id', None)
        secret_access_key = config.get('aws_secret_access_key', None)
        region = config.get('region', None)

        if access_key_id == "None":
            access_key_id = None
        if secret_access_key == "None":
            secret_access_key = None

        if access_key_id and secret_access_key:
            self.credentials['aws_access_key_id'] = access_key_id
            self.credentials['aws_secret_access_key'] = secret_access_key
        elif 'setup' in config:
            # Assume old-style config
            self.credentials = config['setup']

        if region:
            self.credentials['region'] = region

        self.session = Session(aws_access_key_id=self.credentials['aws_access_key_id'],
                               aws_secret_access_key=self.credentials['aws_secret_access_key'])
        # pylint: disable=no-member
        self.account_id = self.session.client('sts').get_caller_identity().get('Account')
        self.cross_roles = {
            arn.split(':')[4]: arn for arn in self.config.get('actions', {}).get('roles', [])
        }

        self.resultsets = ResultSets()

    def assume_role(self, account_id):
        ''' Assumes role and setup Boto3 session for the cross-account capability'''
        try:
            assumed_role = self.session.client('sts').assume_role(  # pylint: disable=no-member
                RoleArn=self.cross_roles[account_id],
                RoleSessionName='StackStormEvents'
            )
        except ClientError:
            self.logger.error("Failed to assume role as account %s when using the AWS session "
                              "client. Check the roles configured for the AWS pack and ensure "
                              "that the '%s' is still valid.",
                              account_id, self.cross_roles[account_id])
            raise
        except KeyError:
            self.logger.error("Could not find the role referring %s account in the config file. "
                              "Please, introduce it in 'aws.yaml' file.", account_id)
            raise

        self.credentials.update({
            'aws_access_key_id': assumed_role["Credentials"]["AccessKeyId"],
            'aws_secret_access_key': assumed_role["Credentials"]["SecretAccessKey"],
            'security_token': assumed_role["Credentials"]["SessionToken"]
        })

    def ec2_connect(self):
        region = self.credentials['region']
        del self.credentials['region']
        return boto.ec2.connect_to_region(region, **self.credentials)

    def vpc_connect(self):
        region = self.credentials['region']
        del self.credentials['region']
        return boto.vpc.connect_to_region(region, **self.credentials)

    def cf_connect(self):
        region = self.credentials['region']
        del self.credentials['region']
        return boto.cloudformation.connect_to_region(region, **self.credentials)

    def r53_connect(self):
        route53_credentials = {
            key: self.credentials[key] for key in self.credentials if key != 'region'
        }
        return boto.route53.connection.Route53Connection(**route53_credentials)

    def get_r53zone(self, zone):
        conn = self.r53_connect()
        return conn.get_zone(zone)

    def st2_user_data(self):
        return self.userdata

    def get_boto3_session(self, resource):
        region = self.credentials['region']
        del self.credentials['region']
        if 'security_token' in self.credentials:
            self.credentials['aws_session_token'] = self.credentials.pop('security_token')
        return boto3.client(resource, region_name=region, **self.credentials)

    def split_tags(self, tags):
        tag_dict = {}
        split_tags = tags.split(',')
        for tag in split_tags:
            if re.search('=', tag):
                k, v = tag.split('=', 1)
                tag_dict[k] = v
        return tag_dict

    def wait_for_state(self, instance_id, state, account_id=None, region=None, timeout=10,
                       retries=3):
        state_list = {}

        if account_id:
            self.assume_role(account_id)
        if region:
            self.credentials['region'] = region

        obj = self.ec2_connect()
        eventlet.sleep(timeout)
        instance_list = []

        for _ in range(retries + 1):
            try:
                instance_list = obj.get_only_instances([instance_id, ])
            except Exception:
                self.logger.info("Waiting for instance to become available")
                eventlet.sleep(timeout)

        for instance in instance_list:
            try:
                current_state = instance.update()
            except Exception as e:
                self.logger.info("Instance (%s) not listed. Error: %s" %
                                 (instance_id, e))
                eventlet.sleep(timeout)

            while current_state != state:
                current_state = instance.update()
            state_list[instance_id] = current_state
        return state_list

    def do_method(self, module_path, cls, action, **kwargs):
        module = importlib.import_module(module_path)

        account_id = kwargs.pop('account_id', None)
        if account_id:
            self.assume_role(account_id)

        region = kwargs.pop('region', None)
        if region:
            self.credentials['region'] = region

        # hack to connect to correct region
        if cls == 'EC2Connection':
            obj = self.ec2_connect()
        elif cls == 'VPCConnection':
            obj = self.vpc_connect()
        elif cls == 'CloudFormationConnection':
            obj = self.cf_connect()
        elif module_path == 'boto.route53.zone' and cls == 'Zone':
            zone = kwargs['zone']
            del kwargs['zone']
            obj = self.get_r53zone(zone)
        elif module_path == 'boto3.s3.transfer':
            kwargs = {k: v for k, v in kwargs.items() if v}
            if 'filename' in kwargs:
                kwargs['Filename'] = kwargs.pop('filename')
            if 'bucket' in kwargs:
                kwargs['Bucket'] = kwargs.pop('bucket')
            if 'key' in kwargs:
                kwargs['Key'] = kwargs.pop('key')
            obj = self.get_boto3_session('s3')
        elif 'boto3' in module_path:
            kwargs = {k: v for k, v in kwargs.items() if v}
            obj = self.get_boto3_session(cls)
        else:
            del self.credentials['region']
            obj = getattr(module, cls)(**self.credentials)

        if not obj:
            raise ValueError('Invalid or missing credentials (aws_access_key_id,'
                             'aws_secret_access_key) or region')

        if self.debug:
            method_fqdn = '%s.%s.%s' % (module_path, cls, action)
            self.logger.debug('Calling method "%s" with kwargs: %s' % (method_fqdn, str(kwargs)))

        resultset = getattr(obj, action)(**kwargs)
        formatted = self.resultsets.formatter(resultset)
        return formatted if isinstance(formatted, list) else [formatted]

    def do_function(self, module_path, action, **kwargs):
        module = __import__(module_path)

        if self.debug:
            function_fqdn = '%s.%s' % (module_path, action)
            self.logger.debug('Calling function "%s" with kwargs: %s' % (function_fqdn,
                                                                         str(kwargs)))

        return getattr(module, action)(**kwargs)
