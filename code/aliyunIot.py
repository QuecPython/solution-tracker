import ujson
import utime
import _thread
import osTimer

from aLiYun import aLiYun

from usr.logging import getLogger
from usr.settings import settings
from usr.settings import default_values_sys
from usr.common import numiter
from usr.common import power_restart

log = getLogger(__name__)

PROPERTY = 0x0
EVENT = 0x1
SERVICE = 0x2

object_model = {
    'event': [
        'sos_alert',
        'fault_alert',
        'low_power_alert',
        'sim_out_alert',
        'disassemble_alert',
        'drive_behavior_alert',
        'over_speed_alert',
    ],
    'property': [
        'power_switch',
        'energy',
        'phone_num',
        'loc_method',
        'loc_mode',
        'loc_cycle_period',
        'local_time',
        'low_power_alert_threshold',
        'low_power_shutdown_threshold',
        'sw_ota',
        'sw_ota_auto_upgrade',
        'sw_voice_listen',
        'sw_voice_record',
        'sw_fault_alert',
        'sw_low_power_alert',
        'sw_over_speed_alert',
        'sw_sim_out_alert',
        'sw_disassemble_alert',
        'sw_drive_behavior_alert',
        'drive_behavior_code',
        'power_restart',
        'over_speed_threshold',
        'fault_code',
        'gps_mode',
        'user_ota_action',
        'ota_status',
        'GeoLocation',
    ],
}


class AliYunIotError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class AliYunIot(object):

    def __init__(self, pk, ps, dk, ds, downlink_queue):
        self.post_res = {}
        self.ali_timer = osTimer()
        self.downlink_queue = downlink_queue

        self.id_iter = numiter()
        self.id_lock = _thread.allocate_lock()

        self.ica_topic_property_post = '/sys/%s/%s/thing/event/property/post' % (pk, dk)
        self.ica_topic_property_post_reply = '/sys/%s/%s/thing/event/property/post_reply' % (pk, dk)
        self.ica_topic_property_set = '/sys/%s/%s/thing/service/property/set' % (pk, dk)
        self.ica_topic_property_get = '/sys/%s/%s/thing/service/property/get' % (pk, dk)
        self.ica_topic_property_query = '/sys/%s/%s/thing/service/property/query' % (pk, dk)
        self.ica_topic_event_post = '/sys/%s/%s/thing/event/{}/post' % (pk, dk)
        self.ica_topic_event_post_reply = '/sys/%s/%s/thing/event/{}/post_reply' % (pk, dk)

        current_settings = settings.get()
        if current_settings['sys']['ali_burning_method'] == default_values_sys._ali_burning_method.one_type_one_density:
            dk = None
        elif current_settings['sys']['ali_burning_method'] == default_values_sys._ali_burning_method.one_machine_one_density:
            ps = None
        self.ali = aLiYun(pk, ps, dk, ds)
        self.clientID = dk
        setMqttres = self.ali.setMqtt(self.clientID, clean_session=False, keepAlive=60, reconn=True)
        if setMqttres == -1:
            raise AliYunIotError('setMqtt Falied!')
        self.ali.setCallback(self.ali_sub_cb)
        self.ali_subcribe_topic()
        self.ali.start()

    def ali_subcribe_topic(self):
        if self.ali.subscribe(self.ica_topic_property_post, qos=0) == -1:
            log.error('Topic [%s] Subscribe Falied.' % self.ica_topic_property_post)
        if self.ali.subscribe(self.ica_topic_property_post_reply, qos=0) == -1:
            log.error('Topic [%s] Subscribe Falied.' % self.ica_topic_property_post_reply)
        if self.ali.subscribe(self.ica_topic_property_set, qos=0) == -1:
            log.error('Topic [%s] Subscribe Falied.' % self.ica_topic_property_set)
        if self.ali.subscribe(self.ica_topic_property_get, qos=0) == -1:
            log.error('Topic [%s] Subscribe Falied.' % self.ica_topic_property_get)
        if self.ali.subscribe(self.ica_topic_property_query, qos=0) == -1:
            log.error('Topic [%s] Subscribe Falied.' % self.ica_topic_property_query)
        for tsl_event_identifier in object_model['event']:
            post_topic = self.ica_topic_event_post.format(tsl_event_identifier)
            if self.ali.subscribe(post_topic, qos=0) == -1:
                log.error('Topic [%s] Subscribe Falied.' % post_topic)

            post_reply_topic = self.ica_topic_event_post_reply.format(tsl_event_identifier)
            if self.ali.subscribe(post_reply_topic, qos=0) == -1:
                log.error('Topic [%s] Subscribe Falied.' % post_reply_topic)

    def get_id(self):
        with self.id_lock:
            try:
                msg_id = next(self.id_iter)
            except StopIteration:
                self.id_iter = numiter()
                msg_id = next(self.id_iter)

        return str(msg_id)

    def put_post_res(self, msg_id, res):
        self.post_res[msg_id] = res

    def get_post_res(self, msg_id):
        current_settings = settings.get()
        self.ali_timer.start(current_settings['sys']['cloud_timeout'] * 1000, 2, power_restart)
        while self.post_res.get(msg_id) is None:
            utime.sleep_ms(200)
        self.ali_timer.stop()
        res = self.post_res.pop(msg_id)
        return res

    def post_data(self, data_type, data):
        msg_ids = []
        if self.ali.getAliyunSta() == 0:
            try:
                property_params = {}
                event_params = {}
                # Format Publish Params.
                for k, v in data.items():
                    if k in object_model['property']:
                        property_params[k] = {
                            'value': v,
                            'time': utime.mktime(utime.localtime()) * 1000
                        }
                    elif k in object_model['event']:
                        event_params[k] = {
                            'value': v,
                            'time': utime.mktime(utime.localtime()) * 1000
                        }
                    else:
                        log.error('Publish Key [%s] is not in property and event' % k)
                # Publish Property Data.
                if property_params:
                    msg_id = self.get_id()
                    publish_data = {
                        'id': msg_id,
                        'version': '1.0',
                        'sys': {
                            'ack': 1
                        },
                        'params': property_params,
                        'method': 'thing.event.property.post'
                    }
                    self.ali.publish(self.ica_topic_property_post, ujson.dumps(publish_data), qos=0)
                    msg_ids.append(msg_id)
                # Publish Event Data.
                if event_params:
                    for event in event_params.keys():
                        topic = self.ica_topic_event_post.format(event)
                        msg_id = self.get_id()
                        publish_data = {
                            'id': msg_id,
                            'version': '1.0',
                            'sys': {
                                'ack': 1
                            },
                            'params': event_params[event],
                            'method': 'thing.event.%s.post' % event
                        }
                        self.ali.publish(topic, ujson.dumps(publish_data), qos=0)
                        msg_ids.append(msg_id)

                pub_res = [self.get_post_res(msg_id) for msg_id in msg_ids]
                return True if False not in pub_res else False
            except Exception:
                log.error('AliYun publish topic %s failed. data: %s' % (data.get('topic'), data.get('data')))

        return False

    def ali_sub_cb(self, topic, data):
        # log.info('topic: %s, data: %s' % (topic.decode(), data.decode()))
        topic = topic.decode()
        data = ujson.loads(data)
        if topic.endswith('/post_reply'):
            log.info('topic: %s, data: %s' % (topic, data))
            self.put_post_res(data['id'], True if data['code'] == 200 else False)
        elif topic.endswith('/property/set'):
            log.info('topic: %s, data: %s' % (topic, data))
            if data['method'] == 'thing.service.property.set':
                dl_data = list(zip(data.get("params", {}).keys(), data.get("params", {}).values()))
                self.downlink_queue.put(('object_model', dl_data))
        else:
            pass
