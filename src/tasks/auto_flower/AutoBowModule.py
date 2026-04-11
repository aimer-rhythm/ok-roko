import random
import time

from ok import Box, og


class AutoBowModule:
    TEXT_INPUT_INTERACTIONS = {'PostMessageInteraction', 'ForegroundPostMessageInteraction'}
    KEY_DOWN_TIME = 0.04
    TAB_TEXT = 'Tab'
    TAB_TEXT_WAIT_TIMEOUT = 1.00
    TAB_RETRY_INTERVAL = 1.00
    TAB_TEMPLATE_SEARCH_MARGIN_RATIO = 0.75
    TAB_TEMPLATE_MATCH_THRESHOLD = 0.75
    TAB_TEMPLATE_POLL_INTERVAL = 0.50
    TAB_TO_TWO_SLEEP_MIN = 12.00
    TAB_TO_TWO_SLEEP_MAX = 15.00
    TWO_TO_ESC_SLEEP_MIN = 0.50
    TWO_TO_ESC_SLEEP_MAX = 1.00
    LOOP_SLEEP_MIN = 2.00
    LOOP_SLEEP_MAX = 3.00
    MAX_LOOP_COUNT = None

    def __init__(self, task):
        self.task = task
        self._tab_text_template = None
        self._tab_text_box = None

    def get_tab_to_two_after_sleep(self):
        return random.uniform(self.TAB_TO_TWO_SLEEP_MIN, self.TAB_TO_TWO_SLEEP_MAX)

    def get_two_to_esc_after_sleep(self):
        return random.uniform(self.TWO_TO_ESC_SLEEP_MIN, self.TWO_TO_ESC_SLEEP_MAX)

    def get_loop_after_sleep(self):
        return random.uniform(self.LOOP_SLEEP_MIN, self.LOOP_SLEEP_MAX)

    def get_max_loop_count(self):
        return self.MAX_LOOP_COUNT

    def cache_tab_text_indicator(self, boxes, frame=None):
        if not boxes:
            return False
        candidate_boxes = [
            box
            for box in boxes
            if hasattr(box, 'crop_frame') and all(hasattr(box, attr) for attr in ('x', 'y', 'width', 'height'))
        ]
        if not candidate_boxes:
            return False
        frame = self.task.current_bgr_frame() if frame is None else self.task.normalize_bgr_image(frame)
        if frame is None:
            return False
        for box in candidate_boxes:
            template = self.task.capture_box_template(box, frame=frame)
            if template is None:
                continue
            self._tab_text_template = template
            self._tab_text_box = Box(
                int(box.x),
                int(box.y),
                int(box.width),
                int(box.height),
                confidence=float(getattr(box, 'confidence', 1.0)),
                name='tab-text-cache',
            )
            return True
        return False

    def find_cached_tab_text(self):
        if self._tab_text_template is None or self._tab_text_box is None:
            return None
        frame = self.task.current_bgr_frame()
        if frame is None:
            return None
        match = self.task.find_template_match(
            self._tab_text_template,
            self._tab_text_box,
            frame=frame,
            search_margin_ratio=self.TAB_TEMPLATE_SEARCH_MARGIN_RATIO,
            threshold=self.TAB_TEMPLATE_MATCH_THRESHOLD,
            name='tab-text-cache',
        )
        if match is not None:
            self.cache_tab_text_indicator([match], frame=frame)
        return match

    def wait_for_cached_tab_text(self):
        if self._tab_text_template is None or self._tab_text_box is None:
            return None
        deadline = time.monotonic() + self.TAB_TEXT_WAIT_TIMEOUT
        while True:
            self.task.checkpoint()
            match = self.find_cached_tab_text()
            if match is not None:
                return [match]
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return None
            self.task.interruptible_wait(min(self.TAB_TEMPLATE_POLL_INTERVAL, remaining))

    def wait_for_tab_text(self):
        self.task.checkpoint()
        cached_result = self.wait_for_cached_tab_text()
        if cached_result:
            self.task.log_info('自动鞠躬模块: 已通过缓存模板识别到 Tab 文字')
            return cached_result
        self.task.log_info('自动鞠躬模块: 等待界面出现 Tab 文字')
        result = self.task.wait_ocr(
            match=self.TAB_TEXT,
            x=0.40, y=0.80, to_x=0.60, to_y=0.95,
            time_out=self.TAB_TEXT_WAIT_TIMEOUT,
            raise_if_not_found=False,
            log=True,
        )
        if result:
            self.cache_tab_text_indicator(result)
            self.task.log_info('自动鞠躬模块: 已识别到 Tab 文字')
        return result

    def ensure_tab_ready(self):
        attempt = 1
        while True:
            self.task.checkpoint()
            self.task.log_info(f'自动鞠躬模块: 第{attempt}次发送 Tab')
            self.task.send_key('tab', down_time=self.KEY_DOWN_TIME, after_sleep=0)
            if self.wait_for_tab_text():
                return
            self.task.log_info(
                f'自动鞠躬模块: 第{attempt}次发送 Tab 后未识别到 Tab 文字，'
                f'{self.TAB_RETRY_INTERVAL:.3f}秒后重试'
            )
            self.task.interruptible_wait(self.TAB_RETRY_INTERVAL)
            attempt += 1

    def should_input_two_as_text(self):
        interaction = getattr(og.device_manager, 'interaction', None)
        return type(interaction).__name__ in self.TEXT_INPUT_INTERACTIONS

    def send_two(self, after_sleep):
        self.task.checkpoint()
        interaction = getattr(og.device_manager, 'interaction', None)
        interaction_name = type(interaction).__name__
        interaction_hwnd = getattr(interaction, 'hwnd', None)
        self.task.log_info(
            f'自动鞠躬模块: 发送数字2，交互方式: {interaction_name}，发送方式: 按键，hwnd: {interaction_hwnd}'
        )
        send_error = None
        try:
            send_result = self.task.send_key('2', down_time=self.KEY_DOWN_TIME, after_sleep=0)
            self.task.log_info(f'自动鞠躬模块: 数字2按键发送返回: {send_result}')
            if after_sleep > 0:
                self.task.interruptible_wait(after_sleep)
            return
        except Exception as error:
            send_error = error
            self.task.log_info(f'自动鞠躬模块: 数字2按键发送异常: {error}')

        if not self.should_input_two_as_text():
            raise send_error

        self.task.log_info(
            f'自动鞠躬模块: 数字2按键发送失败，回退为文本输入，交互方式: {interaction_name}，hwnd: {interaction_hwnd}'
        )
        interaction.input_text('2')
        self.task.log_info('自动鞠躬模块: 数字2文本输入发送完成')
        if after_sleep > 0:
            self.task.interruptible_wait(after_sleep)

    def run(self):
        max_loop_count = self.get_max_loop_count()
        loop_desc = '无限次' if max_loop_count is None else f'{max_loop_count}次'
        self.task.log_info(
            f'开始执行自动鞠躬模块: 固定流程 Tab -> 2 -> ESC，循环 {loop_desc}'
        )
        self.task.log_memory('自动鞠躬模块开始', key='auto-bow/run', min_interval=0)
        loop_index = 1
        while True:
            self.task.checkpoint()
            if max_loop_count is not None and loop_index > max_loop_count:
                break
            self.task.log_memory(
                f'自动鞠躬模块: 第{loop_index}轮开始',
                key='auto-bow/loop',
                min_interval=0,
                level='debug',
            )
            self.task.auto_summon_module.run()
            tab_after_sleep = self.get_tab_to_two_after_sleep()
            two_after_sleep = self.get_two_to_esc_after_sleep()
            loop_after_sleep = self.get_loop_after_sleep()
            self.task.log_info(
                f'自动鞠躬模块: 第{loop_index}轮开始，Tab后等待{tab_after_sleep:.3f}秒，'
                f'数字2后等待{two_after_sleep:.3f}秒，轮次等待{loop_after_sleep:.3f}秒'
            )
            self.ensure_tab_ready()
            if tab_after_sleep > 0:
                self.task.interruptible_wait(tab_after_sleep)
            self.send_two(after_sleep=two_after_sleep)
            self.task.checkpoint()
            self.task.send_key('esc', down_time=self.KEY_DOWN_TIME)
            if (max_loop_count is None or loop_index < max_loop_count) and loop_after_sleep > 0:
                self.task.interruptible_wait(loop_after_sleep)
            self.task.log_info(f'自动鞠躬模块: 第{loop_index}轮完成')
            self.task.log_memory(
                f'自动鞠躬模块: 第{loop_index}轮结束',
                key='auto-bow/loop',
                min_interval=0,
                level='debug',
            )
            import gc
            gc.collect()
            loop_index += 1
        self.task.log_memory('自动鞠躬模块结束', key='auto-bow/run', min_interval=0)
