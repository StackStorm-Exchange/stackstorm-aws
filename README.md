# AWS Integration Pack

The StackStorm AWS integration pack supplies action integration for numerous AWS services.

## Prerequisites

AWS and Stackstorm, up and running.

## Setup

### Install AWS pack on StackStorm

1. Install the [AWS pack](https://github.com/stackstorm-exchange/stackstorm-aws):

    ```
    # Install AWS
    st2 pack install aws

    # Check it
    st2 action list -p aws
    ```

2. Copy the example configuration in [aws.yaml.example](./aws.yaml.example)
to `/opt/stackstorm/configs/aws.yaml` and edit as required. It must contain:

* ``region`` - Region where AWS commands will be executed
* ``aws_access_key_id`` - Access key
* ``aws_secret_access_key_id`` - Secret Access key

You can generate the access key and secret access key by following these directions:

http://docs.aws.amazon.com/IAM/latest/UserGuide/ManagingCredentials.html#Using_CreateAccessKey

If you would like to use the IAM role assigned to the instance stackstorm is running set the
key and secret to null and set the region.

```yaml
---
region: "us-east-1"
aws_access_key_id: null
aws_secret_access_key: null
st2_user_data: ""
 ```

* ``service_notifications_sensor.host`` - Listen host for the HTTP interface.
* ``service_notifications_sensor.port`` - Listen port for the HTTP interface.
* ``service_notifications_sensor.path`` - Path where the events need to be sent.

**Note** : When modifying the configuration in `/opt/stackstorm/configs/` please
           remember to tell StackStorm to load these new values by running
           `st2ctl reload --register-configs`

## st2_user_data

Optionally, you can set the user_data to set a default file to be used during new instance
creation.  Put your user_data file somewhere accessible by the StackStorm user, and use
the st2_user_data config option to set it.

```yaml
st2_user_data: "/full/path/to/file"
 ```

This file/script will be used for all invocations of the ec2_run_instances action

## Actions

Prior to installation of the aws pack, you can get the list of available actions here:

  https://github.com/StackStorm-Exchange/stackstorm-aws/tree/master/actions

Once you have installed the aws pack, you can get a list of actions in the AWS pack using:

```
st2 action list -p aws
```

To get information on a specific action, please run:

```
root@2e1d15fd5d07:/# st2 action get aws.route53_list_hosted_zones
+-------------+--------------------------------------------------------------+
| Property    | Value                                                        |
+-------------+--------------------------------------------------------------+
| id          | 594bfa4ed5d05c0b7e504803                                     |
| uid         | action:aws:route53_list_hosted_zones                         |
| ref         | aws.route53_list_hosted_zones                                |
| pack        | aws                                                          |
| name        | route53_list_hosted_zones                                    |
| enabled     | True                                                         |
| entry_point | run.py                                                       |
| runner_type | run-python                                                   |
| parameters  | {                                                            |
|             |     "DelegationSetId": {                                     |
|             |         "type": "string",                                    |
|             |         "description": "If you"re using reusable delegation  |
|             | sets and you want to list all of the hosted zones that are   |
|             | associated with a reusable delegation set, specify the ID of |
|             | that reusable delegation set. "                              |
|             |     },                                                       |
|             |     "headers": {                                             |
|             |         "type": "string"                                     |
|             |     },                                                       |
|             |     "MaxItems": {                                            |
|             |         "type": "string",                                    |
|             |         "description": "(Optional) The maximum number of     |
|             | hosted zones to be included in the response body for this    |
|             | request. If you have more than maxitems hosted zones, the    |
|             | value of the IsTruncated element in the response is true,    |
|             | and the value of the NextMarker element is the hosted zone   |
|             | ID of the first hosted zone in the next group of maxitems    |
|             | hosted zones."                                               |
|             |     },                                                       |
|             |     "Marker": {                                              |
|             |         "type": "string",                                    |
|             |         "description": "(Optional) If you have more hosted   |
|             | zones than the value of maxitems, ListHostedZones returns    |
|             | only the first maxitems hosted zones. To get the next group  |
|             | of maxitems hosted zones, submit another request to          |
|             | ListHostedZones. For the value of marker, specify the value  |
|             | of the NextMarker element that was returned in the previous  |
|             | response. Hosted zones are listed in the order in which they |
|             | were created."                                               |
|             |     },                                                       |
|             |     "module_path": {                                         |
|             |         "default": "boto3",                                  |
|             |         "type": "string",                                    |
|             |         "immutable": true                                    |
|             |     },                                                       |
|             |     "action": {                                              |
|             |         "default": "list_hosted_zones",                      |
|             |         "type": "string",                                    |
|             |         "immutable": true                                    |
|             |     },                                                       |
|             |     "cls": {                                                 |
|             |         "default": "route53",                                |
|             |         "type": "string"                                     |
|             |     }                                                        |
|             | }                                                            |
| notify      |                                                              |
| tags        |                                                              |
+-------------+--------------------------------------------------------------+
```

Since this action does not take any required parameters and won't create any resources that will
cost us anything, let's run it and see what it returns.

```
$ st2 run aws.route53_list_hosted_zones
.
id: 594cc1c2d5d05c1185bd51e5
status: succeeded
parameters: None
result:
  exit_code: 0
  result:
  - HostedZones:
    - CallerReference: 63FC852C-8B5F-12F9-8945-BC8FF413430A
      Config:
        PrivateZone: false
      Id: /hostedzone/Z2MDOUVGZHYDZ7
      Name: example.com.
      ResourceRecordSetCount: 8
    IsTruncated: false
    MaxItems: '100'
    ResponseMetadata:
      HTTPHeaders:
        content-length: '464'
        content-type: text/xml
        date: Fri, 23 Jun 2017 07:22:42 GMT
        x-amzn-requestid: cf583b3d-57f4-11e7-a217-4b0c7596d765
      HTTPStatusCode: 200
      RequestId: cf583b3d-57f4-11e7-a217-4b0c7596d765
      RetryAttempts: 0
  stderr: ''
  stdout: ''
```

To regenerate the actions used by this pack, run the following:

```
source /opt/stackstorm/virtualenvs/aws/bin/activate
cd /opt/stackstorm/packs/aws/etc/st2packgen
python st2packgen.py -d /opt/stackstorm/packs/aws/actions
st2ctl reload --register-actions
```

`st2packgen.py` will overwrite any existing actions at `/opt/stackstorm/packs/aws/actions`.

## Sensors

### ServiceNotificationsSensor

This sensor exposes a HTTP interface and listens for service event
notifications which are delivered via AWS SNS service using HTTP(s) endpoint.

Currently it supports event notifications generated by the S3 service -
http://docs.aws.amazon.com/AmazonS3/latest/dev/NotificationHowTo.html

Keep in mind that this sensor doesn't implement any kind of authentication.
This means that if the sensor is not behind a proxy which implements
authentication and is accessible to the outside world, you need to configure
``path`` setting to include a random secret which is only known to the
AWS SNS service.

#### aws.service_notification

This trigger is emitted for every service event notification.

Example trigger payload:

```json
{
    "source": "aws:s3",
    "region": "us-west-2",
    "name": "ObjectCreated:Put",
    "timestamp": 123456789,
    "response_elements": {
        "x-amz-id-2": "blahid//4U+rk=",
        "x-amz-request-id": "5FF5BB6EDE3631F8"
    },
    "request_parameters": {
        "sourceIPAddress": "127.0.0.1"
    },
    "payload": {
        "configurationId": "snsnotificationforput",
        "object": {
            "eTag": "5dfd7f29bce6d94dc5c73553f269659b",
            "key": "myfile.tar.gz",
            "size": 178428
        },
        "bucket": {
            "ownerIdentity": {
                "principalId": "BLAHBLAH"
            },
            "name": "testbucket33333",
            "arn": "arn:aws:s3:::testbucket33333"
        },
        "s3SchemaVersion": "1.0"
    }
}
```

``source``, ``region``, ``name`` and ``timestamp`` attributes are included with
all the events, but the format and values inside the ``payload`` attribute
different across different services and event types.

For a list of supported S3 event types see
http://docs.aws.amazon.com/AmazonS3/latest/dev/NotificationHowTo.html#supported-notification-event-types

### AWS SQS sensor

This is generic *SQS* Sensor using boto3 api to fetch messages from *SQS* queue.
After receiving a message it's content is passed as payload to a trigger 'aws.sqs_new_message'

This sensor can be configured either by using aws.yaml or by creating
following values in datastore:

- aws.input_queues (list queues as comma separated string: first_queue,second_queue)
- aws.aws_access_key_id
- aws.aws_secret_access_key
- aws.region
- aws.max_number_of_messages (must be between 1 - 10)

For configuration in ``aws.yaml`` with config like this

```yaml
aws_access_key_id:
aws_access_key_id:
region:
sqs_sensor:
  input_queues:
    - first_queue
    - second_queue
sqs_other:
  max_number_of_messages: 1
```

If any value exist in datastore it will be taken instead of any value in aws.yaml

#### aws.sqs\_new\_message

This trigger is emitted when a single message is received from a queue.

```json
{
  "queue": "first_sqs_queue",
  "body": "example message body"
}
```

