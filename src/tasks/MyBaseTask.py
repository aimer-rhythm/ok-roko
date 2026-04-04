import re
import time

from ok import BaseTask
from ok.task.exceptions import TaskDisabledException

class MyBaseTask(BaseTask):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def ensure_not_stopped(self):
        if self.running and not self.enabled:
            raise TaskDisabledException('task disabled')

    def wait_if_paused(self):
        while self.running and self.paused:
            self.ensure_not_stopped()
            time.sleep(0.05)

    def checkpoint(self):
        self.ensure_not_stopped()
        self.wait_if_paused()

    def interruptible_wait(self, duration):
        remaining = max(0.0, float(duration))
        while remaining > 0:
            self.checkpoint()
            sleep_time = min(0.05, remaining)
            time.sleep(sleep_time)
            remaining -= sleep_time




