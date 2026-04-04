from qfluentwidgets import FluentIcon

from src.tasks.MyBaseTask import MyBaseTask
from src.tasks.auto_flower.AutoBowModule import AutoBowModule
from src.tasks.auto_flower.AutoSummonModule import AutoSummonModule


class AutoFlowerTask(MyBaseTask):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = "自动刷花"
        self.description = "自动刷花总任务，当前按顺序执行自动召唤模块和自动鞠躬模块，后续可接入自动传送模块"
        self.icon = FluentIcon.PLAY
        self.auto_summon_module = AutoSummonModule(self)
        self.auto_bow_module = AutoBowModule(self)

    def run(self):
        self.log_info('开始执行自动刷花任务', notify=True)
        self.auto_summon_module.run()
        self.auto_bow_module.run()
        self.log_info('自动刷花任务执行完成', notify=True)
