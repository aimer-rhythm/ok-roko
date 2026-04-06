import os

import numpy as np
from ok import ConfigOption
from src.globals import Globals  # noqa: F401
from src.tasks.AutoFlowerTask import AutoFlowerTask  # noqa: F401
from src.tasks.MyOneTimeTask import MyOneTimeTask  # noqa: F401
from src.ui.MyTab import MyTab  # noqa: F401

version = "dev"
# Do not edit version manually; the release workflow updates it when packaging.
# Force packaged builds to include dynamically referenced app modules.

key_config_option = ConfigOption(
    "Game Hotkey Config",
    {
        "Echo Key": "q",
        "Liberation Key": "r",
        "Resonance Key": "e",
        "Tool Key": "t",
    },
    description="In Game Hotkey for Skills",
)


def make_bottom_right_black(frame):
    """
    Mask the UID area for games that render it in the screenshot.
    """
    try:
        height, width = frame.shape[:2]

        black_width = int(0.13 * width)
        black_height = int(0.025 * height)

        start_x = width - black_width
        start_y = height - black_height

        black_rect = np.zeros((black_height, black_width, frame.shape[2]), dtype=frame.dtype)
        frame[start_y:height, start_x:width] = black_rect
        return frame
    except Exception as e:
        print(f"Error processing frame: {e}")
        return frame


config = {
    "custom_tasks": True,
    "debug": False,
    "use_gui": True,
    "config_folder": "configs",
    "global_configs": [key_config_option],
    "screenshot_processor": make_bottom_right_black,
    "gui_icon": "icons/icon.png",
    "wait_until_before_delay": 0,
    "wait_until_check_delay": 0,
    "wait_until_settle_time": 0,
    "ocr": {
        "lib": "onnxocr",
        "params": {
            "use_openvino": True,
        },
    },
    "windows": {
        "exe": ["NRC-Win64-Shipping.exe"],
        # Optional: if set, only this executable is searched.
        # "hwnd_class": "UnrealWindow",
        "interaction": ["PostMessage", "Pynput", "Genshin", "PyDirect", "ForegroundPostMessage"],
        "capture_method": ["WGC", "BitBlt_RenderFull"],
        "check_hdr": False,
        "force_no_hdr": False,
        "require_bg": True,
    },
    "adb": {
        # Optional: if set, the package will be started and installation ensured.
        # "packages": ["com.abc.efg1", "com.abc.efg1"]
    },
    "start_timeout": 120,
    "window_size": {
        "width": 1200,
        "height": 800,
        "min_width": 600,
        "min_height": 450,
    },
    "supported_resolution": {
        "ratio": "16:9",
        "min_size": (1280, 720),
        "resize_to": [(2560, 1440), (1920, 1080), (1600, 900), (1280, 720)],
    },
    "links": {
        "default": {
            "github": "https://github.com/aimer-rhythm/ok-roko",
            "discord": "https://discord.gg/vVyCatEBgA",
            "sponsor": "https://www.paypal.com/ncp/payment/JWQBH7JZKNGCQ",
            "share": "Download from https://github.com/aimer-rhythm/ok-roko",
            "faq": "https://github.com/aimer-rhythm/ok-roko",
        }
    },
    "screenshots_folder": "screenshots",
    "gui_title": "ok-roko",
    "template_matching": {
        "coco_feature_json": os.path.join("assets", "result.json"),
        "default_horizontal_variance": 0.002,
        "default_vertical_variance": 0.002,
        "default_threshold": 0.8,
    },
    "version": version,
    "my_app": ["src.globals", "Globals"],
    "onetime_tasks": [
        ["src.tasks.MyOneTimeTask", "MyOneTimeTask"],
        ["src.tasks.AutoFlowerTask", "AutoFlowerTask"],
        ["ok", "DiagnosisTask"],
    ],
    "trigger_tasks": [],
    "custom_tabs": [
        ["src.ui.MyTab", "MyTab"],
    ],
}
