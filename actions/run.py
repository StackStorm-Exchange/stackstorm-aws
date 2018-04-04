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
        aws_action = kwargs['action']
        del kwargs['action']
        module_path = kwargs['module_path']
        del kwargs['module_path']
        if aws_action == 'run_instances':
            kwargs['user_data'] = self.st2_user_data()
        if aws_action == 'create_tags':
            # Skip "Tags" parameter and pass "tags" as is unless it is a string.
            if 'Tags' not in kwargs and isinstance(kwargs.get('tags'), str):
                kwargs['tags'] = self.split_tags(kwargs['tags'])
        if aws_action in ('add_a', 'update_a'):
            kwargs['value'] = kwargs['value'].split(',')
        if 'cls' in kwargs.keys():
            cls = kwargs['cls']
            del kwargs['cls']
            return self.do_method(module_path, cls, action, **kwargs)
        return self.do_function(module_path, action, **kwargs)
