import random

from ok import og


class AutoBowModule:
    TEXT_INPUT_INTERACTIONS = {'PostMessageInteraction', 'ForegroundPostMessageInteraction'}
    KEY_DOWN_TIME = 0.04
    ACTION_SLEEP_MIN = 0.50
    ACTION_SLEEP_MAX = 1.00
    LOOP_SLEEP_MIN = 2.00
    LOOP_SLEEP_MAX = 3.00
    LOOP_COUNT = 10

    def __init__(self, task):
        self.task = task

    def get_action_after_sleep(self):
        return random.uniform(self.ACTION_SLEEP_MIN, self.ACTION_SLEEP_MAX)

    def get_loop_after_sleep(self):
        return random.uniform(self.LOOP_SLEEP_MIN, self.LOOP_SLEEP_MAX)

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
        self.task.log_info(
            f'开始执行自动鞠躬模块: 固定流程 Tab -> 2 -> ESC，循环 {self.LOOP_COUNT} 次'
        )
        for loop_index in range(1, self.LOOP_COUNT + 1):
            self.task.checkpoint()
            tab_after_sleep = self.get_action_after_sleep()
            two_after_sleep = self.get_action_after_sleep()
            loop_after_sleep = self.get_loop_after_sleep()
            self.task.log_info(
                f'自动鞠躬模块: 第{loop_index}轮开始，Tab后等待{tab_after_sleep:.3f}秒，'
                f'数字2后等待{two_after_sleep:.3f}秒，轮次等待{loop_after_sleep:.3f}秒'
            )
            self.task.send_key('tab', down_time=self.KEY_DOWN_TIME, after_sleep=0)
            if tab_after_sleep > 0:
                self.task.interruptible_wait(tab_after_sleep)
            self.send_two(after_sleep=two_after_sleep)
            self.task.checkpoint()
            self.task.send_key('esc', down_time=self.KEY_DOWN_TIME)
            if loop_index < self.LOOP_COUNT and loop_after_sleep > 0:
                self.task.interruptible_wait(loop_after_sleep)
            self.task.log_info(f'自动鞠躬模块: 第{loop_index}轮完成')
