#!/usr/bin/env python
"""Collectd python plugin to read rabbitmq metrics from rabbitmq management plugin."""
from pyrabbit.api import Client
import collectd
import os
import time

def configure(configobj):
    global INTERVAL
    global cl
    global queues_to_count

    config = {c.key: c.values for c in configobj.children}
    INTERVAL = config['interval'][0]
    host = config['host'][0]
    port = int(config['port'][0])
    username = config['username'][0]
    password = config['password'][0]
    queues_to_count = config['message_count']
    collectd.info('rabbitmq_monitoring: Interval: {}'.format(INTERVAL))
    cl = Client('{}:{}'.format(host, port), username, password)
    collectd.info('rabbitmq_monitoring: Connecting to: {}:{} as user:{} password:{}'.format(host, port, username, password))
    collectd.info('rabbitmq_monitoring: Counting messages on: {}'.format(queues_to_count))
    collectd.register_read(read, INTERVAL)

def read(data=None):
    starttime = time.time()

    overview = cl.get_overview()

    # Object counts
    for metric_instance in ['channels', 'connections', 'consumers', 'exchanges', 'queues']:
        metric = collectd.Values()
        metric.plugin = 'rabbitmq_monitoring'
        metric.interval = INTERVAL
        metric.type = 'gauge'
        metric.type_instance = metric_instance
        metric.values = [overview['object_totals'][metric_instance]]
        metric.dispatch()

    # Aggregated Queue message stats
    for metric_instance in ['messages', 'messages_ready', 'messages_unacknowledged']:
        metric = collectd.Values()
        metric.plugin = 'rabbitmq_monitoring'
        metric.interval = INTERVAL
        metric.type = 'gauge'
        metric.type_instance = 'queue_total-{}-count'.format(metric_instance)
        metric.values = [overview['queue_totals'][metric_instance]]
        metric.dispatch()

        metric = collectd.Values()
        metric.plugin = 'rabbitmq_monitoring'
        metric.interval = INTERVAL
        metric.type = 'gauge'
        metric.type_instance = 'queue_total-{}-rate'.format(metric_instance)
        metric.values = [overview['queue_totals']['{}_details'.format(metric_instance)]['rate']]
        metric.dispatch()

    # Aggregated Message Stats
    for metric_instance in ['ack', 'confirm', 'deliver', 'deliver_get', 'deliver_no_ack', 'get',
            'get_no_ack', 'publish', 'publish_in', 'publish_out', 'redeliver',
            'return_unroutable']:
        metric = collectd.Values()
        metric.plugin = 'rabbitmq_monitoring'
        metric.interval = INTERVAL
        metric.type = 'gauge'
        metric.type_instance = 'message_total-{}-count'.format(metric_instance)
        metric.values = [overview['message_stats'][metric_instance]]
        metric.dispatch()

        metric = collectd.Values()
        metric.plugin = 'rabbitmq_monitoring'
        metric.interval = INTERVAL
        metric.type = 'gauge'
        metric.type_instance = 'message_total-{}-rate'.format(metric_instance)
        metric.values = [overview['message_stats']['{}_details'.format(metric_instance)]['rate']]
        metric.dispatch()

    # Configurable per-queue message counts
    for queue_name in queues_to_count:
        messages_detail = cl.get_messages('/', queue_name)
        if messages_detail is None:
            count = 0
        else:
            count = messages_detail[0]['message_count']
        metric = collectd.Values()
        metric.plugin = 'rabbitmq_monitoring'
        metric.interval = INTERVAL
        metric.type = 'gauge'
        metric.type_instance = 'msg_count-{}'.format(queue_name)
        metric.values = [count]
        metric.dispatch()

    timediff = time.time() - starttime
    if timediff > INTERVAL:
        collectd.warning('rabbitmq_monitoring: Took: {} > {}'.format(round(timediff, 2),
            INTERVAL))

collectd.register_config(configure)
