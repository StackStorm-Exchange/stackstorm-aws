# Changelog

## 1.0.0

- Updated actions from boto to boto3 using st2packgen.py. 2244 actions were added (#35).

## 0.11.0

- Add capability for st2packgen.py to generate actions for all available services. Map stype "float"
  to "number".

## 0.10.0

- Updated action `runner_type` from `run-python` to `python-script`

## v0.9.3
* Adding aliases for ec2 actions (list/start/stop) machines

## v0.9.2

* Fix all the boto3 actions (autoscaling, etc.) so they work. Previously they didn't work because
  credentials weren't correctly passed in. #26

## v0.9.1

* Corrected incomplete error handling and validation of configuration (#22).

## v0.6.0

Fix the result format of some of the actions such as ec2_run_instances. Previously, the result was a list of lists of dicts and now the result is correctly a list of dicts.

Keep in mind that this is a breaking changes.

If you previously accessed the result of the ec2_run_instances action in the action-chain workflow like that - run_instances.result[0][0].id, you need to update it so it looks like this run_instance.result[0].id.

## v0.3.0

* Added CloudFormation, VPC, IAM, RDS, SQS, S3

## v0.2.0

* Added Route53

## v0.1.0

* Initial release

## v0.3.0

* Add aws.sqs_sensor which can monitor given sqs queue and trigger aws.sqs_new_message

## v0.4.0

* Add support for handling multiple input_queues to aws.sqs_sensor
