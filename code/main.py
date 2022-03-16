
from usr.tracker import Tracker
from usr.logging import getLogger

log = getLogger(__name__)

PROJECT_NAME = 'QuecPython_Tracker'

PROJECT_VERSION = '2.0.0'


def main():
    tracker = Tracker()
    log.info(tracker.locator.read())


if __name__ == '__main__':
    main()
