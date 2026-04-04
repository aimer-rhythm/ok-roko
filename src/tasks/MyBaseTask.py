import time

from ok import BaseTask, og
from ok.device.intercation import PynputInteraction
from ok.task.exceptions import TaskDisabledException

class MyBaseTask(BaseTask):
    COORDINATE_FOREGROUND_INTERACTIONS = {'PostMessageInteraction', 'ForegroundPostMessageInteraction'}
    FOREGROUND_CLICK_PRE_DELAY = 0.08

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

    def should_use_foreground_mouse_for_coordinates(self):
        interaction = getattr(og.device_manager, 'interaction', None)
        return type(interaction).__name__ in self.COORDINATE_FOREGROUND_INTERACTIONS

    def click_at(self, x, y, move=True, move_back=False, down_time=0.04, key='left', after_sleep=0, description='坐标点击'):
        self.checkpoint()
        interaction = getattr(og.device_manager, 'interaction', None)
        interaction_name = type(interaction).__name__
        if self.should_use_foreground_mouse_for_coordinates():
            capture_method = getattr(og.device_manager, 'capture_method', None)
            hwnd_window = getattr(og.device_manager, 'hwnd_window', None)
            if capture_method is None or hwnd_window is None:
                raise RuntimeError(f'{description} 前台点击失败，窗口或截图对象为空')
            self.log_info(
                f'{description}: 使用前台真实鼠标点击，交互方式: {interaction_name}，坐标: ({x:.3f}, {y:.3f})'
            )
            hwnd_window.bring_to_front()
            self.interruptible_wait(self.FOREGROUND_CLICK_PRE_DELAY)
            foreground_interaction = PynputInteraction(capture_method, hwnd_window)
            foreground_interaction.check_clickable = False
            result = foreground_interaction.click(
                x,
                y,
                move=move,
                move_back=move_back,
                down_time=down_time,
                key=key,
            )
        else:
            self.log_info(
                f'{description}: 使用当前交互点击，交互方式: {interaction_name}，坐标: ({x:.3f}, {y:.3f})'
            )
            result = self.click(
                x,
                y,
                move=move,
                move_back=move_back,
                down_time=down_time,
                key=key,
                after_sleep=0,
            )
        if after_sleep > 0:
            self.interruptible_wait(after_sleep)
        return result




