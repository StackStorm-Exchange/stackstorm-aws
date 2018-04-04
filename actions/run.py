from lib import action


class ActionManager(action.BaseAction):

    def run(self, **kwargs):
        action = kwargs['action']
        del kwargs['action']
        module_path = kwargs['module_path']
        del kwargs['module_path']
        if 'region_name' in kwargs.keys() and kwargs['region_name'] is not None:
            self.credentials['region'] = kwargs['region_name']
            del kwargs['region_name']
        self.create_boto3_session(kwargs['assume_role'])
        del kwargs['assume_role']
        if action == 'run_instances':
            kwargs['user_data'] = self.st2_user_data()
        if action == 'create_tags':
            kwargs['tags'] = self.split_tags(kwargs['tags'])
        if action in ('add_a', 'update_a'):
            kwargs['value'] = kwargs['value'].split(',')
        if 'cls' in kwargs.keys():
            cls = kwargs['cls']
            del kwargs['cls']
            return self.do_method(module_path, cls, action, **kwargs)
        else:
            return self.do_function(module_path, action, **kwargs)
