import datetime
import time
from threading import Timer


class ResettableTimer(object):
    def __init__(self, interval, function, args):
        self._timer     = None
        self.interval   = interval
        self.function   = function
        self.args       = args
        self.is_running = False
        self.start_time = 0

    def start(self):
        print '%s: starting timer' % datetime.datetime.now().strftime('%H:%M:%S')
        self.start_time = time.time()
        if not self.is_running:
            self._timer = Timer(
                self.interval, self.function, self.args)
            self._timer.start()
            self.is_running = True

    def stop(self):
        if self._timer:
            self._timer.cancel()
        self.is_running = False

    def restart(self):
        self.stop()
        self.start()

    def time_remaining(self):
        return self.interval - (time.time() - self.start_time)
