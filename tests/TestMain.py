# Test case
import unittest

import numpy as np
from ok import Box, og
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
        self.set_image('assets/images/0.png')
        feature = self.task.find_one('first_summoned')
        self.assertIsNotNone(feature)
        self.assertEqual('first_summoned', feature.name)

    def test_feature2(self):
        self.set_image('assets/images/0.png')
        features = self.task.find_feature('first_summoned')
        self.assertGreaterEqual(len(features), 1)


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

        def record_click(x=-1, y=-1, move_back=False, name=None, interval=-1, move=True,
                         down_time=0.01, after_sleep=0, key='left'):
            events.append(('click', round(x, 4), round(y, 4), key, move, down_time, after_sleep))
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
        self.task.click = record_click
        self.task.sleep = record_sleep
        self.task.wait_ocr = record_wait_ocr
        self.task.screenshot = lambda name=None, frame=None, show_box=False, frame_box=None: events.append(('screenshot', name))
        self.task.scroll_relative = lambda x, y, count: events.append(('scroll_relative', round(x, 2), round(y, 2), count))
        self.task.interruptible_wait = record_sleep
        self.task.auto_summon_module.run = lambda: events.append(('summon',))
        self.task.auto_bow_module.should_input_two_as_text = lambda: False
        self.task.auto_bow_module.get_tab_to_two_after_sleep = lambda: 12.68
        self.task.auto_bow_module.get_two_to_esc_after_sleep = lambda: 0.68
        self.task.auto_bow_module.get_loop_after_sleep = lambda: 2.68
        self.task.auto_bow_module.get_max_loop_count = lambda: 10
        self.task.run()

        expected_events = []
        for loop_index in range(1, 11):
            expected_events.append(('summon',))
            expected_events.append(('key', 'tab', 0.04, 0))
            expected_events.append(('wait_ocr', 'Tab', 1.0, False, True))
            expected_events.append(('sleep', 12.68))
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

    def test_auto_summon_module_skips_when_all_slots_already_summoned(self):
        events = []

        def record_send_key(key, down_time=0.02, interval=-1, after_sleep=0):
            events.append(('key', key, down_time, after_sleep))
            return True

        def record_click(x=-1, y=-1, move_back=False, name=None, interval=-1, move=True,
                         down_time=0.01, after_sleep=0, key='left'):
            events.append(('click', round(x, 2), round(y, 2), key, move, down_time, after_sleep))
            return True

        summoned_results = {
            slot_number: {'state': 'summoned', 'score': 0.99, 'box': None}
            for slot_number in range(1, 7)
        }

        self.task.send_key = record_send_key
        self.task.click = record_click
        self.task.ocr = lambda *args, **kwargs: ['F2']
        self.task.auto_summon_module.detect_all_slot_summon_states = (
            lambda frame=None, suppress_exceptions=False: (
                np.zeros((1080, 1920, 3), dtype=np.uint8),
                summoned_results,
                {},
            )
        )

        self.task.auto_summon_module.run()

        self.assertEqual([], events)

    def test_auto_summon_module_skips_when_not_on_main_interface(self):
        events = []

        def record_send_key(key, down_time=0.02, interval=-1, after_sleep=0):
            events.append(('key', key, down_time, after_sleep))
            return True

        def record_click(x=-1, y=-1, move_back=False, name=None, interval=-1, move=True,
                         down_time=0.01, after_sleep=0, key='left'):
            events.append(('click', round(x, 2), round(y, 2), key, move, down_time, after_sleep))
            return True

        self.task.send_key = record_send_key
        self.task.click = record_click
        self.task.ocr = lambda *args, **kwargs: []
        self.task.auto_summon_module.detect_all_slot_summon_states = lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError('should not detect summon states when not on main interface')
        )
        self.task.auto_summon_module.run = type(self.task.auto_summon_module).run.__get__(
            self.task.auto_summon_module,
            type(self.task.auto_summon_module),
        )

        self.task.auto_summon_module.run()

        self.assertEqual([], events)

    def test_auto_summon_module_runs_targeted_sequence_when_any_slot_unsummoned(self):
        events = []
        initial_results = {
            1: {'state': 'unsummoned', 'score': 0.21, 'box': None},
            2: {'state': 'summoned', 'score': 0.99, 'box': None},
            3: {'state': 'summoned', 'score': 0.99, 'box': None},
            4: {'state': 'summoned', 'score': 0.99, 'box': None},
            5: {'state': 'summoned', 'score': 0.99, 'box': None},
            6: {'state': 'summoned', 'score': 0.99, 'box': None},
        }

        self.task.ocr = lambda *args, **kwargs: ['F2']
        self.task.auto_summon_module.detect_all_slot_summon_states = (
            lambda frame=None, suppress_exceptions=False: (
                np.zeros((1080, 1920, 3), dtype=np.uint8),
                initial_results,
                {},
            )
        )
        self.task.auto_summon_module.run_full_summon_sequence = lambda slot_numbers=None: events.append(
            ('run_full', tuple(slot_numbers or ()))
        )
        self.task.auto_summon_module.ensure_all_slots_summoned = lambda: events.append(('ensure_all',))
        self.task.auto_summon_module.run = type(self.task.auto_summon_module).run.__get__(
            self.task.auto_summon_module,
            type(self.task.auto_summon_module),
        )

        self.task.auto_summon_module.run()

        self.assertEqual([('run_full', (1,)), ('ensure_all',)], events)

    def test_auto_summon_module_run_full_summon_sequence_uses_slot_order(self):
        slots = []

        self.task.auto_summon_module.summon_slot_until_summoned = lambda slot_number: slots.append(slot_number)

        self.task.auto_summon_module.run_full_summon_sequence()

        self.assertEqual([1, 2, 3, 4, 5, 6], slots)

    def test_auto_summon_module_ensure_all_slots_summoned_repairs_failed_slots(self):
        repair_slots = []
        detect_results = iter([
            (
                np.zeros((1080, 1920, 3), dtype=np.uint8),
                {
                    1: {'state': 'summoned', 'score': 0.99, 'box': None},
                    2: {'state': 'unsummoned', 'score': 0.18, 'box': None},
                    3: {'state': 'summoned', 'score': 0.99, 'box': None},
                    5: {'state': 'unsummoned', 'score': 0.12, 'box': None},
                    6: {'state': 'summoned', 'score': 0.99, 'box': None},
                },
                {
                    4: RuntimeError('temporary disconnect'),
                },
            ),
            (
                np.zeros((1080, 1920, 3), dtype=np.uint8),
                {
                    slot_number: {'state': 'summoned', 'score': 0.99, 'box': None}
                    for slot_number in range(1, 7)
                },
                {},
            ),
        ])

        self.task.auto_summon_module.detect_all_slot_summon_states = (
            lambda frame=None, suppress_exceptions=False: next(detect_results)
        )
        self.task.auto_summon_module.summon_slot_until_summoned = lambda slot_number: repair_slots.append(slot_number)

        result = self.task.auto_summon_module.ensure_all_slots_summoned()

        self.assertEqual([2, 4, 5], repair_slots)
        self.assertTrue(all(result[slot_number]['state'] == 'summoned' for slot_number in range(1, 7)))

    def test_auto_summon_module_retries_single_slot_after_post_summon_unsummoned(self):
        events = []
        state_checks = iter([
            {'state': 'unsummoned', 'score': 0.21, 'box': None},
            {'state': 'summoned', 'score': 0.99, 'box': None},
        ])

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
        self.task.interruptible_wait = record_sleep
        self.task.auto_summon_module.get_key_after_sleep = lambda: 1.08
        self.task.auto_summon_module.get_click_after_sleep = lambda: 1.18
        self.task.auto_summon_module.SUMMON_RECHECK_WAIT = 0
        self.task.auto_summon_module.SUMMON_RETRY_INTERVAL = 10
        self.task.auto_summon_module.detect_slot_summon_state = lambda slot_number, frame=None, region_match=None: next(state_checks)
        self.task.auto_summon_module.summon_slot_until_summoned = type(
            self.task.auto_summon_module
        ).summon_slot_until_summoned.__get__(
            self.task.auto_summon_module,
            type(self.task.auto_summon_module),
        )

        self.task.auto_summon_module.summon_slot_until_summoned(3)

        self.assertEqual([
            ('key', '3', 0.04, 0),
            ('sleep', 1.08),
            ('click', 0.5, 0.5, 'left', True, 0.04, 0),
            ('sleep', 1.18),
            ('sleep', 10),
            ('key', '3', 0.04, 0),
            ('sleep', 1.08),
            ('click', 0.5, 0.5, 'left', True, 0.04, 0),
            ('sleep', 1.18),
        ], events)

    def test_auto_summon_module_retries_single_slot_after_post_summon_detection_error(self):
        events = []
        state_results = iter([
            RuntimeError('temporary disconnect'),
            {'state': 'summoned', 'score': 0.99, 'box': None},
        ])

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

        def record_detect(slot_number, frame=None, region_match=None):
            result = next(state_results)
            if isinstance(result, Exception):
                raise result
            return result

        self.task.send_key = record_send_key
        self.task.click = record_click
        self.task.interruptible_wait = record_sleep
        self.task.auto_summon_module.get_key_after_sleep = lambda: 1.08
        self.task.auto_summon_module.get_click_after_sleep = lambda: 1.18
        self.task.auto_summon_module.SUMMON_RECHECK_WAIT = 0
        self.task.auto_summon_module.SUMMON_RETRY_INTERVAL = 10
        self.task.auto_summon_module.detect_slot_summon_state = record_detect
        self.task.auto_summon_module.summon_slot_until_summoned = type(
            self.task.auto_summon_module
        ).summon_slot_until_summoned.__get__(
            self.task.auto_summon_module,
            type(self.task.auto_summon_module),
        )

        self.task.auto_summon_module.summon_slot_until_summoned(4)

        self.assertEqual([
            ('key', '4', 0.04, 0),
            ('sleep', 1.08),
            ('click', 0.5, 0.5, 'left', True, 0.04, 0),
            ('sleep', 1.18),
            ('sleep', 10),
            ('key', '4', 0.04, 0),
            ('sleep', 1.08),
            ('click', 0.5, 0.5, 'left', True, 0.04, 0),
            ('sleep', 1.18),
        ], events)

    def test_auto_bow_module_run_sequence(self):
        events = []

        def record_send_key(key, down_time=0.02, interval=-1, after_sleep=0):
            events.append(('key', key, down_time, after_sleep))
            return True

        def record_sleep(timeout):
            events.append(('sleep', timeout))
            return True

        def record_wait_ocr(x=0, y=0, to_x=1, to_y=1, width=0, height=0, name=None, box=None, match=None,
                            threshold=0, frame=None, target_height=0, time_out=0, post_action=None,
                            raise_if_not_found=False, log=False, settle_time=-1, lib="default"):
            events.append(('wait_ocr', match, time_out, raise_if_not_found, log))
            return [match]

        self.task.send_key = record_send_key
        self.task.sleep = record_sleep
        self.task.interruptible_wait = record_sleep
        self.task.wait_ocr = record_wait_ocr
        self.task.auto_summon_module.run = lambda: events.append(('summon',))
        self.task.auto_bow_module.should_input_two_as_text = lambda: False
        self.task.auto_bow_module.get_tab_to_two_after_sleep = lambda: 12.68
        self.task.auto_bow_module.get_two_to_esc_after_sleep = lambda: 0.68
        self.task.auto_bow_module.get_loop_after_sleep = lambda: 2.68
        self.task.auto_bow_module.get_max_loop_count = lambda: 10

        self.task.auto_bow_module.run()

        expected_events = []
        for loop_index in range(1, 11):
            expected_events.append(('summon',))
            expected_events.append(('key', 'tab', 0.04, 0))
            expected_events.append(('wait_ocr', 'Tab', 1.0, False, True))
            expected_events.append(('sleep', 12.68))
            expected_events.append(('key', '2', 0.04, 0))
            expected_events.append(('sleep', 0.68))
            expected_events.append(('key', 'esc', 0.04, 0))
            if loop_index < 10:
                expected_events.append(('sleep', 2.68))
        self.assertEqual(expected_events, events)

    def test_auto_bow_module_retries_tab_until_text_appears(self):
        events = []
        wait_results = iter([
            [],
            ['Tab'],
        ])

        def record_send_key(key, down_time=0.02, interval=-1, after_sleep=0):
            events.append(('key', key, down_time, after_sleep))
            return True

        def record_sleep(timeout):
            events.append(('sleep', timeout))
            return True

        def record_wait_ocr(x=0, y=0, to_x=1, to_y=1, width=0, height=0, name=None, box=None, match=None,
                            threshold=0, frame=None, target_height=0, time_out=0, post_action=None,
                            raise_if_not_found=False, log=False, settle_time=-1, lib="default"):
            events.append(('wait_ocr', match, time_out, raise_if_not_found, log))
            return next(wait_results)

        self.task.send_key = record_send_key
        self.task.interruptible_wait = record_sleep
        self.task.wait_ocr = record_wait_ocr
        self.task.auto_summon_module.run = lambda: events.append(('summon',))
        self.task.auto_bow_module.should_input_two_as_text = lambda: False
        self.task.auto_bow_module.get_tab_to_two_after_sleep = lambda: 12.68
        self.task.auto_bow_module.get_two_to_esc_after_sleep = lambda: 0.68
        self.task.auto_bow_module.get_loop_after_sleep = lambda: 2.68
        self.task.auto_bow_module.get_max_loop_count = lambda: 1

        self.task.auto_bow_module.run()

        self.assertEqual([
            ('summon',),
            ('key', 'tab', 0.04, 0),
            ('wait_ocr', 'Tab', 1.0, False, True),
            ('sleep', 1.0),
            ('key', 'tab', 0.04, 0),
            ('wait_ocr', 'Tab', 1.0, False, True),
            ('sleep', 12.68),
            ('key', '2', 0.04, 0),
            ('sleep', 0.68),
            ('key', 'esc', 0.04, 0),
        ], events)

    def test_auto_bow_module_detects_unsummoned_slot_one_icon(self):
        frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        self.task.feature_exists = lambda name: name == 'first_summoned'
        template = self.task.auto_summon_module.resize_reference_for_frame(
            frame,
            self.task.auto_summon_module.slot_one_summoned_reference,
        )
        x = 64
        y = 72
        height, width = template.shape[:2]
        frame[y:y + height, x:x + width] = template
        region_box = Box(x, y, width, height)
        icon_box = self.task.auto_summon_module.build_absolute_icon_box(region_box)
        frame[icon_box.y:icon_box.y + icon_box.height, icon_box.x:icon_box.x + icon_box.width] = 0
        region_match = {
            'box': icon_box,
            'score': 1.0,
            'reference_state': 'test-first-summoned-bbox',
        }

        match = self.task.auto_summon_module.detect_slot_one_summon_state(frame=frame, region_match=region_match)

        self.assertEqual('unsummoned', match['state'])
        self.assertLess(match['score'], self.task.auto_summon_module.SLOT_ONE_SUMMONED_MATCH_MIN_CONFIDENCE)
        self.assertLessEqual(abs(match['region_box'].x - icon_box.x), 1)
        self.assertLessEqual(abs(match['region_box'].y - icon_box.y), 1)
        self.assertGreaterEqual(match['locate_score'], self.task.auto_summon_module.SLOT_ONE_LOCATE_MIN_CONFIDENCE)

    def test_auto_bow_module_locates_slot_one_region_from_annotation_bbox_at_1080p(self):
        frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        region_match = self.task.auto_summon_module.locate_slot_one_region(frame)
        expected_box = self.task.auto_summon_module.build_slot_one_annotation_box(frame)

        self.assertEqual('result-json-first_summoned-bbox', region_match['reference_state'])
        self.assertEqual(1.0, region_match['score'])
        self.assertEqual(expected_box.x, region_match['box'].x)
        self.assertEqual(expected_box.y, region_match['box'].y)
        self.assertEqual(expected_box.width, region_match['box'].width)
        self.assertEqual(expected_box.height, region_match['box'].height)
        self.assertIsNone(region_match['anchor_box'])

    def test_auto_bow_module_detects_summoned_slot_one_icon(self):
        frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        self.task.feature_exists = lambda name: name == 'first_summoned'
        template = self.task.auto_summon_module.resize_reference_for_frame(
            frame,
            self.task.auto_summon_module.slot_one_summoned_reference,
        )
        x = 112
        y = 120
        height, width = template.shape[:2]
        frame[y:y + height, x:x + width] = template
        region_box = Box(x, y, width, height)
        icon_box = self.task.auto_summon_module.build_absolute_icon_box(region_box)
        region_match = {
            'box': icon_box,
            'score': 1.0,
            'reference_state': 'test-first-summoned-bbox',
        }

        match = self.task.auto_summon_module.detect_slot_one_summon_state(frame=frame, region_match=region_match)

        self.assertEqual('summoned', match['state'])
        self.assertGreaterEqual(match['score'], self.task.auto_summon_module.SLOT_ONE_SUMMONED_MATCH_MIN_CONFIDENCE)
        self.assertLessEqual(abs(match['region_box'].x - icon_box.x), 1)
        self.assertLessEqual(abs(match['region_box'].y - icon_box.y), 1)

    def test_auto_bow_module_locates_slot_one_region_from_annotation_bbox_at_900p(self):
        frame = np.zeros((900, 1600, 3), dtype=np.uint8)
        region_match = self.task.auto_summon_module.locate_slot_one_region(frame)
        expected_box = self.task.auto_summon_module.build_slot_one_annotation_box(frame)

        self.assertEqual('result-json-first_summoned-bbox', region_match['reference_state'])
        self.assertEqual(1.0, region_match['score'])
        self.assertEqual(expected_box.x, region_match['box'].x)
        self.assertEqual(expected_box.y, region_match['box'].y)
        self.assertEqual(expected_box.width, region_match['box'].width)
        self.assertEqual(expected_box.height, region_match['box'].height)
        self.assertIsNone(region_match['anchor_box'])

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

        def record_wait_ocr(x=0, y=0, to_x=1, to_y=1, width=0, height=0, name=None, box=None, match=None,
                            threshold=0, frame=None, target_height=0, time_out=0, post_action=None,
                            raise_if_not_found=False, log=False, settle_time=-1, lib="default"):
            events.append(('wait_ocr', match, time_out, raise_if_not_found, log))
            return [match]

        self.task.send_key = record_send_key
        self.task.sleep = record_sleep
        self.task.interruptible_wait = record_sleep
        self.task.wait_ocr = record_wait_ocr
        self.task.auto_summon_module.run = lambda: events.append(('summon',))
        self.task.auto_bow_module.should_input_two_as_text = lambda: True
        self.task.auto_bow_module.get_tab_to_two_after_sleep = lambda: 12.68
        self.task.auto_bow_module.get_two_to_esc_after_sleep = lambda: 0.68
        self.task.auto_bow_module.get_loop_after_sleep = lambda: 2.68
        self.task.auto_bow_module.get_max_loop_count = lambda: 10
        og.device_manager.interaction.input_text = record_input_text

        self.task.auto_bow_module.run()

        expected_events = []
        for loop_index in range(1, 11):
            expected_events.append(('summon',))
            expected_events.append(('key', 'tab', 0.04, 0))
            expected_events.append(('wait_ocr', 'Tab', 1.0, False, True))
            expected_events.append(('sleep', 12.68))
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

        def record_wait_ocr(x=0, y=0, to_x=1, to_y=1, width=0, height=0, name=None, box=None, match=None,
                            threshold=0, frame=None, target_height=0, time_out=0, post_action=None,
                            raise_if_not_found=False, log=False, settle_time=-1, lib="default"):
            events.append(('wait_ocr', match, time_out, raise_if_not_found, log))
            return [match]

        self.task.send_key = raise_send_key
        self.task.sleep = record_sleep
        self.task.interruptible_wait = record_sleep
        self.task.wait_ocr = record_wait_ocr
        self.task.auto_summon_module.run = lambda: events.append(('summon',))
        self.task.auto_bow_module.should_input_two_as_text = lambda: True
        self.task.auto_bow_module.get_tab_to_two_after_sleep = lambda: 12.68
        self.task.auto_bow_module.get_two_to_esc_after_sleep = lambda: 0.68
        self.task.auto_bow_module.get_loop_after_sleep = lambda: 2.68
        self.task.auto_bow_module.get_max_loop_count = lambda: 10
        og.device_manager.interaction.input_text = record_input_text

        self.task.auto_bow_module.run()

        expected_events = []
        for loop_index in range(1, 11):
            expected_events.append(('summon',))
            expected_events.append(('key', 'tab', 0.04, 0))
            expected_events.append(('wait_ocr', 'Tab', 1.0, False, True))
            expected_events.append(('sleep', 12.68))
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
