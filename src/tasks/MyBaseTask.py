import os
import time

import cv2

from ok import BaseTask, Box, og
from ok.device.intercation import PynputInteraction
from ok.task.exceptions import TaskDisabledException
from ok.util.process import get_current_process_memory_usage

class MyBaseTask(BaseTask):
    COORDINATE_FOREGROUND_INTERACTIONS = {'PostMessageInteraction', 'ForegroundPostMessageInteraction'}
    FOREGROUND_CLICK_PRE_DELAY = 0.08
    MEMORY_PROBE_ENV = 'OK_ROKO_MEMORY_PROBE'
    MEMORY_PROBE_INTERVAL_SECONDS = 1.0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._memory_probe_last_log_times = {}
        self._memory_probe_last_rss_by_key = {}

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

    def is_memory_probe_enabled(self):
        env_value = os.getenv(self.MEMORY_PROBE_ENV)
        if env_value is not None:
            return env_value.strip().lower() not in {'', '0', 'false', 'no', 'off'}
        ok_instance = getattr(og, 'ok', None)
        config = getattr(ok_instance, 'config', None)
        if isinstance(config, dict):
            return bool(config.get('debug'))
        return False

    def log_memory(self, label, *, key=None, min_interval=None, level='info'):
        if not self.is_memory_probe_enabled():
            return None

        now = time.time()
        log_key = key or label
        min_interval = (
            self.MEMORY_PROBE_INTERVAL_SECONDS
            if min_interval is None
            else max(0.0, float(min_interval))
        )
        last_log_time = self._memory_probe_last_log_times.get(log_key)
        if last_log_time is not None and now - last_log_time < min_interval:
            return None

        rss_mb, vms_mb, shared_mb = get_current_process_memory_usage()
        previous_rss = self._memory_probe_last_rss_by_key.get(log_key)
        delta_text = ''
        if previous_rss is not None:
            delta_text = f', delta={rss_mb - previous_rss:+.1f}MB'
        shared_text = '' if shared_mb is None else f', shared={shared_mb:.1f}MB'
        message = (
            f'内存埋点: {label}, RSS={rss_mb:.1f}MB, VMS={vms_mb:.1f}MB'
            f'{shared_text}{delta_text}'
        )
        if level == 'debug':
            self.log_debug(message)
        else:
            self.log_info(message)
        self.info['Memory Probe'] = f'{rss_mb:.1f} MB'
        self._memory_probe_last_log_times[log_key] = now
        self._memory_probe_last_rss_by_key[log_key] = rss_mb
        return rss_mb

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

    def normalize_bgr_image(self, image):
        if image is None:
            return None
        if len(image.shape) == 2:
            return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        if len(image.shape) == 3 and image.shape[2] == 4:
            return cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
        return image

    def current_bgr_frame(self):
        frame = self.frame
        if frame is None:
            return None
        normalized = self.normalize_bgr_image(frame)
        if normalized is frame:
            return frame.copy()
        return normalized

    def clamp_box_to_frame(self, box, frame):
        if box is None or frame is None:
            return None
        if not all(hasattr(box, attr) for attr in ('x', 'y', 'width', 'height')):
            return None
        frame_height, frame_width = frame.shape[:2]
        left = max(0, int(box.x))
        top = max(0, int(box.y))
        right = min(frame_width, int(box.x + box.width))
        bottom = min(frame_height, int(box.y + box.height))
        if right <= left or bottom <= top:
            return None
        return Box(
            left,
            top,
            right - left,
            bottom - top,
            confidence=float(getattr(box, 'confidence', 1.0)),
            name=getattr(box, 'name', None),
        )

    def capture_box_template(self, box, frame=None):
        if box is None or not hasattr(box, 'crop_frame'):
            return None
        frame = self.current_bgr_frame() if frame is None else self.normalize_bgr_image(frame)
        if frame is None:
            return None
        clamped_box = self.clamp_box_to_frame(box, frame)
        if clamped_box is None:
            return None
        patch = clamped_box.crop_frame(frame)
        if patch is None or patch.size == 0:
            return None
        return patch.copy()

    def find_template_match(
        self,
        template,
        expected_box,
        *,
        frame=None,
        search_margin_ratio=0.5,
        threshold=0.9,
        use_gray_scale=True,
        name=None,
    ):
        self.checkpoint()
        if template is None or expected_box is None or not hasattr(expected_box, 'copy'):
            return None

        frame = self.current_bgr_frame() if frame is None else self.normalize_bgr_image(frame)
        if frame is None:
            return None

        template = self.normalize_bgr_image(template)
        template_height, template_width = template.shape[:2]
        if template_height <= 0 or template_width <= 0:
            return None

        margin_x = max(2, int(round(expected_box.width * float(search_margin_ratio))))
        margin_y = max(2, int(round(expected_box.height * float(search_margin_ratio))))
        search_box = expected_box.copy(
            x_offset=-margin_x,
            y_offset=-margin_y,
            width_offset=margin_x * 2,
            height_offset=margin_y * 2,
            name=name or getattr(expected_box, 'name', None),
        )
        search_box = self.clamp_box_to_frame(search_box, frame)
        if search_box is None or search_box.width < template_width or search_box.height < template_height:
            return None

        search_frame = search_box.crop_frame(frame).copy()
        if use_gray_scale:
            search_frame = cv2.cvtColor(search_frame, cv2.COLOR_BGR2GRAY)
            template = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)

        match_result = cv2.matchTemplate(search_frame, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(match_result)
        if max_val < float(threshold):
            return None

        return Box(
            search_box.x + max_loc[0],
            search_box.y + max_loc[1],
            template_width,
            template_height,
            confidence=float(max_val),
            name=name or getattr(expected_box, 'name', None),
        )

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

    def ocr(self, *args, **kwargs):
        match = kwargs.get('match')
        label = 'OCR'
        if match is not None:
            label = f'OCR[{match}]'
        self.log_memory(f'{label} 前', key='ocr/before', level='debug')
        result = super().ocr(*args, **kwargs)
        self.log_memory(f'{label} 后', key='ocr/after', level='debug')
        return result

    def wait_ocr(self, *args, **kwargs):
        match = kwargs.get('match')
        label = 'wait_ocr'
        if match is not None:
            label = f'wait_ocr[{match}]'
        self.log_memory(f'{label} 前', key='wait-ocr/before', level='debug')
        result = super().wait_ocr(*args, **kwargs)
        self.log_memory(f'{label} 后', key='wait-ocr/after', level='debug')
        return result

    def screenshot(self, *args, **kwargs):
        name = kwargs.get('name')
        if name is None and args:
            name = args[0]
        label = 'screenshot' if name is None else f'screenshot[{name}]'
        self.log_memory(f'{label} 入队前', key='screenshot/before', level='debug')
        result = super().screenshot(*args, **kwargs)
        self.log_memory(f'{label} 入队后', key='screenshot/after', level='debug')
        return result




