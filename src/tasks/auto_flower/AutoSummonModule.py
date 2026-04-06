import json
import random
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from ok import Box, og


class AutoSummonModule:
    TEXT_INPUT_INTERACTIONS = {'PostMessageInteraction', 'ForegroundPostMessageInteraction'}
    MAIN_INTERFACE_HOTKEY_PATTERN = re.compile(r'F[2-6]')
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
    SUMMON_RECHECK_WAIT = 0.30
    REFERENCE_WIDTH = 1920
    REFERENCE_HEIGHT = 1080
    SLOT_ONE_ICON_RELATIVE_BOX = (0.52, 0.02, 0.40, 0.38)
    SLOT_ONE_SEARCH_REGION = (0.00, 0.02, 0.16, 0.20)
    SLOT_ONE_LOCATE_MIN_CONFIDENCE = 0.45
    SLOT_ONE_STATE_MIN_CONFIDENCE = 0.45
    SLOT_ONE_ICON_LOCATE_MIN_CONFIDENCE = 0.70
    SLOT_ONE_ICON_SEARCH_MARGIN_RATIO = 0.25
    SLOT_ONE_ANCHOR_WHITE_VALUE_MIN = 180
    SLOT_ONE_ANCHOR_WHITE_SATURATION_MAX = 70
    SLOT_ONE_ANCHOR_SEARCH_SCORE_TOLERANCE = 0.02
    PROJECT_ROOT = Path(__file__).resolve().parents[3]
    DEBUG_OUTPUT_DIR = PROJECT_ROOT / '.tmp' / 'auto-summon-slot-one-debug'
    LATEST_DEBUG_OUTPUT_DIR = DEBUG_OUTPUT_DIR / 'latest'
    SLOT_ONE_UNSUMMONED_REFERENCE_PATH = PROJECT_ROOT / 'assets' / 'unsummoned.png'
    SLOT_ONE_SUMMONED_REFERENCE_PATH = PROJECT_ROOT / 'assets' / 'summoned.png'
    SLOT_ONE_SUMMONED_ICON_PATH = PROJECT_ROOT / 'assets' / 'summoned-icon.png'

    def __init__(self, task):
        self.task = task
        self.slot_one_unsummoned_reference = self.load_reference_image(
            self.SLOT_ONE_UNSUMMONED_REFERENCE_PATH,
            '未召唤',
        )
        self.slot_one_summoned_reference = self.load_reference_image(
            self.SLOT_ONE_SUMMONED_REFERENCE_PATH,
            '已召唤',
        )
        self.slot_one_locator_reference = self.slot_one_summoned_reference
        self.slot_one_summoned_icon_reference = self.load_reference_image(
            self.SLOT_ONE_SUMMONED_ICON_PATH,
            '已召唤图标',
        )
        self.slot_one_icon_relative_box = self.detect_slot_one_icon_relative_box(
            self.slot_one_summoned_reference,
            self.slot_one_summoned_icon_reference,
        )
        self.slot_one_anchor_relative_box = self.detect_slot_one_anchor_relative_box(
            self.slot_one_summoned_reference,
        )
        self.slot_one_anchor_reference = self.crop_relative_box(
            self.slot_one_summoned_reference,
            self.slot_one_anchor_relative_box,
        )
        self.slot_one_anchor_mask = self.build_slot_one_anchor_mask(
            self.slot_one_anchor_reference,
        )
        self.slot_one_icon_references = {
            'unsummoned': self.crop_relative_box(
                self.slot_one_unsummoned_reference,
                self.slot_one_icon_relative_box,
            ),
            'summoned': self.normalize_bgr_image(self.slot_one_summoned_icon_reference),
        }

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

    def load_reference_image(self, image_path, state_name):
        image = cv2.imread(str(image_path), cv2.IMREAD_UNCHANGED)
        if image is None:
            raise FileNotFoundError(f'自动召唤模块: 未找到1号位精灵{state_name}参考图片: {image_path}')
        return self.normalize_bgr_image(image)

    def normalize_bgr_image(self, image):
        if image is None:
            raise RuntimeError('自动召唤模块: 图像为空，无法识别1号位精灵召唤状态')
        if len(image.shape) == 2:
            return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        if image.shape[2] == 4:
            return cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
        return image

    def get_current_frame(self):
        frame = self.task.frame
        if frame is None:
            raise RuntimeError('自动召唤模块: 当前帧为空，无法识别1号位精灵召唤状态')
        return self.normalize_bgr_image(frame.copy())

    def resize_reference_for_frame(self, frame, image, interpolation=None):
        frame_height, frame_width = frame.shape[:2]
        scale_x = frame_width / self.REFERENCE_WIDTH
        scale_y = frame_height / self.REFERENCE_HEIGHT
        width = max(1, int(round(image.shape[1] * scale_x)))
        height = max(1, int(round(image.shape[0] * scale_y)))
        if interpolation is None:
            interpolation = cv2.INTER_AREA if width < image.shape[1] or height < image.shape[0] else cv2.INTER_LINEAR
        return cv2.resize(image, (width, height), interpolation=interpolation)

    def relative_box_to_rect(self, width, height, relative_box):
        relative_x, relative_y, relative_width, relative_height = relative_box
        left = max(0, min(width - 1, int(round(width * relative_x))))
        top = max(0, min(height - 1, int(round(height * relative_y))))
        right = max(left + 1, min(width, int(round(width * (relative_x + relative_width)))))
        bottom = max(top + 1, min(height, int(round(height * (relative_y + relative_height)))))
        return left, top, right - left, bottom - top

    def crop_relative_box(self, image, relative_box):
        height, width = image.shape[:2]
        left, top, crop_width, crop_height = self.relative_box_to_rect(width, height, relative_box)
        return image[top:top + crop_height, left:left + crop_width].copy()

    def detect_slot_one_icon_relative_box(self, reference_image, icon_image):
        reference_gray = cv2.cvtColor(reference_image, cv2.COLOR_BGR2GRAY)
        icon_gray = cv2.cvtColor(icon_image, cv2.COLOR_BGR2GRAY)
        if (
            reference_gray.shape[0] < icon_gray.shape[0]
            or reference_gray.shape[1] < icon_gray.shape[1]
        ):
            raise RuntimeError('自动召唤模块: 已召唤图标尺寸大于1号位精灵参考图尺寸')
        result = cv2.matchTemplate(reference_gray, icon_gray, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        if max_val < self.SLOT_ONE_ICON_LOCATE_MIN_CONFIDENCE:
            raise RuntimeError(
                '自动召唤模块: 无法在1号位精灵已召唤参考图中定位右上角已召唤图标，'
                f'匹配分数={max_val:.3f}'
            )
        reference_height, reference_width = reference_image.shape[:2]
        icon_height, icon_width = icon_image.shape[:2]
        return (
            max_loc[0] / reference_width,
            max_loc[1] / reference_height,
            icon_width / reference_width,
            icon_height / reference_height,
        )

    def build_white_anchor_mask(self, image):
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(
            hsv,
            (0, 0, self.SLOT_ONE_ANCHOR_WHITE_VALUE_MIN),
            (180, self.SLOT_ONE_ANCHOR_WHITE_SATURATION_MAX, 255),
        )
        mask = cv2.medianBlur(mask, 3)
        return mask

    def detect_slot_one_anchor_relative_box(self, reference_image):
        mask = self.build_white_anchor_mask(reference_image)
        height, width = reference_image.shape[:2]
        mask[:, int(round(width * 0.45)):] = 0
        num_labels, _, stats, _ = cv2.connectedComponentsWithStats(mask)
        best_box = None
        best_area = -1
        for label in range(1, num_labels):
            x, y, box_width, box_height, area = stats[label]
            if area < 120:
                continue
            if x > int(round(width * 0.25)):
                continue
            aspect_ratio = box_width / max(1, box_height)
            if not 0.6 <= aspect_ratio <= 1.6:
                continue
            if area > best_area:
                best_area = int(area)
                best_box = (int(x), int(y), int(box_width), int(box_height))
        if best_box is None:
            raise RuntimeError('自动召唤模块: 无法在1号位精灵参考图中定位左侧数字1圆圈')
        x, y, box_width, box_height = best_box
        margin_x = max(2, int(round(width * 0.02)))
        margin_y = max(2, int(round(height * 0.02)))
        left = max(0, x - margin_x)
        top = max(0, y - margin_y)
        right = min(width, x + box_width + margin_x)
        bottom = min(height, y + box_height + margin_y)
        return (
            left / width,
            top / height,
            (right - left) / width,
            (bottom - top) / height,
        )

    def build_slot_one_anchor_mask(self, anchor_image):
        mask = np.full(anchor_image.shape[:2], 255, dtype=np.uint8)
        return mask

    def find_topmost_best_match_location(self, result, prefer='min'):
        tolerance = self.SLOT_ONE_ANCHOR_SEARCH_SCORE_TOLERANCE
        if prefer == 'max':
            best_val = float(np.max(result))
            candidate_locations = np.argwhere(result >= best_val - tolerance)
            score = best_val
        else:
            best_val = float(np.min(result))
            candidate_locations = np.argwhere(result <= best_val + tolerance)
            score = best_val
        if candidate_locations.size == 0:
            raise RuntimeError('自动召唤模块: 左侧数字1圆圈匹配结果为空')
        topmost = min(candidate_locations.tolist(), key=lambda location: (location[0], location[1]))
        return score, (int(topmost[1]), int(topmost[0]))

    def build_search_box(self, frame):
        frame_height, frame_width = frame.shape[:2]
        left, top, width, height = self.relative_box_to_rect(
            frame_width,
            frame_height,
            self.SLOT_ONE_SEARCH_REGION,
        )
        return Box(left, top, width, height, name='slot-one-search-region')

    def ensure_debug_output_dir(self):
        self.DEBUG_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        return self.DEBUG_OUTPUT_DIR

    def prepare_debug_dump_dir(self, latest=False):
        if latest:
            if self.LATEST_DEBUG_OUTPUT_DIR.exists():
                shutil.rmtree(self.LATEST_DEBUG_OUTPUT_DIR)
            self.LATEST_DEBUG_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            return self.LATEST_DEBUG_OUTPUT_DIR
        debug_root = self.ensure_debug_output_dir()
        dump_dir = debug_root / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
        dump_dir.mkdir(parents=True, exist_ok=True)
        return dump_dir

    def should_dump_every_check_debug_artifacts(self):
        entry_name = Path(sys.argv[0]).name.lower() if sys.argv else ''
        return entry_name == 'main_debug.py'

    def is_main_interface(self):
        self.task.checkpoint()
        self.task.log_info('自动召唤模块: OCR识别当前界面是否存在 F2/F3 等快捷键文字')
        result = self.task.ocr(
            match=self.MAIN_INTERFACE_HOTKEY_PATTERN,
            log=True,
        )
        if result:
            self.task.log_info('自动召唤模块: 已识别到 F2/F3 等快捷键文字，判定当前为主界面')
        else:
            self.task.log_info('自动召唤模块: 未识别到 F2/F3 等快捷键文字，判定当前不是主界面')
        return bool(result)

    def save_debug_image(self, output_path, image):
        if not cv2.imwrite(str(output_path), image):
            raise RuntimeError(f'自动召唤模块: 调试图片写入失败: {output_path}')

    def dump_slot_one_state_debug_artifacts(self, frame, region_match, icon_patch, icon_matches, scores, reason, latest=False):
        self.task.checkpoint()
        dump_dir = self.prepare_debug_dump_dir(latest=latest)

        frame_with_boxes = frame.copy()
        cv2.rectangle(
            frame_with_boxes,
            (region_match['box'].x, region_match['box'].y),
            (region_match['box'].x + region_match['box'].width, region_match['box'].y + region_match['box'].height),
            (0, 255, 255),
            2,
        )
        anchor_box = region_match.get('anchor_box')
        if anchor_box is not None:
            cv2.rectangle(
                frame_with_boxes,
                (anchor_box.x, anchor_box.y),
                (anchor_box.x + anchor_box.width, anchor_box.y + anchor_box.height),
                (255, 0, 255),
                2,
            )
        for match in icon_matches:
            box = match['box']
            color = (0, 255, 0) if match['state'] == 'summoned' else (0, 128, 255)
            cv2.rectangle(
                frame_with_boxes,
                (box.x, box.y),
                (box.x + box.width, box.y + box.height),
                color,
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
            'reason': reason,
            'locate_score': region_match['score'],
            'locate_reference_state': region_match['reference_state'],
            'scores': {
                'unsummoned': scores['unsummoned'],
                'summoned': scores['summoned'],
            },
            'region_box': {
                'x': region_match['box'].x,
                'y': region_match['box'].y,
                'width': region_match['box'].width,
                'height': region_match['box'].height,
            },
            'anchor_box': None,
            'search_box': {
                'x': region_match['search_box'].x,
                'y': region_match['search_box'].y,
                'width': region_match['search_box'].width,
                'height': region_match['search_box'].height,
            },
            'templates': {
                'locator': str(self.SLOT_ONE_SUMMONED_REFERENCE_PATH),
                'unsummoned': str(self.SLOT_ONE_UNSUMMONED_REFERENCE_PATH),
                'summoned': str(self.SLOT_ONE_SUMMONED_ICON_PATH),
            },
            'matches': {},
        }
        if anchor_box is not None:
            metadata['anchor_box'] = {
                'x': anchor_box.x,
                'y': anchor_box.y,
                'width': anchor_box.width,
                'height': anchor_box.height,
            }

        for match in icon_matches:
            state = match['state']
            self.save_debug_image(dump_dir / f'{state}-icon-template.png', match['template'])
            self.save_debug_image(dump_dir / f'{state}-matched-patch.png', match['matched_patch'])
            metadata['matches'][state] = {
                'score': match['score'],
                'box': {
                    'x': match['box'].x,
                    'y': match['box'].y,
                    'width': match['box'].width,
                    'height': match['box'].height,
                },
            }

        (dump_dir / 'metadata.json').write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2),
            encoding='utf-8',
        )
        if not latest:
            self.task.log_info(f'自动召唤模块: 1号位精灵状态调试材料已输出: {dump_dir}')
        return dump_dir

    def locate_slot_one_region(self, frame):
        self.task.checkpoint()
        search_box = self.build_search_box(frame)
        search_frame = frame[
            search_box.y:search_box.y + search_box.height,
            search_box.x:search_box.x + search_box.width,
        ].copy()
        frame_gray = cv2.cvtColor(search_frame, cv2.COLOR_BGR2GRAY)
        template = self.resize_reference_for_frame(frame, self.slot_one_locator_reference)
        anchor_template = self.resize_reference_for_frame(frame, self.slot_one_anchor_reference)
        anchor_mask = self.resize_reference_for_frame(
            frame,
            self.slot_one_anchor_mask,
            interpolation=cv2.INTER_NEAREST,
        )
        template_gray = cv2.cvtColor(anchor_template, cv2.COLOR_BGR2GRAY)
        if (
            frame_gray.shape[0] < template_gray.shape[0]
            or frame_gray.shape[1] < template_gray.shape[1]
        ):
            raise RuntimeError('自动召唤模块: 当前帧尺寸小于1号位精灵左侧数字1圆圈参考图尺寸')
        result = cv2.matchTemplate(frame_gray, template_gray, cv2.TM_CCOEFF_NORMED)
        result = np.nan_to_num(result, nan=0.0, posinf=0.0, neginf=0.0)
        max_val, min_loc = self.find_topmost_best_match_location(result, prefer='max')
        score = max(0.0, float(max_val))
        anchor_offset_left, anchor_offset_top, _, _ = self.relative_box_to_rect(
            template.shape[1],
            template.shape[0],
            self.slot_one_anchor_relative_box,
        )
        region_left = int(search_box.x + min_loc[0] - anchor_offset_left)
        region_top = int(search_box.y + min_loc[1] - anchor_offset_top)
        frame_height, frame_width = frame.shape[:2]
        region_left = max(0, min(frame_width - template.shape[1], region_left))
        region_top = max(0, min(frame_height - template.shape[0], region_top))
        anchor_box = Box(
            int(search_box.x + min_loc[0]),
            int(search_box.y + min_loc[1]),
            int(template_gray.shape[1]),
            int(template_gray.shape[0]),
            confidence=score,
            name='slot-one-anchor',
        )
        box = Box(
            region_left,
            region_top,
            int(template.shape[1]),
            int(template.shape[0]),
            confidence=score,
            name='slot-one-region',
        )
        anchor_frame = frame[
            anchor_box.y:anchor_box.y + anchor_box.height,
            anchor_box.x:anchor_box.x + anchor_box.width,
        ].copy()
        region_frame = frame[box.y:box.y + box.height, box.x:box.x + box.width].copy()
        return {
            'reference_state': 'slot-one-anchor-circle',
            'score': score,
            'box': box,
            'anchor_box': anchor_box,
            'template': anchor_template.copy(),
            'mask': anchor_mask.copy(),
            'matched_patch': anchor_frame,
            'region_frame': region_frame,
            'search_box': search_box,
            'search_frame': search_frame,
        }

    def try_locate_slot_one_region(self, frame=None):
        self.task.checkpoint()
        frame = self.get_current_frame() if frame is None else self.normalize_bgr_image(frame)
        region_match = self.locate_slot_one_region(frame)
        is_visible = region_match['score'] >= self.SLOT_ONE_LOCATE_MIN_CONFIDENCE
        return frame, region_match, is_visible

    def build_absolute_icon_box(self, region_box):
        left, top, width, height = self.relative_box_to_rect(
            region_box.width,
            region_box.height,
            self.slot_one_icon_relative_box,
        )
        return Box(
            region_box.x + left,
            region_box.y + top,
            width,
            height,
            name='slot-one-icon',
        )

    def extract_slot_one_icon_patch(self, frame, region_box):
        expected_icon_box = self.build_absolute_icon_box(region_box)
        frame_height, frame_width = frame.shape[:2]
        margin_x = max(2, int(round(expected_icon_box.width * self.SLOT_ONE_ICON_SEARCH_MARGIN_RATIO)))
        margin_y = max(2, int(round(expected_icon_box.height * self.SLOT_ONE_ICON_SEARCH_MARGIN_RATIO)))
        search_left = max(0, expected_icon_box.x - margin_x)
        search_top = max(0, expected_icon_box.y - margin_y)
        search_right = min(frame_width, expected_icon_box.x + expected_icon_box.width + margin_x)
        search_bottom = min(frame_height, expected_icon_box.y + expected_icon_box.height + margin_y)
        search_box = Box(
            search_left,
            search_top,
            search_right - search_left,
            search_bottom - search_top,
            name='slot-one-icon-search',
        )
        patch = frame[
            search_box.y:search_box.y + search_box.height,
            search_box.x:search_box.x + search_box.width,
        ].copy()
        return patch, search_box, expected_icon_box

    def match_slot_one_icon_patch(self, icon_patch, icon_search_box, expected_icon_box, reference_icon, state_name):
        interpolation = (
            cv2.INTER_AREA
            if expected_icon_box.width < reference_icon.shape[1] or expected_icon_box.height < reference_icon.shape[0]
            else cv2.INTER_LINEAR
        )
        template = cv2.resize(
            reference_icon,
            (expected_icon_box.width, expected_icon_box.height),
            interpolation=interpolation,
        )
        patch_gray = cv2.cvtColor(icon_patch, cv2.COLOR_BGR2GRAY)
        template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
        result = cv2.matchTemplate(patch_gray, template_gray, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        matched_box = Box(
            icon_search_box.x + int(max_loc[0]),
            icon_search_box.y + int(max_loc[1]),
            int(template_gray.shape[1]),
            int(template_gray.shape[0]),
            confidence=float(max_val),
            name=f'slot-one-{state_name}-icon',
        )
        matched_patch = icon_patch[
            int(max_loc[1]):int(max_loc[1]) + template_gray.shape[0],
            int(max_loc[0]):int(max_loc[0]) + template_gray.shape[1],
        ].copy()
        return {
            'state': state_name,
            'score': float(max_val),
            'box': matched_box,
            'template': template.copy(),
            'matched_patch': matched_patch,
        }

    def detect_slot_one_summon_state(self, frame=None, region_match=None):
        self.task.checkpoint()
        frame = self.get_current_frame() if frame is None else self.normalize_bgr_image(frame)
        region_match = self.locate_slot_one_region(frame) if region_match is None else region_match
        icon_patch, icon_search_box, expected_icon_box = self.extract_slot_one_icon_patch(frame, region_match['box'])
        matches = [
            self.match_slot_one_icon_patch(
                icon_patch,
                icon_search_box,
                expected_icon_box,
                self.slot_one_icon_references['unsummoned'],
                'unsummoned',
            ),
            self.match_slot_one_icon_patch(
                icon_patch,
                icon_search_box,
                expected_icon_box,
                self.slot_one_icon_references['summoned'],
                'summoned',
            ),
        ]
        scores = {match['state']: match['score'] for match in matches}
        summoned_match = next(match for match in matches if match['state'] == 'summoned')
        state = 'summoned' if summoned_match['score'] >= self.SLOT_ONE_STATE_MIN_CONFIDENCE else 'unsummoned'
        self.task.log_info(
            '自动召唤模块: 1号位精灵状态识别完成, '
            f"区域参考={region_match['reference_state']}, 区域分数={region_match['score']:.3f}, "
            f"未召唤参考分数={scores['unsummoned']:.3f}, 已召唤图标分数={scores['summoned']:.3f}, "
            f'判定状态={state}'
        )
        if self.should_dump_every_check_debug_artifacts():
            self.dump_slot_one_state_debug_artifacts(
                frame=frame,
                region_match=region_match,
                icon_patch=icon_patch,
                icon_matches=matches,
                scores=scores,
                reason='latest-check',
                latest=True,
            )
        if region_match['score'] < self.SLOT_ONE_LOCATE_MIN_CONFIDENCE:
            debug_dir = self.dump_slot_one_state_debug_artifacts(
                frame=frame,
                region_match=region_match,
                icon_patch=icon_patch,
                icon_matches=matches,
                scores=scores,
                reason='low_region_confidence',
            )
            self.task.screenshot(
                'auto-summon-slot-one-state-unknown',
                frame=frame,
                show_box=True,
                frame_box=region_match['box'],
            )
            raise RuntimeError(
                '自动召唤模块: 无法可靠识别1号位精灵召唤状态，'
                f"区域分数={region_match['score']:.3f}，已召唤图标分数={scores['summoned']:.3f}，"
                f'调试目录: {debug_dir}'
            )
        return {
            'state': state,
            'score': summoned_match['score'],
            'box': summoned_match['box'],
            'region_box': region_match['box'],
            'locate_score': region_match['score'],
        }

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
        if not self.is_main_interface():
            self.task.log_info('自动召唤模块: 当前界面不是主界面，跳过自动召唤模块')
            return
        frame, region_match, is_visible = self.try_locate_slot_one_region()
        if not is_visible:
            self.task.log_info(
                '自动召唤模块: 当前画面未检测到1号位精灵区域，跳过自动召唤模块，'
                f"区域分数={region_match['score']:.3f}"
            )
            return
        match = self.detect_slot_one_summon_state(frame=frame, region_match=region_match)
        if match['state'] == 'summoned':
            self.task.log_info(
                '自动召唤模块: 检测到1号位精灵已召唤，跳过自动召唤模块，'
                f"匹配分数={match['score']:.3f}"
            )
            return
        self.task.log_info(
            '开始执行自动召唤模块: 1 -> 左键 -> 2 -> 左键 -> 3 -> 左键 -> 4 -> 左键 -> 5 -> 左键 -> 6 -> 左键，'
            f"检测到1号位精灵未召唤，匹配分数={match['score']:.3f}"
        )
        for number in self.SLOT_SEQUENCE:
            self.task.checkpoint()
            self.task.log_info(f'自动召唤模块: 准备进入槽位{number}')
            self.run_slot(number)
            self.task.log_info(f'自动召唤模块: 槽位{number} 处理完成')
        if self.SUMMON_RECHECK_WAIT > 0:
            self.task.interruptible_wait(self.SUMMON_RECHECK_WAIT)
        match = self.detect_slot_one_summon_state()
        if match['state'] != 'summoned':
            self.task.screenshot(
                'auto-summon-slot-one-still-unsummoned-after-auto-summon',
                frame=self.get_current_frame(),
                show_box=True,
                frame_box=match['box'],
            )
            raise RuntimeError('自动召唤模块: 自动召唤后，1号位精灵仍未识别为已召唤状态')
        self.task.log_info(
            f'自动召唤模块: 自动召唤后确认1号位精灵已召唤，匹配分数={match["score"]:.3f}'
        )
