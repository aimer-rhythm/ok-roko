# Test case
import unittest

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

    def test_run_sequence(self):
        events = []

        def record_send_key(key, down_time=0.02, interval=-1, after_sleep=0):
            events.append(('key', key, down_time, after_sleep))
            return True

        def record_click(x=-1, y=-1, move_back=False, name=None, interval=-1, move=True,
                         down_time=0.01, after_sleep=0, key='left'):
            events.append(('click', round(x, 2), round(y, 2), key, move, down_time, after_sleep))
            return True

        def record_sleep(timeout):
            events.append(('sleep', timeout))
            return True

        self.task.send_key = record_send_key
        self.task.click = record_click
        self.task.sleep = record_sleep
        self.task.interruptible_wait = record_sleep
        self.task.auto_summon_module.get_key_after_sleep = lambda: 1.08
        self.task.auto_summon_module.get_click_after_sleep = lambda: 1.18
        self.task.auto_bow_module.should_input_two_as_text = lambda: False
        self.task.auto_bow_module.get_action_after_sleep = lambda: 0.68
        self.task.auto_bow_module.get_loop_after_sleep = lambda: 2.68

        self.task.run()

        expected_events = []
        for number in range(1, 7):
            expected_events.append(('key', str(number), 0.04, 0))
            expected_events.append(('sleep', 1.08))
            expected_events.append(('click', 0.5, 0.5, 'left', True, 0.04, 0))
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

        def record_click(x=-1, y=-1, move_back=False, name=None, interval=-1, move=True,
                         down_time=0.01, after_sleep=0, key='left'):
            events.append(('click', round(x, 2), round(y, 2), key, move, down_time, after_sleep))
            return True

        self.task.send_key = record_send_key
        self.task.auto_summon_module.should_input_slot_as_text = lambda: True
        og.device_manager.interaction.input_text = record_input_text
        self.task.click = record_click
        self.task.interruptible_wait = lambda timeout: None
        self.task.auto_summon_module.get_key_after_sleep = lambda: 1.08
        self.task.auto_summon_module.get_click_after_sleep = lambda: 1.18

        self.task.auto_summon_module.run_slot(2)

        self.assertEqual([
            ('key', '2', 0.04, 0),
            ('click', 0.5, 0.5, 'left', True, 0.04, 0),
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

        def record_click(x=-1, y=-1, move_back=False, name=None, interval=-1, move=True,
                         down_time=0.01, after_sleep=0, key='left'):
            events.append(('click', round(x, 2), round(y, 2), key, move, down_time, after_sleep))
            return True

        self.task.send_key = raise_send_key
        self.task.auto_summon_module.should_input_slot_as_text = lambda: True
        og.device_manager.interaction.input_text = record_input_text
        self.task.sleep = record_sleep
        self.task.interruptible_wait = record_sleep
        self.task.click = record_click
        self.task.auto_summon_module.get_key_after_sleep = lambda: 1.08
        self.task.auto_summon_module.get_click_after_sleep = lambda: 1.18

        self.task.auto_summon_module.run_slot(2)

        self.assertEqual([
            ('text', '2'),
            ('sleep', 1.08),
            ('click', 0.5, 0.5, 'left', True, 0.04, 0),
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
if __name__ == '__main__':
    unittest.main()
