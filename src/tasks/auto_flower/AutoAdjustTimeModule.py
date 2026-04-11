import random
import re
from pathlib import Path

import cv2
from ok import Box, og
from ok.device.intercation import PynputInteraction


class AutoAdjustTimeModule:
    FOREGROUND_CLICK_INTERACTIONS = {'PostMessageInteraction', 'ForegroundPostMessageInteraction'}
    KEY_DOWN_TIME = 0.04
    CLICK_DOWN_TIME = 0.04
    ACTION_SLEEP_MIN = 0.10
    ACTION_SLEEP_MAX = 0.30
    SCROLL_SLEEP_MIN = 0.03
    SCROLL_SLEEP_MAX = 0.07
    MAP_TEXT = '地图'
    TELEPORT_TEXT = '传送'
    HOTKEY_READY_PATTERN = re.compile(r'F[2-6]')
    MAP_WAIT_TIMEOUT = 5
    HOTKEY_READY_TIMEOUT = 5
    TELEPORT_TEXT_WAIT_TIMEOUT = 5
    OPEN_MAP_RETRY_COUNT = 3
    HOTKEY_READY_RETRY_COUNT = 3
    SCROLL_COUNT_MIN = 20
    SCROLL_COUNT_MAX = 25
    SCROLL_X = 0.50
    SCROLL_Y = 0.50
    TELEPORT_ICON_THRESHOLD = 0.80
    TELEPORT_ICON_FALLBACK_THRESHOLD = 0.68
    TELEPORT_ICON_EDGE_THRESHOLD = 0.55
    PROJECT_ROOT = Path(__file__).resolve().parents[3]
    TELEPORT_ICON_PATH = PROJECT_ROOT / 'assets' / 'teleport-point-icon.png'

    def __init__(self, task):
        self.task = task
        self.teleport_template = self.load_teleport_template()

    def load_teleport_template(self):
        template = cv2.imread(str(self.TELEPORT_ICON_PATH), cv2.IMREAD_UNCHANGED)
        if template is None:
            raise FileNotFoundError(f'未找到传送点模板图片: {self.TELEPORT_ICON_PATH}')
        if len(template.shape) == 3 and template.shape[2] == 4:
            template = cv2.cvtColor(template, cv2.COLOR_BGRA2BGR)
        return template

    def get_teleport_icon_match_strategies(self):
        return [
            {
                'name': '彩色严格匹配',
                'threshold': self.TELEPORT_ICON_THRESHOLD,
                'use_gray_scale': False,
                'canny_lower': 0,
                'canny_higher': 0,
            },
            {
                'name': '灰度宽松匹配',
                'threshold': self.TELEPORT_ICON_FALLBACK_THRESHOLD,
                'use_gray_scale': True,
                'canny_lower': 0,
                'canny_higher': 0,
            },
            {
                'name': '边缘宽松匹配',
                'threshold': self.TELEPORT_ICON_EDGE_THRESHOLD,
                'use_gray_scale': True,
                'canny_lower': 80,
                'canny_higher': 160,
            },
        ]

    def normalize_bgr_image(self, image):
        if image is None:
            raise RuntimeError('调整游戏时间模块: 图像为空，无法继续识别')
        if len(image.shape) == 2:
            return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        if image.shape[2] == 4:
            return cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
        return image

    def get_current_frame(self):
        frame = self.task.frame
        if frame is None:
            raise RuntimeError('调整游戏时间模块: 当前帧为空，无法识别传送点图标')
        return self.normalize_bgr_image(frame.copy())

    def find_teleport_icon_box(self):
        self.task.checkpoint()
        frame = self.get_current_frame()
        return self.find_teleport_icon_box_in_frame(frame)

    def find_teleport_icon_box_in_frame(self, frame):
        self.task.checkpoint()
        self.task.log_memory(
            '调整游戏时间模块: 传送点图标匹配开始',
            key='auto-adjust-time/teleport-match',
            min_interval=0,
            level='debug',
        )
        for strategy in self.get_teleport_icon_match_strategies():
            self.task.log_info(
                '调整游戏时间模块: 传送点图标匹配尝试, '
                f"策略={strategy['name']}, threshold={strategy['threshold']:.2f}, "
                f"use_gray_scale={strategy['use_gray_scale']}, "
                f"canny=({strategy['canny_lower']}, {strategy['canny_higher']})"
            )
            teleport_icon_box = self.match_teleport_icon_with_strategy(frame, strategy)
            if teleport_icon_box is not None:
                self.task.log_info(f"调整游戏时间模块: 传送点图标匹配成功，使用策略: {strategy['name']}")
                self.task.log_memory(
                    '调整游戏时间模块: 传送点图标匹配结束',
                    key='auto-adjust-time/teleport-match',
                    min_interval=0,
                    level='debug',
                )
                return teleport_icon_box
        self.task.screenshot('auto-adjust-time-teleport-icon-not-found', frame=frame)
        self.task.log_memory(
            '调整游戏时间模块: 传送点图标匹配结束',
            key='auto-adjust-time/teleport-match',
            min_interval=0,
            level='debug',
        )
        return None

    def preprocess_template_match_image(self, image, strategy):
        processed = self.normalize_bgr_image(image)
        if strategy['use_gray_scale']:
            processed = cv2.cvtColor(processed, cv2.COLOR_BGR2GRAY)
        if strategy['canny_lower'] > 0 or strategy['canny_higher'] > 0:
            processed = cv2.Canny(processed, strategy['canny_lower'], strategy['canny_higher'])
        return processed

    def match_teleport_icon_with_strategy(self, frame, strategy):
        processed_frame = self.preprocess_template_match_image(frame, strategy)
        processed_template = self.preprocess_template_match_image(self.teleport_template, strategy)
        if (
            processed_frame.shape[0] < processed_template.shape[0]
            or processed_frame.shape[1] < processed_template.shape[1]
        ):
            self.task.log_info('调整游戏时间模块: 当前帧尺寸小于传送点模板尺寸，跳过本次匹配')
            return None
        result = cv2.matchTemplate(processed_frame, processed_template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        self.task.log_debug(
            f"调整游戏时间模块: 传送点图标匹配分数, 策略={strategy['name']}, score={max_val:.3f}"
        )
        if max_val < strategy['threshold']:
            return None
        return Box(
            max_loc[0],
            max_loc[1],
            processed_template.shape[1],
            processed_template.shape[0],
            confidence=float(max_val),
            name='teleport-icon',
        )

    def get_action_after_sleep(self):
        return random.uniform(self.ACTION_SLEEP_MIN, self.ACTION_SLEEP_MAX)

    def get_scroll_count(self):
        return random.randint(self.SCROLL_COUNT_MIN, self.SCROLL_COUNT_MAX)

    def get_scroll_after_sleep(self):
        return random.uniform(self.SCROLL_SLEEP_MIN, self.SCROLL_SLEEP_MAX)

    def wait_after_action(self):
        self.task.checkpoint()
        after_sleep = self.get_action_after_sleep()
        self.task.log_debug(f'调整游戏时间模块: 动作后等待 {after_sleep:.3f} 秒')
        self.task.interruptible_wait(after_sleep)

    def should_use_foreground_click(self):
        interaction = getattr(og.device_manager, 'interaction', None)
        return type(interaction).__name__ in self.FOREGROUND_CLICK_INTERACTIONS

    def click_point(self, x, y, description):
        self.task.checkpoint()
        if self.should_use_foreground_click():
            capture_method = getattr(og.device_manager, 'capture_method', None)
            hwnd_window = getattr(og.device_manager, 'hwnd_window', None)
            if capture_method is None or hwnd_window is None:
                raise RuntimeError(f'调整游戏时间模块: {description} 前台点击失败，窗口或截图对象为空')
            self.task.log_info(
                f'调整游戏时间模块: {description} 使用前台真实鼠标点击，坐标: ({x:.1f}, {y:.1f})'
            )
            hwnd_window.bring_to_front()
            self.task.interruptible_wait(0.08)
            foreground_interaction = PynputInteraction(capture_method, hwnd_window)
            foreground_interaction.check_clickable = False
            foreground_interaction.click(
                x,
                y,
                move=False,
                down_time=self.CLICK_DOWN_TIME,
                key='left',
            )
            return
        self.task.log_info(
            f'调整游戏时间模块: {description} 使用当前交互点击，坐标: ({x:.1f}, {y:.1f})'
        )
        self.task.click(
            x,
            y,
            move=True,
            key='left',
            down_time=self.CLICK_DOWN_TIME,
            after_sleep=0,
        )

    def wait_for_map(self):
        self.task.checkpoint()
        self.task.log_info('调整游戏时间模块: 等待地图界面出现')
        result = self.task.wait_ocr(
            match=self.MAP_TEXT,
            time_out=self.MAP_WAIT_TIMEOUT,
            raise_if_not_found=False,
            log=True,
        )
        if result:
            self.task.log_info('调整游戏时间模块: 已识别到地图')
        return result

    def wait_for_hotkey_ready(self):
        self.task.checkpoint()
        self.task.log_info('调整游戏时间模块: 等待界面重新出现 F2/F3 等快捷键文字')
        result = self.task.wait_ocr(
            match=self.HOTKEY_READY_PATTERN,
            time_out=self.HOTKEY_READY_TIMEOUT,
            raise_if_not_found=False,
            log=True,
        )
        if result:
            self.task.log_info('调整游戏时间模块: 已识别到 F2/F3 等快捷键文字')
        return result

    def send_key_and_wait(self, key):
        self.task.checkpoint()
        self.task.log_info(f'调整游戏时间模块: 发送按键 {key}')
        self.task.send_key(key, down_time=self.KEY_DOWN_TIME, after_sleep=0)
        self.wait_after_action()

    def open_map(self):
        interaction = getattr(og.device_manager, 'interaction', None)
        interaction_name = type(interaction).__name__
        interaction_hwnd = getattr(interaction, 'hwnd', None)
        for attempt in range(1, self.OPEN_MAP_RETRY_COUNT + 1):
            self.task.checkpoint()
            self.task.log_info(
                f'调整游戏时间模块: 第{attempt}次发送 M 打开地图，交互方式: {interaction_name}，hwnd: {interaction_hwnd}'
            )
            self.send_key_and_wait('m')
            if self.wait_for_map():
                return
            self.task.log_info(f'调整游戏时间模块: 第{attempt}次打开地图未识别到地图文字，准备重试')
            self.task.screenshot(f'auto-adjust-time-open-map-retry-{attempt}')
        raise RuntimeError('调整游戏时间模块: 多次发送 M 后仍未识别到地图界面')

    def wait_for_hotkey_ready_with_retry(self):
        for attempt in range(1, self.HOTKEY_READY_RETRY_COUNT + 1):
            self.task.checkpoint()
            if self.wait_for_hotkey_ready():
                return
            self.task.log_info(f'调整游戏时间模块: 第{attempt}次等待快捷键文字失败，准备重试')
            self.task.screenshot(f'auto-adjust-time-hotkey-ready-retry-{attempt}')
            self.wait_after_action()
        raise RuntimeError('调整游戏时间模块: 未识别到 F2/F3 等快捷键文字')

    def scroll_map(self):
        self.task.checkpoint()
        scroll_count = self.get_scroll_count()
        self.task.log_info(
            f'调整游戏时间模块: 开始执行地图上滚，目标位置=({self.SCROLL_X:.2f}, {self.SCROLL_Y:.2f})，'
            f'滚动次数={scroll_count}'
        )
        for index in range(1, scroll_count + 1):
            self.task.checkpoint()
            after_sleep = self.get_scroll_after_sleep()
            self.task.scroll_relative(self.SCROLL_X, self.SCROLL_Y, 1)
            self.task.log_debug(
                f'调整游戏时间模块: 第{index}次上滚完成，滚动后等待 {after_sleep:.3f} 秒'
            )
            self.task.interruptible_wait(after_sleep)
        self.wait_after_action()

    def click_teleport_icon(self):
        self.task.checkpoint()
        self.task.log_info('调整游戏时间模块: 查找传送点图标')
        frame = self.get_current_frame()
        teleport_icon_box = self.find_teleport_icon_box_in_frame(frame)
        if teleport_icon_box is None:
            raise RuntimeError('调整游戏时间模块: 未找到传送点图标，宽松匹配后仍失败')
        click_x, click_y = teleport_icon_box.center()
        self.task.log_info(
            '调整游戏时间模块: 传送点图标框坐标: '
            f'x={teleport_icon_box.x}, y={teleport_icon_box.y}, '
            f'width={teleport_icon_box.width}, height={teleport_icon_box.height}, '
            f'confidence={teleport_icon_box.confidence:.3f}'
        )
        self.task.screenshot(
            'auto-adjust-time-teleport-icon-match',
            frame=frame,
            show_box=True,
            frame_box=teleport_icon_box,
        )
        self.task.log_info(
            '调整游戏时间模块: 已找到传送点图标，'
            f'点击图标中心位置: ({click_x:.1f}, {click_y:.1f})'
        )
        self.click_point(click_x, click_y, '传送点图标点击')
        self.wait_after_action()

    def click_teleport_text(self):
        self.task.checkpoint()
        self.task.log_info('调整游戏时间模块: 等待传送文字')
        try:
            teleport_boxes = self.task.wait_ocr(
                match=self.TELEPORT_TEXT,
                time_out=self.TELEPORT_TEXT_WAIT_TIMEOUT,
                raise_if_not_found=True,
                log=True,
            )
        except Exception:
            self.task.screenshot('auto-adjust-time-teleport-text-not-found')
            raise
        teleport_box = teleport_boxes[0]
        center_x, center_y = teleport_box.center()
        self.task.log_info(
            '调整游戏时间模块: 已识别到传送文字，'
            f'框坐标: x={teleport_box.x}, y={teleport_box.y}, '
            f'width={teleport_box.width}, height={teleport_box.height}, '
            f'center=({center_x:.1f}, {center_y:.1f})'
        )
        self.click_point(center_x, center_y, '传送按钮点击')
        self.wait_after_action()

    def run(self):
        self.task.log_info('开始执行调整游戏时间模块: M -> 地图 -> 上滚轮 -> ESC -> M -> 传送点 -> 传送')
        self.task.log_memory('调整游戏时间模块开始', key='auto-adjust-time/run', min_interval=0)
        self.open_map()
        self.scroll_map()
        self.send_key_and_wait('esc')
        self.wait_for_hotkey_ready_with_retry()
        self.open_map()
        self.click_teleport_icon()
        self.click_teleport_text()
        self.task.log_memory('调整游戏时间模块结束', key='auto-adjust-time/run', min_interval=0)
