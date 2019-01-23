from simcore import Event
from heapq import heappush, heappop
from collections import namedtuple


class Put(Event):
    def __init__(self, resource):
        super(Put, self).__init__(resource._env)
        self.resource = resource
        self.proc = self.env.active_process

        resource.put_queue.append(self)
        self.callbacks.append(resource._trigger_get)
        resource._trigger_put(None)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.cancel()

    def cancel(self):
        if not self.triggered:
            self.resource.put_queue.remove(self)


class Get(Event):
    def __init__(self, resource):
        super(Get, self).__init__(resource._env)
        self.resource = resource
        self.proc = self.env.active_process

        resource.get_queue.append(self)
        self.callbacks.append(resource._trigger_put)
        resource._trigger_get(None)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.cancel()

    def cancel(self):
        if not self.triggered:
            self.resource.get_queue.remove(self)


class BaseResource(object):
    PutQueue = list
    GetQueue = list

    def __init__(self, env, capacity):
        self._env = env
        self._capacity = capacity
        self.put_queue = self.PutQueue()
        self.get_queue = self.GetQueue()

    @property
    def capacity(self):
        return self._capacity

    def _do_put(self, event):
        raise NotImplementedError(self)

    def _trigger_put(self, get_event):
        idx = 0
        while idx < len(self.put_queue):
            put_event = self.put_queue[idx]
            proceed = self._do_put(put_event)
            if not put_event.triggered:
                idx += 1
            elif self.put_queue.pop(idx) != put_event:
                raise RuntimeError('Put queue invariant violated')

            if not proceed:
                break

    def _do_get(self, event):
        raise NotImplementedError(self)

    def _trigger_get(self, put_event):
        idx = 0
        while idx < len(self.get_queue):
            get_event = self.get_queue[idx]
            proceed = self._do_get(get_event)
            if not get_event.triggered:
                idx += 1
            elif self.get_queue.pop(idx) != get_event:
                raise RuntimeError('Get queue invariant violated')

            if not proceed:
                break


class Request(Put):
    def __exit__(self, exc_type, value, traceback):
        super(Request, self).__exit__(exc_type, value, traceback)
        if exc_type is not GeneratorExit:
            Release(self.resource, self)


class Release(Get):
    def __init__(self, resource, request):
        self.request = request
        super(Release, self).__init__(resource)


class PriorityRequest(Request):
    def __init__(self, resource, priority=0):
        self.priority = priority
        self.time = resource._env.now
        self.key = (self.priority, self.time)
        super(PriorityRequest, self).__init__(resource)

class Resource(BaseResource):
    def __init__(self, env, capacity=1):
        if capacity <= 0:
            raise ValueError('"capacity" must be > 0.')

        super(Resource, self).__init__(env, capacity)

        self.users = []
        self.queue = self.put_queue

    @property
    def count(self):
        return len(self.users)

    def _do_put(self, event):
        if len(self.users) < self.capacity:
            self.users.append(event)
            event.succeed()

    def _do_get(self, event):
        try:
            self.users.remove(event.request)
        except ValueError:
            pass
        event.succeed()


class StorePut(Put):
    def __init__(self, store, item):
        self.item = item
        super(StorePut, self).__init__(store)


class StoreGet(Get):
    pass


class FilterStoreGet(StoreGet):
    def __init__(self, resource, filter=lambda item: True):
        self.filter = filter
        super(FilterStoreGet, self).__init__(resource)


class Store(BaseResource):
    def __init__(self, env, capacity=float('inf')):
        if capacity <= 0:
            raise ValueError('"capacity" must be > 0.')

        super(Store, self).__init__(env, capacity)

        self.items = []

    def _do_put(self, event):
        if len(self.items) < self._capacity:
            self.items.append(event.item)
            event.succeed()

    def _do_get(self, event):
        if self.items:
            event.succeed(self.items.pop(0))


class FilterStore(Store):
    def _do_get(self, event):
        for item in self.items:
            if event.filter(item):
                self.items.remove(item)
                event.succeed(item)
                break
        return True
