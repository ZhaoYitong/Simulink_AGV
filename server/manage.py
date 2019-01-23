from simcore import RtEnvironment
from facilities import (RemoteClock, BaseTask, QC, QCTask, AGV, AGVTask, ARMG, ARMGTask, LOAD, UNLOAD, OUT, ENTER,
                        RANDOM_SEED, INPORT, OUTPORT, SHIPCYCLE, YARDCYCLE, FINISHED)
import random

random.seed(RANDOM_SEED)


class Task(BaseTask):
    def __init__(self, raw_id, priority, container, start_facility, end_facility, transporter=None):
        super().__init__(raw_id)
        self.priority = priority
        self.container = container
        self.start_facility = start_facility
        self.end_facility = end_facility
        self.transporter = transporter


class TaskManager(object):
    def __init__(self, tasks=None):
        self.tasks = tasks

    def assign_qc(self):
        for task in self.tasks:
            if isinstance(task.start_facility, QC):
                task.start_facility.put_task(task.priority, QCTask(task.raw_id, UNLOAD, task.container.bay, transporter=task.transporter))
            if isinstance(task.end_facility, QC):
                bay = task.container.cycle_bay if task.container.flag == SHIPCYCLE else task.container.bay
                task.end_facility.put_task(task.priority, QCTask(task.raw_id, LOAD, bay, transporter=task.transporter))

    def assign_agv(self):
        for task in self.tasks:
            task.transporter.put_task(task.priority, AGVTask(task.raw_id, task.start_facility, task.end_facility))

    def assign_armg(self):
        for task in self.tasks:
            if isinstance(task.start_facility, ARMG):
                task.start_facility.put_task(task.priority, ARMGTask(task.raw_id, OUT, transporter=task.transporter))
            if isinstance(task.end_facility, ARMG):
                task.end_facility.put_task(task.priority, ARMGTask(task.raw_id, ENTER, transporter=task.transporter))

    def set_done(self, raw_id):
        for task in self.tasks:
            if task.raw_id == raw_id:
                task.status = FINISHED
                break

    def all_done(self):
        for task in self.tasks:
            if not task.finished:
                return False
        return True


class Term(object):
    def __init__(self, factor, traffic_dispatch_address, **kwargs):
        self.facilities = {}
        self._tasks = []
        self.env = RtEnvironment(factor=factor)
        for key, value in kwargs.items():
            setattr(self, key, value)
        self.traffic_dispatcher_address = traffic_dispatch_address
        self.task_manager = TaskManager()
        self.clock = RemoteClock(self.env, "clock", traffic_dispatch_address, self.task_manager)

    def add_facility(self, facility):
        self.facilities[facility.name] = facility

    @property
    def tasks(self):
        return self._tasks

    @tasks.setter
    def tasks(self, tasks):
        for task in tasks:
            if not isinstance(task, Task):
                raise ValueError('Task must be instance of manager.py:`Task`')
            self.tasks.append(task)
        self.task_manager.tasks = self.tasks
        self.task_manager.assign_qc()
        self.task_manager.assign_armg()
        self.task_manager.assign_agv()

    def run(self):
        self.clock.start_process()
        for facility in self.facilities.values():
            facility.start_process()
        self.env.run()
        return self.env.now
