from lib import action
from lib import util


class ActionManager(action.BaseAction):

    def run(self, **kwargs):
        action = kwargs['action']
        del kwargs['action']
        module_path = kwargs['module_path']
        del kwargs['module_path']
        if action == 'run_instances':
            kwargs['user_data'] = self.st2_user_data()
        if action == 'create_tags':
            kwargs['tags'] = self.split_tags(kwargs['tags'])
        if action == 'create_load_balancer' or action == 'create_load_balancer_listeners':
            if kwargs['listeners'] is not None:
                kwargs['listeners'] = util.get_listners(kwargs['listeners'])
        if action == 'configure_health_check':
            util.populate_elb_health_check(kwargs)            
        if action in ('add_a', 'update_a'):
            kwargs['value'] = kwargs['value'].split(',')
        if 'cls' in kwargs.keys():
            cls = kwargs['cls']
            del kwargs['cls']
            return self.do_method(module_path, cls, action, **kwargs)
        else:
            return self.do_function(module_path, action, **kwargs)
