import random

from ok import og


class AutoSummonModule:
    TEXT_INPUT_INTERACTIONS = {'PostMessageInteraction', 'ForegroundPostMessageInteraction'}
    SLOT_SEQUENCE = (1, 2, 3, 4, 5, 6)
    SLOT_MIN = 1
    SLOT_MAX = 6
    KEY_DOWN_TIME = 0.04
    KEY_AFTER_SLEEP_MIN = 1.00
    KEY_AFTER_SLEEP_MAX = 2.00
    SUMMON_CLICK_X = 0.50
    SUMMON_CLICK_Y = 0.50
    CLICK_DOWN_TIME = 0.04
    CLICK_AFTER_SLEEP_MIN = 1.00
    CLICK_AFTER_SLEEP_MAX = 2.00

    def __init__(self, task):
        self.task = task

    def validate_slot_number(self, slot_number):
        if not self.SLOT_MIN <= slot_number <= self.SLOT_MAX:
            raise ValueError(f'槽位编号必须在 {self.SLOT_MIN} 到 {self.SLOT_MAX} 之间')

    def get_key_after_sleep(self):
        return random.uniform(self.KEY_AFTER_SLEEP_MIN, self.KEY_AFTER_SLEEP_MAX)

    def get_click_after_sleep(self):
        return random.uniform(self.CLICK_AFTER_SLEEP_MIN, self.CLICK_AFTER_SLEEP_MAX)

    def should_input_slot_as_text(self):
        interaction = getattr(og.device_manager, 'interaction', None)
        return type(interaction).__name__ in self.TEXT_INPUT_INTERACTIONS

    def send_slot_key(self, slot_number):
        self.task.checkpoint()
        self.validate_slot_number(slot_number)
        after_sleep = self.get_key_after_sleep()
        slot_text = str(slot_number)
        interaction = getattr(og.device_manager, 'interaction', None)
        interaction_name = type(interaction).__name__
        interaction_hwnd = getattr(interaction, 'hwnd', None)
        self.task.log_info(
            f'自动召唤模块: 槽位{slot_number} 发送选择指令，交互方式: {interaction_name}，发送方式: 按键，hwnd: {interaction_hwnd}'
        )
        send_error = None
        try:
            send_result = self.task.send_key(
                slot_text,
                down_time=self.KEY_DOWN_TIME,
                after_sleep=0,
            )
            self.task.log_info(f'自动召唤模块: 槽位{slot_number} 按键发送返回: {send_result}')
            if after_sleep > 0:
                self.task.interruptible_wait(after_sleep)
            return
        except Exception as error:
            send_error = error
            self.task.log_info(f'自动召唤模块: 槽位{slot_number} 按键发送异常: {error}')

        if not self.should_input_slot_as_text():
            raise send_error

        self.task.log_info(
            f'自动召唤模块: 槽位{slot_number} 按键发送失败，回退为文本输入，交互方式: {interaction_name}，hwnd: {interaction_hwnd}'
        )
        interaction.input_text(slot_text)
        self.task.log_info(f'自动召唤模块: 槽位{slot_number} 文本输入发送完成: {slot_text}')
        if after_sleep > 0:
            self.task.interruptible_wait(after_sleep)
            self.task.log_debug(f'自动召唤模块: 槽位{slot_number} 文本输入后等待完成: {after_sleep:.3f}秒')

    def run_slot(self, slot_number):
        self.task.checkpoint()
        self.validate_slot_number(slot_number)
        self.task.log_info(f'自动召唤模块: 开始处理槽位{slot_number}')
        self.send_slot_key(slot_number)
        self.task.log_info(f'自动召唤模块: 槽位{slot_number} 数字键发送完成，执行鼠标左键')
        after_sleep = self.get_click_after_sleep()
        click_result = self.task.click(
            self.SUMMON_CLICK_X,
            self.SUMMON_CLICK_Y,
            move=True,
            down_time=self.CLICK_DOWN_TIME,
            key='left',
            after_sleep=0,
        )
        self.task.log_info(f'自动召唤模块: 槽位{slot_number} 左键点击返回: {click_result}')
        if after_sleep > 0:
            self.task.interruptible_wait(after_sleep)

    def run(self):
        self.task.log_info(
            '开始执行自动召唤模块: 1 -> 左键 -> 2 -> 左键 -> 3 -> 左键 -> 4 -> 左键 -> 5 -> 左键 -> 6 -> 左键'
        )
        for number in self.SLOT_SEQUENCE:
            self.task.checkpoint()
            self.task.log_info(f'自动召唤模块: 准备进入槽位{number}')
            self.run_slot(number)
            self.task.log_info(f'自动召唤模块: 槽位{number} 处理完成')
