from simcore.events import Event, NORMAL, URGENT
from simcore.exceptions import StopSimulation, EmptySchedule
from itertools import count
from heapq import heappush, heappop
from time import monotonic as time
from selectors import DefaultSelector, EVENT_READ, EVENT_WRITE
from socket import socket


Infinity = time() + 2**16


class BaseEnvironment(object):
    @property
    def now(self):
        raise NotImplementedError(self)

    @property
    def active_process(self):
        raise NotImplementedError(self)

    def schedule(self, event, priority=NORMAL, delay=0):
        raise NotImplementedError(self)

    def step(self):
        raise NotImplementedError(self)

    def run(self, until=None):
        if until is not None:
            if not isinstance(until, Event):
                at = float(until)
                if at <= self.now:
                    raise ValueError('until(=%s) should be > the current simulation time.' % at)
                until = Event(self)
                until._ok = True
                until._value = None
                self.schedule(until, URGENT, at - self.now)

            if until.callbacks is None:
                return until.value
            until.callbacks.append(StopSimulation.callback)
        try:
            while True:
                self.step()
        except StopSimulation as exc:
            return exc.args[0]
        except EmptySchedule:
            if until is not None:
                assert not until.triggered
                raise RuntimeError('No scheduled events left but "until" event was not triggered: %s' % until)


class RtEnvironment(BaseEnvironment):
    def __init__(self, initial_time=0, factor=1.0, strict=True):
        self.env_start = initial_time
        self.real_start = time()
        self._factor = factor
        self._strict = strict
        self._now = initial_time
        self._queue = []
        self._eid = count()
        self._rid = 0
        self._active_proc = None
        self._prepare()
        self._data = {}

    def _prepare(self):
        self._selector = DefaultSelector()
        self._sock = socket()
        self._selector.register(self._sock, EVENT_READ, None)

    def get_data(self, key):
        if key in self._data.keys():
            return self._data[key]
        else:
            return 0

    def set_data(self, key, value):
        self._data[key] = value

    @property
    def now(self):
        return self._now

    @property
    def active_process(self):
        return self._active_proc

    @property
    def factor(self):
        return self._factor

    @property
    def strict(self):
        return self._strict

    def schedule(self, event, priority=NORMAL, delay=0):
        heappush(self._queue, (self._now + delay, priority, next(self._eid), event))

    def register(self, fileobj, events, callback):
        self._rid += 1
        self._selector.register(fileobj, events, callback)

    def unregister(self, fileobj):
        self._rid -= 1
        self._selector.unregister(fileobj)

    def peek(self):
        return self._queue[0][0]

    def sync(self):
        self.real_start = time()

    def step(self):
        try:
            evt_time = self.peek()
        except IndexError:
            if self._rid > 0:
                evt_time = Infinity
            else:
                raise EmptySchedule()
        real_time = self.real_start + (evt_time - self.env_start) * self.factor

        if self.strict and time() - real_time > self.factor:
            raise RuntimeError('Simulation too slow for real time (%.3fs).' % (time() - real_time))

        while True:
            delta = real_time - time()
            if delta <= 0:
                break
            events = self._selector.select(timeout=delta)
            if events:
                self._now = (time() - self.real_start) / self.factor
                for key, mask in events:
                    callback = key.data
                    callback()
                real_time = self.real_start + (self.peek() - self.env_start) * self.factor

        self._now, _, _, event = heappop(self._queue)

        callbacks, event.callbacks = event.callbacks, None
        for callback in callbacks:
            callback(event)

        if not event._ok:
            exc = type(event._value)(*event._value.args)
            exc.__cause__ = event._value
            raise exc
