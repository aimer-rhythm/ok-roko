import random

from ok import og


class AutoBowModule:
    TEXT_INPUT_INTERACTIONS = {'PostMessageInteraction', 'ForegroundPostMessageInteraction'}
    KEY_DOWN_TIME = 0.04
    TAB_TEXT = 'Tab'
    TAB_TEXT_WAIT_TIMEOUT = 1.00
    TAB_RETRY_INTERVAL = 1.00
    TAB_TO_TWO_SLEEP_MIN = 12.00
    TAB_TO_TWO_SLEEP_MAX = 15.00
    TWO_TO_ESC_SLEEP_MIN = 0.50
    TWO_TO_ESC_SLEEP_MAX = 1.00
    LOOP_SLEEP_MIN = 2.00
    LOOP_SLEEP_MAX = 3.00
    MAX_LOOP_COUNT = None

    def __init__(self, task):
        self.task = task

    def get_tab_to_two_after_sleep(self):
        return random.uniform(self.TAB_TO_TWO_SLEEP_MIN, self.TAB_TO_TWO_SLEEP_MAX)

    def get_two_to_esc_after_sleep(self):
        return random.uniform(self.TWO_TO_ESC_SLEEP_MIN, self.TWO_TO_ESC_SLEEP_MAX)

    def get_loop_after_sleep(self):
        return random.uniform(self.LOOP_SLEEP_MIN, self.LOOP_SLEEP_MAX)

    def get_max_loop_count(self):
        return self.MAX_LOOP_COUNT

    def wait_for_tab_text(self):
        self.task.checkpoint()
        self.task.log_info('自动鞠躬模块: 等待界面出现 Tab 文字')
        result = self.task.wait_ocr(
            match=self.TAB_TEXT,
            time_out=self.TAB_TEXT_WAIT_TIMEOUT,
            raise_if_not_found=False,
            log=True,
        )
        if result:
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
        loop_index = 1
        while True:
            self.task.checkpoint()
            if max_loop_count is not None and loop_index > max_loop_count:
                break
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
            loop_index += 1
