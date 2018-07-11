from lib import action


class ActionManager(action.BaseAction):

    def run(self, **kwargs):
        action = kwargs['action']
        del kwargs['action']
        module_path = kwargs['module_path']
        del kwargs['module_path']
        if action == 'run_instances' and not kwargs.get('user_data', None):
            # Include default user_data from config (if set)
            user_data = self.st2_user_data()

            if user_data:
                self.logger.info('Passing in default user_data specified as st2_user_data config '
                                 'option (%s file)' % (self.user_data_file))
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
