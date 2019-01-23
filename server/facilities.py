from simcore import Process, Send, Realtime, Timeout, Store, FilterStore, FilterStoreGet, StorePut, StoreGet, Infinity
from itertools import count
from heapq import heappush, heappop
from utils import lane2position, BUFFER_LANE, MAX_CELL_X
from sim_params import *
import logging

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

PENDING = 0  # 未指派
PROCESSING = 1  # 进行中
FINISHED = 2  # 已完成


class DeadLock(Exception):
    pass


class BaseTask(object):
    def __init__(self, raw_id):
        self.raw_id = raw_id
        self._status = PENDING

    @property
    def finished(self):
        return self._status == FINISHED

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, value):
        self._status = value


class BaseFacility(object):
    def __init__(self, env, name, remote=False, address=None):
        self.env = env
        self.name = name
        self.remote = remote
        self.address = address
        self._position = None
        self._queue = []
        self._tid = count()
        self._current_task = None
        self._priority = None

    @property
    def position(self):
        """设备当前位置"""
        return self._position

    @position.setter
    def position(self, position):
        try:
            self._position = int(position)
        except ValueError:
            raise TypeError("Position should be the cell id instead of %s:%s." % (type(position), position))

    @property
    def current_task(self):
        return self._current_task

    def has_task(self, raw_id):
        if self._current_task is not None and self._current_task.raw_id == raw_id:
            return True
        for _, _, task in self._queue:
            if task.raw_id == raw_id:
                return True
        return False

    def find_unprocessed_task(self, raw_id):
        for _, _, task in self._queue:
            if task.raw_id == raw_id:
                return task
        return None

    def put_task(self, priority, task):
        """根据优先级`priority`插入任务到设备任务序列，数字越小优先级越高"""
        tid = next(self._tid)
        heappush(self._queue, [priority, tid, task])
        log.debug('(%.3f)%s get task %s with priority %s', self.env.now, self.name, task, priority)
        return tid

    def get_task(self):
        """取出优先级最高的任务"""
        priority, _, task = heappop(self._queue)
        self._current_task = task
        self._priority = priority
        return priority, task

    def peek_task(self):
        """查看下一任务不取出"""
        return self._queue[0][2]

    def process(self):
        """具体仿真的协程函数"""
        raise NotImplementedError(self)

    def start_process(self):
        """启动协程"""
        if self._position is None:
            raise ValueError("Position is not assigned.")
        if self.remote and self.address is None:
            raise ValueError("Address is not assigned.")
        Process(self.env, self.process())


class RemoteClock(BaseFacility):
    def __init__(self, env, name, address, task_manager):
        super().__init__(env, name)
        self.remote = True
        self.address = address
        self.task_manager = task_manager  # 任务管理器

    def process(self):
        while not self.task_manager.all_done():
            yield Send(self.env, self.address, "sync %s" % self.env.now)
            yield Timeout(self.env, 0.5)

    def start_process(self):
        if self.remote and self.address is None:
            raise ValueError("Address is not assigned.")
        Process(self.env, self.process())


class QCTask(BaseTask):
    def __init__(self, raw_id, flag, bay, lane=None, transporter=None):
        super().__init__(raw_id)
        self.flag = flag  # 装卸类型标记
        self.bay = bay  # 任务贝位
        self.lane = lane  # 任务车道
        self.transporter = transporter  # 运输AGV

    def __repr__(self):
        return '<QCTask(raw_id=%s, flag=%s, bay=%s, lane=%s, transporter=%s)>' % (self.raw_id, self.flag, self.bay, self.lane, self.transporter)


class QC(BaseFacility):
    def __init__(self, env, name, position, lanes, address, task_manager):
        super().__init__(env, name)
        self.position = position
        self.address = address
        self.shift_store = FilterStore(env, capacity=len(lanes))  # 交换区
        self.lanes_queue = {int(lane): [] for lane in lanes}  # 车道队列长度
        self.task_manager = task_manager
        log.debug('Create %s at cell %s with lanes %s.', name, position, lanes)

    def __repr__(self):
        return self.name

    def select_min_lane(self):
        min_lane, min_len = 0, Infinity
        for lane, lane_queue in self.lanes_queue.items():
            if len(lane_queue) < min_len:
                min_len = len(lane_queue)
                min_lane = lane
        return min_lane

    def set_task_lane(self, raw_id, lane):
        if self.current_task.raw_id == raw_id:
            self.current_task.lane = lane
            return
        for _, _, task in self._queue:
            if task.raw_id == raw_id:
                task.lane = lane
                return
        raise IndexError('Invalid task_id: %s.' % raw_id)

    def get_task_lane(self, raw_id):
        if self.current_task.raw_id == raw_id:
            return self.current_task.lane
        for _, _, task in self._queue:
            if task.raw_id == raw_id:
                return task.lane
        raise IndexError('Invalid task_id: %s.' % raw_id)
    
    def process(self):
        self.env.set_data(self.name + "_start", self.env.now)

        while True:
            try:
                priority, task = self.get_task()  # 从任务队列取出一个任务
            except IndexError:
                log.info('(%.3f)%s finished all jobs.', self.env.now, self.name)
                break
            log.info('(%.3f)%s start processing %s.', self.env.now, self.name, task)

            if not task.lane:
                lane = self.select_min_lane()
                task.lane = lane
                self.lanes_queue[lane].append(priority)
            yield Send(self.env, self.address, "setcell %s %s" % (lane2position(self.position, task.lane), priority))
            log.debug('(%.3f)%s current lanes_queue: %s.', self.env.now, self.name, self.lanes_queue)

            if task.flag == UNLOAD:
                yield Timeout(self.env, QC_READY)  # 岸侧小车提箱到位
                log.info('(%.3f)%s ready to drop container to %s in task_%s.', self.env.now, self.name, task.transporter, task.raw_id)
                temp_now, wait_sum = self.env.now, self.env.get_data(self.name + "_wait")
                agv = yield FilterStoreGet(self.shift_store, lambda item: item == task.transporter)  # 看AGV是否到了
                self.env.set_data(self.name + "_wait", wait_sum + self.env.now - temp_now)
                yield Timeout(self.env, QC_LIFT_DROP)  # 落箱到AGV
                log.info('(%.3f)%s dropped container to %s in task_%s.', self.env.now, self.name, agv, task.raw_id)
                yield StorePut(agv.shift_store, self)  # AGV接到箱子

                self.lanes_queue[task.lane].remove(priority)
                if self.lanes_queue[task.lane]:
                    yield Send(self.env, self.address, "setcell %s %s" % (lane2position(self.position, task.lane), min(self.lanes_queue[task.lane])))
                log.debug('(%.3f)%s current lanes_queue: %s.', self.env.now, self.name, self.lanes_queue)

            elif task.flag == LOAD:
                temp_now, wait_sum = self.env.now, self.env.get_data(self.name + "_wait")
                agv = yield FilterStoreGet(self.shift_store, lambda item: item == task.transporter)  # 看AGV是否到了
                self.env.set_data(self.name + "_wait", wait_sum + self.env.now - temp_now)
                yield Timeout(self.env, QC_LIFT_DROP)  # 从AGV提箱
                log.info('(%.3f)%s got container from %s in task_%s.', self.env.now, self.name, agv, task.raw_id)
                yield StorePut(agv.shift_store, self)  # AGV可以走了

                self.lanes_queue[task.lane].remove(priority)
                if self.lanes_queue[task.lane]:
                    yield Send(self.env, self.address, "setcell %s %s" % (lane2position(self.position, task.lane), min(self.lanes_queue[task.lane])))
                log.debug('(%.3f)%s current lanes_queue: %s.', self.env.now, self.name, self.lanes_queue)

                yield Timeout(self.env, QC_TOSHIP)  # 放到船上
                self.task_manager.set_done(task.raw_id)
                log.info('(%.3f)task_%s finished.', self.env.now, task.raw_id)

        self.env.set_data(self.name + "_end", self.env.now)


class AGVTask(BaseTask):
    def __init__(self, raw_id, start_facility=None, end_facility=None):
        super().__init__(raw_id)
        self.start_facility = start_facility  # 起点设备
        self.end_facility = end_facility  # 终点设备

    def __repr__(self):
        return '<AGVTask(raw_id=%s, start_facility=%s, end_facility=%s)>' % (self.raw_id, self.start_facility, self.end_facility)


class AGV(BaseFacility):
    def __init__(self, env, name, position, address, speed, task_manager):
        super().__init__(env, name)
        self.remote = True
        self.address = address
        self.position = position
        self.speed = speed
        self.shift_store = Store(env, capacity=1)  # 交换区
        self.task_manager = task_manager  # 任务管理器
        log.debug('Create %s at cell %s.', name, position)

    def __repr__(self):
        return self.name

    def process(self):
        self.env.set_data(self.name + "_start", self.env.now)

        while True:
            try:
                priority, task = self.get_task()  # 从任务队列取出一个任务
            except IndexError:
                log.info('(%.3f)%s finished all jobs.', self.env.now, self.name)
                break
            log.info('(%.3f)%s start processing %s.', self.env.now, self.name, task)

            lane = task.start_facility.get_task_lane(task.raw_id)
            lane_priority = None
            if not lane:
                lane = task.start_facility.select_min_lane()
                task.start_facility.set_task_lane(task.raw_id, lane)
                task.start_facility.lanes_queue[lane].append(priority)
                lane_priority = min(task.start_facility.lanes_queue[lane])

            if isinstance(task.start_facility, ARMG):
                if not task.start_facility.holders[lane].has_task(task.raw_id):
                    task.start_facility.holders[lane].put_task(priority, task.start_facility.find_unprocessed_task(task.raw_id))

            if lane_priority:
                yield Send(self.env, self.address, "setcell %s %s" % (lane2position(task.start_facility.position, lane), lane_priority))
                log.debug('(%.3f)%s current lanes_queue: %s.', self.env.now, task.start_facility.name, task.start_facility.lanes_queue)

            if isinstance(task.start_facility, ARMG):
                task.start_facility = task.start_facility.holders[lane]  # 起点设备改为支架

            log.info('(%.3f)%s departs to %s on lane %s in task_%s.', self.env.now, self.name, task.start_facility, lane, task.raw_id)
            sock = yield Send(self.env, self.address, "go %s %s %s %s %s %s" % (self.name, priority, self._position, lane2position(task.start_facility.position, lane), self.speed, 0))  # 去任务起点
            position = yield Realtime(self.env, sock)
            if position == "-1":
                raise DeadLock("Traffic deadlock found in %s." % self.name)
            self._position = int(position)
            log.info('(%.3f)%s arrives %s in task_%s.', self.env.now, self.name, self.position, task.raw_id)

            yield StorePut(task.start_facility.shift_store, self)  # 起点处设备可以作业了
            temp_now, wait_sum = self.env.now, self.env.get_data(self.name + "_wait")
            yield StoreGet(self.shift_store)  # 拿到箱子
            self.env.set_data(self.name + "_wait", wait_sum + self.env.now - temp_now)
            log.info('(%.3f)%s got container from %s in task_%s.', self.env.now, self.name, task.start_facility, task.raw_id)

            lane = task.end_facility.get_task_lane(task.raw_id)
            lane_priority = None
            if not lane:
                lane = task.end_facility.select_min_lane()
                task.end_facility.set_task_lane(task.raw_id, lane)
                task.end_facility.lanes_queue[lane].append(priority)
                lane_priority = min(task.end_facility.lanes_queue[lane])

            if isinstance(task.end_facility, ARMG):
                if not task.end_facility.holders[lane].has_task(task.raw_id):
                    task.end_facility.holders[lane].put_task(priority, task.end_facility.find_unprocessed_task(task.raw_id))

            if lane_priority:
                yield Send(self.env, self.address, "setcell %s %s" % (lane2position(task.end_facility.position, lane), lane_priority))
                log.debug('(%.3f)%s current lanes_queue: %s.', self.env.now, task.end_facility.name, task.end_facility.lanes_queue)

            if isinstance(task.end_facility, ARMG):
                task.end_facility = task.end_facility.holders[lane]  # 终点设备改为支架

            log.info('(%.3f)%s departs to %s in lane %s in task_%s.', self.env.now, self.name, task.end_facility, lane, task.raw_id)
            sock = yield Send(self.env, self.address, "go %s %s %s %s %s %s" % (self.name, priority, self._position, lane2position(task.end_facility.position, lane), self.speed, 1))  # 去任务终点
            position = yield Realtime(self.env, sock)
            if position == "-1":
                raise DeadLock("Traffic deadlock found in %s." % self.name)
            self._position = int(position)
            log.info('(%.3f)%s arrives %s in task_%s.', self.env.now, self.name, self.position, task.raw_id)

            yield StorePut(task.end_facility.shift_store, self)  # 终点处设备可以作业了
            temp_now, wait_sum = self.env.now, self.env.get_data(self.name + "_wait")
            yield StoreGet(self.shift_store)  # 等终点设备完成作业
            self.env.set_data(self.name + "_wait", wait_sum + self.env.now - temp_now)

        if MAX_CELL_X * BUFFER_LANE + 1 <= self._position <= MAX_CELL_X * (BUFFER_LANE + 1):
            self.env.set_data(self.name + "_end", self.env.now)
            return

        sock = yield Send(self.env, self.address, "go %s %s %s %s %s %s" % (self.name, 0, self._position, -1, self.speed, -1))  # 归位
        log.info('(%.3f)%s return to buffer lane.', self.env.now, self.name)
        position = yield Realtime(self.env, sock)
        if position == "-1":
            raise DeadLock("Traffic deadlock found in %s." % self.name)
        self._position = int(position)
        log.info('(%.3f)%s returned buffer lane %s.', self.env.now, self.name, self.position)

        self.env.set_data(self.name + "_end", self.env.now)


class ARMGTask(BaseTask):
    def __init__(self, raw_id, flag, lane=None, transporter=None):
        super().__init__(raw_id)
        self.flag = flag  # 进出堆场标记
        self.lane = lane  # 装卸车道/支架
        self.transporter = transporter  # 运输AGV

    def __repr__(self):
        return '<ARMGTask(raw_id=%s, flag=%s, lane=%s, transporter=%s)>' % (self.raw_id, self.flag, self.lane, self.transporter)


class ARMG(BaseFacility):
    def __init__(self, env, name, position, lanes, address, task_manager):
        super().__init__(env, name)
        self.position = position
        self.lanes = lanes
        self.address = address
        self.shift_store = FilterStore(env, capacity=len(lanes))  # 交换区
        self.holders = {int(lane): Holder(env, 'holder_%s' % lane, int(lane), self) for lane in lanes}  # 支架
        self.lanes_queue = {int(lane): [] for lane in lanes}  # 车道队列长度
        self.task_manager = task_manager
        self._task_lanes = {}  # 车道选择结果存储
        log.debug('Create %s at cell %s with lanes %s.', name, position, self.lanes)

    def __repr__(self):
        return self.name

    def select_min_lane(self):
        min_lane, min_len = 0, Infinity
        for lane, lane_queue in self.lanes_queue.items():
            if len(lane_queue) < min_len:
                min_len = len(lane_queue)
                min_lane = lane
        return min_lane

    def set_task_lane(self, raw_id, lane):
        if self.current_task.raw_id == raw_id:
            self.current_task.lane = lane
            self._task_lanes[raw_id] = lane
            return
        for _, _, task in self._queue:
            if task.raw_id == raw_id:
                task.lane = lane
                self._task_lanes[raw_id] = lane
                return
        raise IndexError('Invalid task_id: %s.' % raw_id)

    def get_task_lane(self, raw_id):
        if raw_id in self._task_lanes.keys():
            return self._task_lanes[raw_id]
        else:
            return None

    def process(self):
        for holder in self.holders.values():
            Process(self.env, holder.process())

        self.env.set_data(self.name + "_start", self.env.now)

        while True:
            try:
                priority, task = self.get_task()  # 从任务队列取出一个任务
            except IndexError:
                log.info('(%.3f)%s finished all jobs.', self.env.now, self.name)
                break
            log.info('(%.3f)%s start processing %s.', self.env.now, self.name, task)

            if not task.lane:
                lane = self.select_min_lane()
                task.lane = lane
                self._task_lanes[task.raw_id] = lane
                self.lanes_queue[lane].append(priority)

            if not self.holders[task.lane].has_task(task.raw_id):
                self.holders[task.lane].put_task(priority, task)  # 任务传递给支架

            yield Send(self.env, self.address, "setcell %s %s" % (lane2position(self.position, task.lane), priority))
            log.debug('(%.3f)%s current lanes_queue: %s.', self.env.now, self.name, self.lanes_queue)

            if task.flag == OUT:
                yield Timeout(self.env, ARMG_READY)  # 海侧场吊提箱到位
                log.info('(%.3f)%s ready to drop container to %s in task_%s.', self.env.now, self.name, task.lane, task.raw_id)
                temp_now, wait_sum = self.env.now, self.env.get_data(self.name + "_wait")
                agv = yield FilterStoreGet(self.shift_store, lambda item: item == task.transporter)  # 等待支架/AGV就绪
                self.env.set_data(self.name + "_wait", wait_sum + self.env.now - temp_now)
                yield Timeout(self.env, ARMG_LIFT_DROP)  # 落箱到支架
                yield StorePut(self.holders[task.lane].inter_store, self)  # 支架接到箱子
                log.info('(%.3f)%s dropped container to %s in task_%s.', self.env.now, self.name, task.lane, task.raw_id)
            elif task.flag == ENTER:
                temp_now, wait_sum = self.env.now, self.env.get_data(self.name + "_wait")
                agv = yield FilterStoreGet(self.shift_store, lambda item: item == task.transporter)
                self.env.set_data(self.name + "_wait", wait_sum + self.env.now - temp_now)
                yield Timeout(self.env, ARMG_LIFT_DROP)  # 从支架提箱
                yield StorePut(self.holders[task.lane].inter_store, self)  # 支架空闲了
                log.info('(%.3f)%s got container from %s in task_%s.', self.env.now, self.name, task.lane, task.raw_id)
                yield Timeout(self.env, ARMG_TOYARD)  # 放到指定箱位
                self.task_manager.set_done(task.raw_id)
                log.info('(%.3f)task_%s finished.', self.env.now, task.raw_id)

        self.env.set_data(self.name + "_end", self.env.now)


class Holder(BaseFacility):
    """顶升支架，配合海侧场吊使用"""
    def __init__(self, env, name, position, armg):
        super().__init__(env, name)
        self.position = position
        self.armg = armg  # 所在场吊
        self.inter_store = Store(env, capacity=1)  # 内部交换区，仅对场吊开放
        self.shift_store = Store(env, capacity=1)  # 外部交换区，仅对AGV开放
        self.stop = False  # 停止工作标志
        self._tasks = []

    def __repr__(self):
        return self.name

    def process(self):
        self.env.set_data(self.name + "_start", self.env.now)

        while True:
            try:
                priority, task = self.get_task()  # 从任务队列取出一个任务
            except IndexError:
                if self.armg.task_manager.all_done():
                    log.debug('(%.3f)%s close.', self.env.now, self.name)
                    break
                yield Timeout(self.env, 0.1)  # 等待所有任务完成再结束
                continue
            temp_now, occupied_sum = self.env.now, self.env.get_data(self.name + "_occupied")
            if task.flag == OUT:
                yield StorePut(self.armg.shift_store, task.transporter)  # 场吊可以落箱了
                yield StoreGet(self.inter_store)  # 场吊落完箱了
                agv = yield StoreGet(self.shift_store)  # 看AGV是否到了
                yield Timeout(self.env, HOLDER_JACK)  # 顶升
                log.info('(%.3f)%s jacked container to %s in task_%s.', self.env.now, self.name, agv, task.raw_id)
                yield StorePut(agv.shift_store, self)  # AGV可以走了

                self.armg.lanes_queue[self.position].remove(priority)
                if self.armg.lanes_queue[task.lane]:
                    yield Send(self.env, self.armg.address, "setcell %s %s" % (lane2position(self.position, task.lane), min(self.armg.lanes_queue[task.lane])))
                log.debug('(%.3f)%s current lanes_queue: %s.', self.env.now, self.armg.name, self.armg.lanes_queue)

            elif task.flag == ENTER:
                agv = yield StoreGet(self.shift_store)  # 看AGV是否到了
                yield Timeout(self.env, HOLDER_JACK)  # 顶升
                log.info('(%.3f)%s jacked container from %s in task_%s.', self.env.now, self.name, agv, task.raw_id)
                yield StorePut(agv.shift_store, self)  # AGV可以走了
                yield StorePut(self.armg.shift_store, task.transporter)  # 场吊可以提箱了
                yield StoreGet(self.inter_store)  # 场吊提完了

                self.armg.lanes_queue[self.position].remove(priority)
                if self.armg.lanes_queue[task.lane]:
                    yield Send(self.env, self.armg.address, "setcell %s %s" % (lane2position(self.position, task.lane), min(self.armg.lanes_queue[task.lane])))
                log.debug('(%.3f)%s current lanes_queue: %s.', self.env.now, self.armg.name, self.armg.lanes_queue)
            self.env.set_data(self.name + "_occupied", occupied_sum + self.env.now - temp_now)

        self.env.set_data(self.name + "_end", self.env.now)
