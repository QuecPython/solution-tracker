import utime
import dataCall
from umqtt import MQTTClient
try:
    from libs.logging import getLogger
    from libs import Application
    from extensions import (
    qth_client,
    # gnss_service,
    lbs_service,
    sensor_service,
)
except ImportError:
    from usr.libs.logging import getLogger
    from usr.libs import Application
    from usr.extensions import (
    qth_client,
    # gnss_service,
    lbs_service,
    sensor_service,
    )

WAIT_NETWORK_READY_S = 30   # 30s

logger = getLogger(__name__)


def create_app(name="SimpliKit", version="1.0.0", config_path="/usr/config.json"):
    _app = Application(name, version)
    _app.config.init(config_path)

    qth_client.init_app(_app)
    # gnss_service.init_app(_app)
    lbs_service.init_app(_app)
    sensor_service.init_app(_app)

    return _app


def wait_network_ready():
    wait_cnt = WAIT_NETWORK_READY_S / 5
    is_ready = False

    while wait_cnt:
        lte = dataCall.getInfo(1, 0)
        if lte[2][0] == 1:
            is_ready = True
            break

        utime.sleep(5)
        wait_cnt -= 1

    return is_ready


if __name__ == "__main__":
    while True:
        if wait_network_ready():
            logger.debug('lte network normal')
            break

        logger.debug('wait lte network normal...')
        ret=dataCall.setPDPContext(1, 0, 'BICSAPN', '', '', 0)
        ret2=dataCall.activate(1)
        while not ret and ret2:
            ret=dataCall.setPDPContext(1, 0, 'BICSAPN', '', '', 0)  # 激活之前，应该先配置APN，这里配置第1路的APN
            ret2=dataCall.activate(1)
            if  ret and ret2:
                print("Net injection failure")
                break
    
    app = create_app()
    app.run()


