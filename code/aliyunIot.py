import utime
import _thread
import osTimer

from aLiYun import aLiYun

from usr.logging import getLogger
from usr.settings import settings
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
    ],
}


class AliYunIot(object):

    def __init__(self, pk, ps, dk, ds):
        self.ali = aLiYun(pk, ps, dk, ds)
        clientID = dk
        self.ali.setMqtt(clientID, clean_session=False, keeyAlive=60, reconn=True)
        self.ali.setCallback(self.ali_sub_cb)

        self.ica_topic_property_post = 'sys/%s/%s/thing/event/property/post' % (pk, dk)
        self.ica_topic_property_post_reply = 'sys/%s/%s/thing/event/property/post_reply' % (pk, dk)
        self.ica_topic_property_set = 'sys/%s/%s/thing/service/property/set' % (pk, dk)
        self.ica_topic_event_post = 'sys/%s/%s/thing/event/{}/post' % (pk, dk)
        self.ica_topic_event_post_reply = 'sys/%s/%s/thing/event/{}/post_reply' % (pk, dk)
        self.ali_subcribe_topic()
        self.post_res = {}
        self.ali_timer = osTimer()

        self.id_iter = numiter()
        self.id_lock = _thread.allocate_lock()

        self.ali.start()

    def ali_subcribe_topic(self):
        self.ali.subcribute(self.ica_topic_property_post, qos=0)
        self.ali.subcribute(self.ica_topic_property_post_reply, qos=0)
        self.ali.subcribute(self.ica_topic_property_set, qos=0)
        for tsl_event_identifier in object_model['event']:
            self.ali.subcribute(self.ica_topic_event_post.format(tsl_event_identifier), qos=0)
            self.ali.subcribute(self.ica_topic_event_post_reply.format(tsl_event_identifier), qos=0)

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
                    pub_res = self.ali.publish(self.ica_topic_property_post, publish_data, qos=0)
                    if pub_res == 0:
                        msg_ids.append(msg_id)
                    else:
                        return False
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
                        pub_res = self.ali.publish(topic, publish_data, qos=0)
                        if pub_res == 0:
                            msg_ids.append(msg_id)
                        else:
                            return False

                pub_res = [self.get_post_res(msg_id) for msg_id in msg_ids]
                return True if False not in pub_res else False
            except Exception:
                log.error('AliYun publish topic %s failed. data: %s' % (data.get('topic'), data.get('data')))

        return False

    def ali_sub_cb(self, topic, data):
        log.info('topic: %s, data: %s' % (topic, data))
        if topic.endswith('/post_reply'):
            self.put_post_res(data['id'], True if data['code'] == 200 else False)
        else:
            pass
