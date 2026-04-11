import json
import random
import re
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from ok import Box, og


class AutoSummonModule:
    TEXT_INPUT_INTERACTIONS = {'PostMessageInteraction', 'ForegroundPostMessageInteraction'}
    MAIN_INTERFACE_HOTKEY_PATTERN = re.compile(r'F[2-6]')
    SLOT_SEQUENCE = (1, 2, 3, 4, 5, 6)
    SLOT_FEATURE_NAMES = {
        1: 'first_summoned',
        2: 'second_summoned',
        3: 'third_summoned',
        4: 'fourth_summoned',
        5: 'five_summoned',
        6: 'six_summoned',
    }
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
    SUMMON_RECHECK_WAIT = 0.30
    SUMMON_RETRY_INTERVAL = 10.0
    SLOT_SUMMONED_MATCH_MIN_CONFIDENCE = 0.80
    SLOT_ONE_SUMMONED_MATCH_MIN_CONFIDENCE = SLOT_SUMMONED_MATCH_MIN_CONFIDENCE
    SLOT_ONE_LOCATE_MIN_CONFIDENCE = 1.0
    SLOT_ICON_SEARCH_MARGIN_RATIO = 0.25
    DEBUG_OUTPUT_DIR = Path(__file__).resolve().parents[3] / '.tmp' / 'auto-summon-slot-debug'
    ANNOTATION_JSON_PATH = Path(__file__).resolve().parents[3] / 'assets' / 'result.json'

    def __init__(self, task):
        self.task = task
        annotation_data = self.load_summoned_annotations()
        self.annotation_image_size = (
            annotation_data['image_width'],
            annotation_data['image_height'],
        )
        self.slot_annotations = annotation_data['slots']
        self.reference_frame = self.load_reference_image(
            annotation_data['image_path'],
            '已标注源图',
        )
        self.slot_summoned_references = self.build_slot_summoned_references()
        self.slot_one_summoned_reference = self.slot_summoned_references[1]

    def validate_slot_number(self, slot_number):
        if not self.SLOT_MIN <= slot_number <= self.SLOT_MAX:
            raise ValueError(f'槽位编号必须在 {self.SLOT_MIN} 到 {self.SLOT_MAX} 之间')

    def get_feature_name(self, slot_number):
        self.validate_slot_number(slot_number)
        return self.SLOT_FEATURE_NAMES[slot_number]

    def ensure_summoned_feature_available(self, slot_number):
        feature_name = self.get_feature_name(slot_number)
        if not self.task.feature_exists(feature_name):
            raise RuntimeError(
                f'自动召唤模块: 未找到槽位{slot_number}的已召唤特征 {feature_name}，请检查 assets/result.json'
            )

    def ensure_all_summoned_features_available(self):
        for slot_number in self.SLOT_SEQUENCE:
            self.ensure_summoned_feature_available(slot_number)

    def ensure_slot_one_summoned_feature_available(self):
        self.ensure_summoned_feature_available(1)

    def get_key_after_sleep(self):
        return random.uniform(self.KEY_AFTER_SLEEP_MIN, self.KEY_AFTER_SLEEP_MAX)

    def get_click_after_sleep(self):
        return random.uniform(self.CLICK_AFTER_SLEEP_MIN, self.CLICK_AFTER_SLEEP_MAX)

    def should_input_slot_as_text(self):
        interaction = getattr(og.device_manager, 'interaction', None)
        return type(interaction).__name__ in self.TEXT_INPUT_INTERACTIONS

    def load_reference_image(self, image_path, state_name):
        image = cv2.imread(str(image_path), cv2.IMREAD_UNCHANGED)
        if image is None:
            raise FileNotFoundError(f'自动召唤模块: 未找到{state_name}参考图片: {image_path}')
        return self.normalize_bgr_image(image)

    def load_summoned_annotations(self):
        annotation_data = json.loads(self.ANNOTATION_JSON_PATH.read_text(encoding='utf-8'))
        category_by_id = {category['id']: category['name'] for category in annotation_data.get('categories', [])}
        image_by_id = {image['id']: image for image in annotation_data.get('images', [])}

        slots = {}
        image_info = None
        for slot_number, feature_name in self.SLOT_FEATURE_NAMES.items():
            target_annotation = None
            for annotation in annotation_data.get('annotations', []):
                if category_by_id.get(annotation.get('category_id')) == feature_name:
                    target_annotation = annotation
                    break
            if target_annotation is None:
                raise RuntimeError(
                    f'自动召唤模块: 未在 result.json 中找到槽位{slot_number}的已召唤标注 {feature_name}'
                )

            current_image_info = image_by_id.get(target_annotation.get('image_id'))
            if current_image_info is None:
                raise RuntimeError(
                    f'自动召唤模块: result.json 中槽位{slot_number}的已召唤标注缺少对应图片信息'
                )
            if image_info is None:
                image_info = current_image_info
            elif current_image_info['id'] != image_info['id']:
                raise RuntimeError('自动召唤模块: 当前仅支持所有已召唤标注来自同一张图片')

            bbox = target_annotation.get('bbox')
            if not bbox or len(bbox) != 4:
                raise RuntimeError(
                    f'自动召唤模块: result.json 中槽位{slot_number}的已召唤标注 bbox 无效'
                )

            slots[slot_number] = {
                'feature_name': feature_name,
                'bbox': tuple(float(value) for value in bbox),
            }

        if image_info is None:
            raise RuntimeError('自动召唤模块: result.json 中缺少已召唤标注图片信息')

        return {
            'image_path': self.ANNOTATION_JSON_PATH.parent / image_info['file_name'],
            'image_width': int(image_info['width']),
            'image_height': int(image_info['height']),
            'slots': slots,
        }

    def normalize_bgr_image(self, image):
        if image is None:
            raise RuntimeError('自动召唤模块: 图像为空，无法识别精灵召唤状态')
        if len(image.shape) == 2:
            return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        if image.shape[2] == 4:
            return cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
        return image

    def get_current_frame(self):
        frame = self.task.frame
        if frame is None:
            raise RuntimeError('自动召唤模块: 当前帧为空，无法识别精灵召唤状态')
        return self.normalize_bgr_image(frame.copy())

    def resize_reference_for_frame(self, frame, image, interpolation=None):
        frame_height, frame_width = frame.shape[:2]
        scale_x = frame_width / self.annotation_image_size[0]
        scale_y = frame_height / self.annotation_image_size[1]
        width = max(1, int(round(image.shape[1] * scale_x)))
        height = max(1, int(round(image.shape[0] * scale_y)))
        if interpolation is None:
            interpolation = cv2.INTER_AREA if width < image.shape[1] or height < image.shape[0] else cv2.INTER_LINEAR
        return cv2.resize(image, (width, height), interpolation=interpolation)

    def annotation_bbox_to_box(self, bbox, width, height, name):
        left = int(round(bbox[0]))
        top = int(round(bbox[1]))
        box_width = max(1, int(round(bbox[2])))
        box_height = max(1, int(round(bbox[3])))
        left = max(0, min(width - box_width, left))
        top = max(0, min(height - box_height, top))
        box_width = max(1, min(width - left, box_width))
        box_height = max(1, min(height - top, box_height))
        return Box(left, top, box_width, box_height, confidence=1.0, name=name)

    def build_slot_summoned_references(self):
        references = {}
        frame_height, frame_width = self.reference_frame.shape[:2]
        for slot_number, slot_data in self.slot_annotations.items():
            box = self.annotation_bbox_to_box(
                slot_data['bbox'],
                frame_width,
                frame_height,
                name=f'slot-{slot_number}-reference',
            )
            references[slot_number] = box.crop_frame(self.reference_frame).copy()
        return references

    def build_slot_annotation_box(self, frame, slot_number):
        slot_data = self.slot_annotations[slot_number]
        frame_height, frame_width = frame.shape[:2]
        scale_x = frame_width / self.annotation_image_size[0]
        scale_y = frame_height / self.annotation_image_size[1]
        bbox = slot_data['bbox']
        left = int(round(bbox[0] * scale_x))
        top = int(round(bbox[1] * scale_y))
        width = max(1, int(round(bbox[2] * scale_x)))
        height = max(1, int(round(bbox[3] * scale_y)))
        left = max(0, min(frame_width - width, left))
        top = max(0, min(frame_height - height, top))
        width = max(1, min(frame_width - left, width))
        height = max(1, min(frame_height - top, height))
        return Box(
            left,
            top,
            width,
            height,
            confidence=1.0,
            name=f'slot-{slot_number}-{slot_data["feature_name"]}-annotation',
        )

    def build_slot_one_annotation_box(self, frame):
        return self.build_slot_annotation_box(frame, 1)

    def ensure_debug_output_dir(self):
        self.DEBUG_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        return self.DEBUG_OUTPUT_DIR

    def prepare_debug_dump_dir(self):
        debug_root = self.ensure_debug_output_dir()
        dump_dir = debug_root / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
        dump_dir.mkdir(parents=True, exist_ok=True)
        return dump_dir

    def is_main_interface(self):
        self.task.checkpoint()
        self.task.log_info('自动召唤模块: OCR识别当前界面是否存在 F2/F3 等快捷键文字')
        result = self.task.ocr(match=self.MAIN_INTERFACE_HOTKEY_PATTERN, log=True)
        if result:
            self.task.log_info('自动召唤模块: 已识别到 F2/F3 等快捷键文字，判定当前为主界面')
        else:
            self.task.log_info('自动召唤模块: 未识别到 F2/F3 等快捷键文字，判定当前不是主界面')
        return bool(result)

    def save_debug_image(self, output_path, image):
        if not cv2.imwrite(str(output_path), image):
            raise RuntimeError(f'自动召唤模块: 调试图片写入失败: {output_path}')

    def dump_slot_state_debug_artifacts(
        self,
        slot_number,
        frame,
        region_match,
        icon_search_box,
        expected_icon_box,
        icon_patch,
        summoned_match,
        score,
        state,
        reason,
        error_message=None,
    ):
        self.task.checkpoint()
        dump_dir = self.prepare_debug_dump_dir()
        feature_name = self.get_feature_name(slot_number)

        frame_with_boxes = frame.copy()
        cv2.rectangle(
            frame_with_boxes,
            (region_match['box'].x, region_match['box'].y),
            (region_match['box'].x + region_match['box'].width, region_match['box'].y + region_match['box'].height),
            (0, 255, 255),
            2,
        )
        cv2.rectangle(
            frame_with_boxes,
            (expected_icon_box.x, expected_icon_box.y),
            (expected_icon_box.x + expected_icon_box.width, expected_icon_box.y + expected_icon_box.height),
            (0, 128, 255),
            2,
        )
        cv2.rectangle(
            frame_with_boxes,
            (icon_search_box.x, icon_search_box.y),
            (icon_search_box.x + icon_search_box.width, icon_search_box.y + icon_search_box.height),
            (255, 255, 0),
            1,
        )
        if summoned_match is not None:
            cv2.rectangle(
                frame_with_boxes,
                (summoned_match.x, summoned_match.y),
                (summoned_match.x + summoned_match.width, summoned_match.y + summoned_match.height),
                (0, 255, 0),
                2,
            )

        self.save_debug_image(dump_dir / 'frame.png', frame)
        self.save_debug_image(dump_dir / 'frame-boxes.png', frame_with_boxes)
        self.save_debug_image(dump_dir / 'search-region.png', region_match['search_frame'])
        self.save_debug_image(dump_dir / 'slot-region.png', region_match['region_frame'])
        self.save_debug_image(dump_dir / 'locator-template.png', region_match['template'])
        self.save_debug_image(dump_dir / 'locator-mask.png', region_match['mask'])
        self.save_debug_image(dump_dir / 'locator-matched-patch.png', region_match['matched_patch'])
        self.save_debug_image(dump_dir / 'icon-patch.png', icon_patch)

        metadata = {
            'slot_number': slot_number,
            'feature_name': feature_name,
            'reason': reason,
            'error_message': error_message,
            'locate_score': region_match['score'],
            'locate_reference_state': region_match['reference_state'],
            'score': score,
            'state': state,
            'region_box': {
                'x': region_match['box'].x,
                'y': region_match['box'].y,
                'width': region_match['box'].width,
                'height': region_match['box'].height,
            },
            'search_box': {
                'x': region_match['search_box'].x,
                'y': region_match['search_box'].y,
                'width': region_match['search_box'].width,
                'height': region_match['search_box'].height,
            },
            'expected_icon_box': {
                'x': expected_icon_box.x,
                'y': expected_icon_box.y,
                'width': expected_icon_box.width,
                'height': expected_icon_box.height,
            },
            'icon_search_box': {
                'x': icon_search_box.x,
                'y': icon_search_box.y,
                'width': icon_search_box.width,
                'height': icon_search_box.height,
            },
            'match_box': None,
        }
        if summoned_match is not None:
            matched_patch = summoned_match.crop_frame(frame)
            self.save_debug_image(dump_dir / 'summoned-matched-patch.png', matched_patch)
            metadata['match_box'] = {
                'x': summoned_match.x,
                'y': summoned_match.y,
                'width': summoned_match.width,
                'height': summoned_match.height,
                'confidence': summoned_match.confidence,
            }

        (dump_dir / 'metadata.json').write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2),
            encoding='utf-8',
        )
        self.task.log_info(f'自动召唤模块: 槽位{slot_number}状态调试材料已输出: {dump_dir}')
        return dump_dir

    def locate_slot_region(self, frame, slot_number):
        self.task.checkpoint()
        feature_name = self.get_feature_name(slot_number)
        box = self.build_slot_annotation_box(frame, slot_number)
        region_frame = box.crop_frame(frame).copy()
        mask = np.full(region_frame.shape[:2], 255, dtype=np.uint8)
        return {
            'slot_number': slot_number,
            'feature_name': feature_name,
            'reference_state': f'result-json-{feature_name}-bbox',
            'score': 1.0,
            'box': box,
            'anchor_box': None,
            'template': region_frame.copy(),
            'mask': mask,
            'matched_patch': region_frame.copy(),
            'region_frame': region_frame,
            'search_box': box,
            'search_frame': region_frame.copy(),
        }

    def locate_slot_one_region(self, frame):
        return self.locate_slot_region(frame, 1)

    def try_locate_slot_region(self, frame=None, slot_number=1):
        self.task.checkpoint()
        frame = self.get_current_frame() if frame is None else self.normalize_bgr_image(frame)
        region_match = self.locate_slot_region(frame, slot_number)
        return frame, region_match, region_match['score'] >= self.SLOT_SUMMONED_MATCH_MIN_CONFIDENCE

    def try_locate_slot_one_region(self, frame=None):
        return self.try_locate_slot_region(frame=frame, slot_number=1)

    def build_absolute_icon_box(self, region_box):
        return Box(
            region_box.x,
            region_box.y,
            region_box.width,
            region_box.height,
            confidence=region_box.confidence,
            name='slot-summoned-icon',
        )

    def clamp_box_to_frame(self, box, frame_width, frame_height):
        left = max(0, box.x)
        top = max(0, box.y)
        right = min(frame_width, box.x + box.width)
        bottom = min(frame_height, box.y + box.height)
        return Box(
            left,
            top,
            max(1, right - left),
            max(1, bottom - top),
            confidence=box.confidence,
            name=box.name,
        )

    def extract_slot_icon_patch(self, frame, expected_icon_box):
        frame_height, frame_width = frame.shape[:2]
        margin_x = max(2, int(round(expected_icon_box.width * self.SLOT_ICON_SEARCH_MARGIN_RATIO)))
        margin_y = max(2, int(round(expected_icon_box.height * self.SLOT_ICON_SEARCH_MARGIN_RATIO)))
        search_box = self.clamp_box_to_frame(
            expected_icon_box.copy(
                x_offset=-margin_x,
                y_offset=-margin_y,
                width_offset=margin_x * 2,
                height_offset=margin_y * 2,
                name='slot-summoned-icon-search',
            ),
            frame_width,
            frame_height,
        )
        return search_box.crop_frame(frame).copy(), search_box

    def find_slot_summoned_match(self, slot_number, frame, icon_search_box):
        self.task.checkpoint()
        feature_name = self.get_feature_name(slot_number)
        self.ensure_summoned_feature_available(slot_number)
        match = self.task.find_one(
            feature_name,
            box=icon_search_box,
            threshold=0,
            frame=frame,
            use_gray_scale=False,
        )
        if match is None:
            return None
        return Box(
            match.x,
            match.y,
            match.width,
            match.height,
            confidence=float(match.confidence),
            name=f'slot-{slot_number}-summoned-feature',
        )

    def find_slot_one_summoned_match(self, frame, icon_search_box):
        return self.find_slot_summoned_match(1, frame, icon_search_box)

    def detect_slot_summon_state(self, slot_number, frame=None, region_match=None):
        self.task.checkpoint()
        slot_number = int(slot_number)
        self.validate_slot_number(slot_number)
        frame = self.get_current_frame() if frame is None else self.normalize_bgr_image(frame)
        region_match = self.locate_slot_region(frame, slot_number) if region_match is None else region_match
        feature_name = self.get_feature_name(slot_number)
        expected_icon_box = region_match['box']
        icon_patch, icon_search_box = self.extract_slot_icon_patch(frame, expected_icon_box)
        try:
            summoned_match = self.find_slot_summoned_match(slot_number, frame, icon_search_box)
        except Exception as error:
            debug_dir = self.dump_slot_state_debug_artifacts(
                slot_number=slot_number,
                frame=frame,
                region_match=region_match,
                icon_search_box=icon_search_box,
                expected_icon_box=expected_icon_box,
                icon_patch=icon_patch,
                summoned_match=None,
                score=0.0,
                state='error',
                reason='detect_exception',
                error_message=str(error),
            )
            raise RuntimeError(
                f'自动召唤模块: 槽位{slot_number}状态识别异常: {error}，调试目录: {debug_dir}'
            ) from error

        score = 0.0 if summoned_match is None else float(summoned_match.confidence)
        state = 'summoned' if score >= self.SLOT_SUMMONED_MATCH_MIN_CONFIDENCE else 'unsummoned'
        self.task.log_info(
            f'自动召唤模块: 槽位{slot_number}精灵状态识别完成, '
            f"区域参考={region_match['reference_state']}, 区域分数={region_match['score']:.3f}, "
            f'已召唤特征={feature_name}, 已召唤特征分数={score:.3f}, 判定状态={state}'
        )
        return {
            'slot_number': slot_number,
            'feature_name': feature_name,
            'state': state,
            'score': score,
            'box': summoned_match or expected_icon_box,
            'region_box': region_match['box'],
            'locate_score': region_match['score'],
        }

    def detect_slot_one_summon_state(self, frame=None, region_match=None):
        return self.detect_slot_summon_state(1, frame=frame, region_match=region_match)

    def detect_all_slot_summon_states(self, frame=None, suppress_exceptions=False):
        frame = self.get_current_frame() if frame is None else self.normalize_bgr_image(frame)
        results = {}
        errors = {}
        for slot_number in self.SLOT_SEQUENCE:
            try:
                results[slot_number] = self.detect_slot_summon_state(slot_number, frame=frame)
            except Exception as error:
                errors[slot_number] = error
                if not suppress_exceptions:
                    raise
        return frame, results, errors

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
            send_result = self.task.send_key(slot_text, down_time=self.KEY_DOWN_TIME, after_sleep=0)
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

    def summon_slot_until_summoned(self, slot_number):
        attempt = 1
        while True:
            self.task.log_info(f'自动召唤模块: 槽位{slot_number} 开始召唤确认流程，第{attempt}次尝试')
            self.run_slot(slot_number)
            if self.SUMMON_RECHECK_WAIT > 0:
                self.task.interruptible_wait(self.SUMMON_RECHECK_WAIT)
            try:
                match = self.detect_slot_summon_state(slot_number)
            except Exception as error:
                self.task.log_info(
                    f'自动召唤模块: 槽位{slot_number} 召唤后状态识别异常: {error}，'
                    f'{self.SUMMON_RETRY_INTERVAL:.0f}秒后重试'
                )
                self.task.interruptible_wait(self.SUMMON_RETRY_INTERVAL)
                attempt += 1
                continue

            if match['state'] == 'summoned':
                self.task.log_info(
                    f'自动召唤模块: 槽位{slot_number} 已识别为已召唤，匹配分数={match["score"]:.3f}'
                )
                return match

            self.task.log_info(
                f'自动召唤模块: 槽位{slot_number} 仍未识别为已召唤，'
                f'匹配分数={match["score"]:.3f}，{self.SUMMON_RETRY_INTERVAL:.0f}秒后重试'
            )
            self.task.interruptible_wait(self.SUMMON_RETRY_INTERVAL)
            attempt += 1

    def run_full_summon_sequence(self, slot_numbers=None):
        if slot_numbers is None:
            slot_numbers = self.SLOT_SEQUENCE
        for slot_number in slot_numbers:
            self.task.checkpoint()
            self.task.log_info(f'自动召唤模块: 准备依次召唤槽位{slot_number}')
            self.summon_slot_until_summoned(slot_number)

    def ensure_all_slots_summoned(self):
        round_index = 1
        while True:
            _, results, errors = self.detect_all_slot_summon_states(suppress_exceptions=True)
            unsummoned_slots = [
                slot_number
                for slot_number in self.SLOT_SEQUENCE
                if results.get(slot_number, {}).get('state') != 'summoned'
            ]
            retry_slots = sorted(set(unsummoned_slots + list(errors.keys())))
            if not retry_slots:
                self.task.log_info('自动召唤模块: 6个槽位已全部识别为已召唤，自动召唤流程完成')
                return results

            if errors:
                error_slots = ', '.join(str(slot_number) for slot_number in sorted(errors))
                self.task.log_info(f'自动召唤模块: 第{round_index}轮全量复检存在识别异常槽位: {error_slots}')
            if unsummoned_slots:
                unsummoned_desc = ', '.join(str(slot_number) for slot_number in unsummoned_slots)
                self.task.log_info(f'自动召唤模块: 第{round_index}轮全量复检发现未召唤槽位: {unsummoned_desc}')

            for slot_number in retry_slots:
                self.task.log_info(f'自动召唤模块: 对槽位{slot_number}执行补召流程')
                self.summon_slot_until_summoned(slot_number)
            round_index += 1

    def run(self):
        if not self.is_main_interface():
            self.task.log_info('自动召唤模块: 当前界面不是主界面，跳过自动召唤模块')
            return

        _, results, errors = self.detect_all_slot_summon_states(suppress_exceptions=True)
        if not errors and all(results[slot]['state'] == 'summoned' for slot in self.SLOT_SEQUENCE):
            self.task.log_info('自动召唤模块: 6个槽位均已识别为已召唤，跳过自动召唤模块')
            return

        if errors:
            error_slots = ', '.join(str(slot_number) for slot_number in sorted(errors))
            target_slots = sorted(errors)
            self.task.log_info(f'自动召唤模块: 预检查存在识别异常槽位: {error_slots}，继续执行全量召唤流程')
        else:
            unsummoned_slots = [
                slot_number
                for slot_number in self.SLOT_SEQUENCE
                if results[slot_number]['state'] != 'summoned'
            ]
            target_slots = unsummoned_slots
            unsummoned_desc = ', '.join(str(slot_number) for slot_number in unsummoned_slots)
            self.task.log_info(f'自动召唤模块: 预检查发现未召唤槽位: {unsummoned_desc}，开始执行全量召唤流程')

        self.run_full_summon_sequence(target_slots)
        self.ensure_all_slots_summoned()
