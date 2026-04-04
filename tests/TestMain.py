# Test case
import unittest

import numpy as np
from ok import og
from ok.test.TaskTestCase import TaskTestCase
from src.config import config
from src.tasks.AutoFlowerTask import AutoFlowerTask
from src.tasks.MyOneTimeTask import MyOneTimeTask


class TestMyOneTimeTask(TaskTestCase):
    task_class = MyOneTimeTask

    config = config

    def test_ocr1(self):
        self.set_image('tests/images/main.png')
        text = self.task.find_some_text_on_bottom_right()
        self.assertEqual(text[0].name, '商城')

    def test_ocr2(self):
        self.set_image('tests/images/main.png')
        text = self.task.find_some_text_with_relative_box()
        self.assertEqual(text[0].name, '招募')

    def test_feature1(self):
        self.set_image('tests/images/main.png')
        feature = self.task.test_find_one_feature()
        self.assertIsNone(feature)

    def test_feature2(self):
        self.set_image('tests/images/main.png')
        features = self.task.test_find_feature_list()
        self.assertEqual(0, len(features))


class TestZAutoFlowerTask(TaskTestCase):
    task_class = AutoFlowerTask

    config = config

    class DummyTeleportIconBox:
        x = 300
        y = 630
        width = 42
        height = 48
        confidence = 0.934

        def center(self):
            return (321, 654)

    class DummyTextBox:
        x = 888
        y = 432
        width = 96
        height = 32

        def center(self):
            return (936, 448)

    def test_run_sequence(self):
        events = []

        def record_send_key(key, down_time=0.02, interval=-1, after_sleep=0):
            events.append(('key', key, down_time, after_sleep))
            return True

        def record_click_at(x, y, move=True, move_back=False, down_time=0.04, key='left', after_sleep=0,
                            description='坐标点击'):
            events.append(('click_at', round(x, 4), round(y, 4), key, move, down_time, after_sleep, description))
            return True

        def record_sleep(timeout):
            events.append(('sleep', timeout))
            return True

        def record_wait_ocr(x=0, y=0, to_x=1, to_y=1, width=0, height=0, name=None, box=None, match=None,
                            threshold=0, frame=None, target_height=0, time_out=0, post_action=None,
                            raise_if_not_found=False, log=False, settle_time=-1, lib="default"):
            events.append(('wait_ocr', match, time_out, raise_if_not_found, log))
            if match == '传送':
                return [self.DummyTextBox()]
            return [match]

        self.task.send_key = record_send_key
        self.task.click_at = record_click_at
        self.task.sleep = record_sleep
        self.task.wait_ocr = record_wait_ocr
        self.task.screenshot = lambda name=None, frame=None, show_box=False, frame_box=None: events.append(('screenshot', name))
        self.task.scroll_relative = lambda x, y, count: events.append(('scroll_relative', round(x, 2), round(y, 2), count))
        self.task.interruptible_wait = record_sleep
        self.task.auto_summon_module.get_key_after_sleep = lambda: 1.08
        self.task.auto_summon_module.get_click_after_sleep = lambda: 1.18
        self.task.auto_bow_module.should_input_two_as_text = lambda: False
        self.task.auto_bow_module.get_action_after_sleep = lambda: 0.68
        self.task.auto_bow_module.get_loop_after_sleep = lambda: 2.68
        self.task.auto_bow_module.get_max_loop_count = lambda: 10
        self.task.run()

        expected_events = []
        for number in range(1, 7):
            expected_events.append(('key', str(number), 0.04, 0))
            expected_events.append(('sleep', 1.08))
            expected_events.append((
                'click_at', 0.5, 0.5, 'left', True, 0.04, 0, f'自动召唤模块: 槽位{number} 左键召唤'
            ))
            expected_events.append(('sleep', 1.18))
        for loop_index in range(1, 11):
            expected_events.append(('key', 'tab', 0.04, 0))
            expected_events.append(('sleep', 0.68))
            expected_events.append(('key', '2', 0.04, 0))
            expected_events.append(('sleep', 0.68))
            expected_events.append(('key', 'esc', 0.04, 0))
            if loop_index < 10:
                expected_events.append(('sleep', 2.68))
        self.assertEqual(expected_events, events)

    def test_auto_summon_module_prefers_send_key_for_postmessage(self):
        events = []

        def record_send_key(key, down_time=0.02, interval=-1, after_sleep=0):
            events.append(('key', key, down_time, after_sleep))
            return True

        def record_input_text(text):
            events.append(('text', text))

        def record_click_at(x, y, move=True, move_back=False, down_time=0.04, key='left', after_sleep=0,
                            description='坐标点击'):
            events.append(('click_at', round(x, 2), round(y, 2), key, move, down_time, after_sleep, description))
            return True

        self.task.send_key = record_send_key
        self.task.auto_summon_module.should_input_slot_as_text = lambda: True
        og.device_manager.interaction.input_text = record_input_text
        self.task.click_at = record_click_at
        self.task.interruptible_wait = lambda timeout: None
        self.task.auto_summon_module.get_key_after_sleep = lambda: 1.08
        self.task.auto_summon_module.get_click_after_sleep = lambda: 1.18

        self.task.auto_summon_module.run_slot(2)

        self.assertEqual([
            ('key', '2', 0.04, 0),
            ('click_at', 0.5, 0.5, 'left', True, 0.04, 0, '自动召唤模块: 槽位2 左键召唤'),
        ], events)

    def test_auto_summon_module_falls_back_to_text_input_when_send_key_fails(self):
        events = []

        def raise_send_key(key, down_time=0.02, interval=-1, after_sleep=0):
            raise RuntimeError('send key denied')

        def record_input_text(text):
            events.append(('text', text))

        def record_sleep(timeout):
            events.append(('sleep', timeout))
            return True

        def record_click_at(x, y, move=True, move_back=False, down_time=0.04, key='left', after_sleep=0,
                            description='坐标点击'):
            events.append(('click_at', round(x, 2), round(y, 2), key, move, down_time, after_sleep, description))
            return True

        self.task.send_key = raise_send_key
        self.task.auto_summon_module.should_input_slot_as_text = lambda: True
        og.device_manager.interaction.input_text = record_input_text
        self.task.sleep = record_sleep
        self.task.interruptible_wait = record_sleep
        self.task.click_at = record_click_at
        self.task.auto_summon_module.get_key_after_sleep = lambda: 1.08
        self.task.auto_summon_module.get_click_after_sleep = lambda: 1.18

        self.task.auto_summon_module.run_slot(2)

        self.assertEqual([
            ('text', '2'),
            ('sleep', 1.08),
            ('click_at', 0.5, 0.5, 'left', True, 0.04, 0, '自动召唤模块: 槽位2 左键召唤'),
            ('sleep', 1.18),
        ], events)

    def test_auto_summon_module_send_slot_key_raises_when_fallback_disabled(self):
        def raise_send_key(key, down_time=0.02, interval=-1, after_sleep=0):
            raise RuntimeError('send key denied')

        self.task.send_key = raise_send_key
        self.task.auto_summon_module.should_input_slot_as_text = lambda: False
        self.task.auto_summon_module.get_key_after_sleep = lambda: 1.08

        with self.assertRaises(RuntimeError):
            self.task.auto_summon_module.send_slot_key(2)

    def test_auto_bow_module_run_sequence(self):
        events = []

        def record_send_key(key, down_time=0.02, interval=-1, after_sleep=0):
            events.append(('key', key, down_time, after_sleep))
            return True

        def record_sleep(timeout):
            events.append(('sleep', timeout))
            return True

        self.task.send_key = record_send_key
        self.task.sleep = record_sleep
        self.task.interruptible_wait = record_sleep
        self.task.auto_bow_module.should_input_two_as_text = lambda: False
        self.task.auto_bow_module.get_action_after_sleep = lambda: 0.68
        self.task.auto_bow_module.get_loop_after_sleep = lambda: 2.68
        self.task.auto_bow_module.get_max_loop_count = lambda: 10

        self.task.auto_bow_module.run()

        expected_events = []
        for loop_index in range(1, 11):
            expected_events.append(('key', 'tab', 0.04, 0))
            expected_events.append(('sleep', 0.68))
            expected_events.append(('key', '2', 0.04, 0))
            expected_events.append(('sleep', 0.68))
            expected_events.append(('key', 'esc', 0.04, 0))
            if loop_index < 10:
                expected_events.append(('sleep', 2.68))
        self.assertEqual(expected_events, events)

    def test_auto_bow_module_prefers_send_key_for_two(self):
        events = []

        def record_send_key(key, down_time=0.02, interval=-1, after_sleep=0):
            events.append(('key', key, down_time, after_sleep))
            return True

        def record_input_text(text):
            events.append(('text', text))

        def record_sleep(timeout):
            events.append(('sleep', timeout))
            return True

        self.task.send_key = record_send_key
        self.task.sleep = record_sleep
        self.task.interruptible_wait = record_sleep
        self.task.auto_bow_module.should_input_two_as_text = lambda: True
        self.task.auto_bow_module.get_action_after_sleep = lambda: 0.68
        self.task.auto_bow_module.get_loop_after_sleep = lambda: 2.68
        self.task.auto_bow_module.get_max_loop_count = lambda: 10
        og.device_manager.interaction.input_text = record_input_text

        self.task.auto_bow_module.run()

        expected_events = []
        for loop_index in range(1, 11):
            expected_events.append(('key', 'tab', 0.04, 0))
            expected_events.append(('sleep', 0.68))
            expected_events.append(('key', '2', 0.04, 0))
            expected_events.append(('sleep', 0.68))
            expected_events.append(('key', 'esc', 0.04, 0))
            if loop_index < 10:
                expected_events.append(('sleep', 2.68))
        self.assertEqual(expected_events, events)

    def test_auto_bow_module_falls_back_to_text_input_for_two_when_send_key_fails(self):
        events = []

        def raise_send_key(key, down_time=0.02, interval=-1, after_sleep=0):
            if key == '2':
                raise RuntimeError('send key denied')
            events.append(('key', key, down_time, after_sleep))
            return True

        def record_input_text(text):
            events.append(('text', text))

        def record_sleep(timeout):
            events.append(('sleep', timeout))
            return True

        self.task.send_key = raise_send_key
        self.task.sleep = record_sleep
        self.task.interruptible_wait = record_sleep
        self.task.auto_bow_module.should_input_two_as_text = lambda: True
        self.task.auto_bow_module.get_action_after_sleep = lambda: 0.68
        self.task.auto_bow_module.get_loop_after_sleep = lambda: 2.68
        self.task.auto_bow_module.get_max_loop_count = lambda: 10
        og.device_manager.interaction.input_text = record_input_text

        self.task.auto_bow_module.run()

        expected_events = []
        for loop_index in range(1, 11):
            expected_events.append(('key', 'tab', 0.04, 0))
            expected_events.append(('sleep', 0.68))
            expected_events.append(('text', '2'))
            expected_events.append(('sleep', 0.68))
            expected_events.append(('key', 'esc', 0.04, 0))
            if loop_index < 10:
                expected_events.append(('sleep', 2.68))
        self.assertEqual(expected_events, events)

    def test_auto_adjust_time_module_run_sequence(self):
        events = []

        def record_send_key(key, down_time=0.02, interval=-1, after_sleep=0):
            events.append(('key', key, down_time, after_sleep))
            return True

        def record_click(x=-1, y=-1, move_back=False, name=None, interval=-1, move=True,
                         down_time=0.01, after_sleep=0, key='left'):
            events.append(('click', round(x, 4), round(y, 4), key, move, down_time, after_sleep))
            return True

        def record_wait_ocr(x=0, y=0, to_x=1, to_y=1, width=0, height=0, name=None, box=None, match=None,
                            threshold=0, frame=None, target_height=0, time_out=0, post_action=None,
                            raise_if_not_found=False, log=False, settle_time=-1, lib="default"):
            events.append(('wait_ocr', match, time_out, raise_if_not_found, log))
            if match == '传送':
                return [self.DummyTextBox()]
            return [match]

        def record_click_box(box=None, relative_x=0.5, relative_y=0.5, raise_if_not_found=False,
                             move_back=False, down_time=0.01, after_sleep=1):
            center = box.center() if hasattr(box, 'center') else box
            if isinstance(center, tuple):
                events.append(('click_box', round(center[0]), round(center[1]), down_time, after_sleep))
            else:
                events.append(('click_box', center, down_time, after_sleep))
            return True

        def record_sleep(timeout):
            events.append(('sleep', timeout))
            return True

        self.task.send_key = record_send_key
        self.task.click = record_click
        self.task.wait_ocr = record_wait_ocr
        self.task.click_box = record_click_box
        self.task.screenshot = lambda name=None, frame=None, show_box=False, frame_box=None: events.append(('screenshot', name))
        self.task.scroll_relative = lambda x, y, count: events.append(('scroll_relative', round(x, 2), round(y, 2), count))
        self.task.interruptible_wait = record_sleep
        self.task.auto_adjust_time_module.get_action_after_sleep = lambda: 0.18
        self.task.auto_adjust_time_module.get_scroll_count = lambda: 22
        self.task.auto_adjust_time_module.get_scroll_after_sleep = lambda: 0.05
        self.task.auto_adjust_time_module.get_current_frame = lambda: np.zeros((1080, 1920, 3), dtype=np.uint8)
        self.task.auto_adjust_time_module.find_teleport_icon_box_in_frame = lambda frame: self.DummyTeleportIconBox()

        self.task.auto_adjust_time_module.run()

        expected_events = [
            ('key', 'm', 0.04, 0),
            ('sleep', 0.18),
            ('wait_ocr', '地图', 5, False, True),
            ('scroll_relative', 0.5, 0.5, 1),
            ('sleep', 0.05),
            ('scroll_relative', 0.5, 0.5, 1),
            ('sleep', 0.05),
            ('scroll_relative', 0.5, 0.5, 1),
            ('sleep', 0.05),
            ('scroll_relative', 0.5, 0.5, 1),
            ('sleep', 0.05),
            ('scroll_relative', 0.5, 0.5, 1),
            ('sleep', 0.05),
            ('scroll_relative', 0.5, 0.5, 1),
            ('sleep', 0.05),
            ('scroll_relative', 0.5, 0.5, 1),
            ('sleep', 0.05),
            ('scroll_relative', 0.5, 0.5, 1),
            ('sleep', 0.05),
            ('scroll_relative', 0.5, 0.5, 1),
            ('sleep', 0.05),
            ('scroll_relative', 0.5, 0.5, 1),
            ('sleep', 0.05),
            ('scroll_relative', 0.5, 0.5, 1),
            ('sleep', 0.05),
            ('scroll_relative', 0.5, 0.5, 1),
            ('sleep', 0.05),
            ('scroll_relative', 0.5, 0.5, 1),
            ('sleep', 0.05),
            ('scroll_relative', 0.5, 0.5, 1),
            ('sleep', 0.05),
            ('scroll_relative', 0.5, 0.5, 1),
            ('sleep', 0.05),
            ('scroll_relative', 0.5, 0.5, 1),
            ('sleep', 0.05),
            ('scroll_relative', 0.5, 0.5, 1),
            ('sleep', 0.05),
            ('scroll_relative', 0.5, 0.5, 1),
            ('sleep', 0.05),
            ('scroll_relative', 0.5, 0.5, 1),
            ('sleep', 0.05),
            ('scroll_relative', 0.5, 0.5, 1),
            ('sleep', 0.05),
            ('scroll_relative', 0.5, 0.5, 1),
            ('sleep', 0.05),
            ('scroll_relative', 0.5, 0.5, 1),
            ('sleep', 0.05),
            ('sleep', 0.18),
            ('key', 'esc', 0.04, 0),
            ('sleep', 0.18),
            ('wait_ocr', self.task.auto_adjust_time_module.HOTKEY_READY_PATTERN, 5, False, True),
            ('key', 'm', 0.04, 0),
            ('sleep', 0.18),
            ('wait_ocr', '地图', 5, False, True),
            ('screenshot', 'auto-adjust-time-teleport-icon-match'),
            ('click', 321, 654, 'left', True, 0.04, 0),
            ('sleep', 0.18),
            ('wait_ocr', '传送', 5, True, True),
            ('click', 936, 448, 'left', True, 0.04, 0),
            ('sleep', 0.18),
        ]
        self.assertEqual(expected_events, events)

    def test_auto_adjust_time_module_raises_when_teleport_icon_not_found(self):
        self.task.auto_adjust_time_module.teleport_template = np.zeros((10, 10, 3), dtype=np.uint8)
        self.task.auto_adjust_time_module.get_action_after_sleep = lambda: 0.18
        self.task.auto_adjust_time_module.get_scroll_count = lambda: 22
        self.task.auto_adjust_time_module.get_scroll_after_sleep = lambda: 0.05
        self.task.send_key = lambda key, down_time=0.02, interval=-1, after_sleep=0: True
        self.task.wait_ocr = lambda **kwargs: (
            ['地图']
            if kwargs.get('match') == self.task.auto_adjust_time_module.MAP_TEXT
            else ['F2']
        )
        self.task.interruptible_wait = lambda timeout: True
        self.task.scroll_relative = lambda x, y, count: None
        self.task.screenshot = lambda name=None, frame=None, show_box=False, frame_box=None: True
        self.task.auto_adjust_time_module.get_current_frame = lambda: np.zeros((1080, 1920, 3), dtype=np.uint8)
        self.task.auto_adjust_time_module.match_teleport_icon_with_strategy = lambda frame, strategy: None

        with self.assertRaises(RuntimeError):
            self.task.auto_adjust_time_module.run()

    def test_auto_adjust_time_module_falls_back_to_relaxed_teleport_icon_match(self):
        events = []
        attempts = {'count': 0}

        def record_match(frame, strategy):
            attempts['count'] += 1
            events.append((
                'match',
                attempts['count'],
                strategy['threshold'],
                strategy['use_gray_scale'],
                strategy['canny_lower'],
                strategy['canny_higher'],
            ))
            if attempts['count'] == 1:
                return None
            return self.DummyTeleportIconBox()

        self.task.auto_adjust_time_module.match_teleport_icon_with_strategy = record_match
        self.task.auto_adjust_time_module.teleport_template = np.zeros((10, 10, 3), dtype=np.uint8)
        self.task.auto_adjust_time_module.get_current_frame = lambda: np.zeros((1080, 1920, 3), dtype=np.uint8)

        result = self.task.auto_adjust_time_module.find_teleport_icon_box()

        self.assertIsNotNone(result)
        self.assertEqual([
            ('match', 1, 0.8, False, 0, 0),
            ('match', 2, 0.68, True, 0, 0),
        ], events)
if __name__ == '__main__':
    unittest.main()
