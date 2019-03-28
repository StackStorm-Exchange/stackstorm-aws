'''
ST2 AWS pack action runner script
'''

from lib import action


class ActionManager(action.BaseAction):
    '''
    Main action class
    '''

    def run(self, **kwargs):
        '''
        Action runner method
        '''
        aws_action = kwargs.pop('action')
        module_path = kwargs.pop('module_path')
        if aws_action == 'run_instances' and not kwargs.get('UserData', None):
            # Include default user_data from config (if set)
            user_data = self.st2_user_data()

            if user_data:
                self.logger.info('Passing in default UserData specified as st2_user_data config '
                                 'option (%s ...)' % (self.st2_user_data()[:15]))
                # Convert user_data to kwargs['UserData'] per boto3 paramaters
                kwargs['UserData'] = self.st2_user_data()
        if aws_action == 'create_tags':
            # Skip "Tags" parameter and pass "tags" as is unless it is a string.
            if 'Tags' not in kwargs and isinstance(kwargs.get('tags'), str):
                kwargs['tags'] = self.split_tags(kwargs['tags'])
        if aws_action in ('add_a', 'update_a'):
            kwargs['value'] = kwargs['value'].split(',')
        if 'cls' in kwargs.keys():
            cls = kwargs.pop('cls')
            return self.do_method(module_path, cls, aws_action, **kwargs)
        return self.do_function(module_path, aws_action, **kwargs)
