from qfluentwidgets import FluentIcon

from src.tasks.MyBaseTask import MyBaseTask
from src.tasks.auto_flower.AutoAdjustTimeModule import AutoAdjustTimeModule
from src.tasks.auto_flower.AutoBowModule import AutoBowModule
from src.tasks.auto_flower.AutoSummonModule import AutoSummonModule


class AutoFlowerTask(MyBaseTask):
    ADJUST_TIME_ENABLED = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = "自动刷花"
        self.description = "自动刷花总任务，当前按顺序执行自动召唤和自动鞠躬，调整游戏时间模块暂时关闭"
        self.icon = FluentIcon.PLAY
        self.auto_summon_module = AutoSummonModule(self)
        self.auto_bow_module = AutoBowModule(self)
        self.auto_adjust_time_module = AutoAdjustTimeModule(self)

    def run(self):
        self.log_info('开始执行自动刷花任务', notify=True)
        if self.ADJUST_TIME_ENABLED:
            self.auto_adjust_time_module.run()
        else:
            self.log_info('自动刷花任务: 调整游戏时间模块暂时关闭，跳过执行')
        self.auto_summon_module.run()
        self.auto_bow_module.run()
        self.log_info('自动刷花任务执行完成', notify=True)
