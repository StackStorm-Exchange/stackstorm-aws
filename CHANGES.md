# Changelog

## 1.2.2
- Fix `sqs_sensor` to parse payload as dictionary (so that it actually works)

## 1.2.1
- Update `kwargs['user_data`] to `kwargs['UserData']` per the aws.ec2_run_instances action.

## 1.2.0
- Update `st2_user_data` to take raw data as input as an alternative to file path.

## 1.1.1

- Use non-deprecated runner name and change ``runner_type`` from ``run-remote`` to
  ``remote-shell-script``.

## 1.1.0

- Fix ``ec2_run_instances`` action so ``user_data`` parameter passed to this action takes
  precedence over user data which is specified via ``st2_user_data`` config option.

  This way user can override / provide custom user data on per action invocation basis.

- Add additional log statements under debug log level which log which boto method / function
  is called and with which arguments when ``debug`` config option is set to ``True``. This helps
  with debugging / troubleshooting various pack related issues.

## 1.0.3

- Fixed issue with create_vm and destroy_vm workflows using snake_case for CamelCase params

## 1.0.2

- Fix actions which operate with tags on AWS resources.

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
