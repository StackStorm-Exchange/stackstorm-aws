from boto.ec2.elb import HealthCheck


def get_listners(listener_string):
    listeners = listener_string.split('#')
    listener_list = []

    if len(listeners) == 0:
        listeners = listener_string

    for i in range(len(listeners)):
        values = listeners[i].split(',')
        tup = (int(values[0]), int(values[1]), values[2])

        listener_list.append(tup)

    return listener_list


def populate_elb_health_check(kwargs):

    healthy_threshold = kwargs['healthy_threshold']
    interval = kwargs['interval']
    unhealthy_threshold = kwargs['unhealthy_threshold']
    target_value = kwargs['target']

    health_check = HealthCheck(interval=int(healthy_threshold),
        healthy_threshold=int(interval),
        unhealthy_threshold=int(unhealthy_threshold),
        target=target_value)

    del kwargs['healthy_threshold']
    del kwargs['interval']
    del kwargs['unhealthy_threshold']
    del kwargs['target']

    kwargs['health_check'] = health_check
