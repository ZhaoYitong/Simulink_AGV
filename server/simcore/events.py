from simcore.exceptions import StopProcess
from socket import socket, AF_INET, SOCK_STREAM


PENDING = object()
URGENT = 0
NORMAL = 1


class Event(object):
    def __init__(self, env):
        self.env = env
        self.callbacks = []
        self._value = PENDING

    def __repr__(self):
        return '<%s() object at 0x%x>' % (self.__class__.__name__, id(self))

    @property
    def triggered(self):
        return self._value is not PENDING

    @property
    def processed(self):
        return self.callbacks is None

    @property
    def ok(self):
        return self._ok

    @property
    def value(self):
        if self._value is PENDING:
            raise AttributeError('Value of %s is not yet available' % self)
        return self._value

    def trigger(self, event):
        self._ok = event._ok
        self._value = None
        self.env.schedule(self)

    def succeed(self, value=None):
        if self._value is not PENDING:
            raise RuntimeError('%s has already been triggered' % self)
        self._ok = True
        self._value = value
        self.env.schedule(self)
        return self

    def fail(self, exception):
        if self._value is not PENDING:
            raise RuntimeError('%s has already been triggered' % self)
        if not isinstance(exception, BaseException):
            raise ValueError('%s is not an exception.' % exception)
        self._ok = False
        self._value = exception
        self.env.schedule(self)
        return self


class Timeout(Event):
    def __init__(self, env, delay, value=None):
        if delay < 0:
            raise ValueError('Negative delay %s' % delay)
        self.env = env
        self.callbacks = []
        self._value = value
        self._delay = delay
        self._ok = True
        env.schedule(self, NORMAL, delay)


class Send(Event):
    def __init__(self, env, addr, msg):
        self.env = env
        self.sock = socket(AF_INET, SOCK_STREAM)
        self.msg = msg
        self.callbacks = []
        self._value = None
        self.sock.setblocking(False)
        try:
            self.sock.connect(addr)
        except BlockingIOError:
            pass
        env.register(self.sock, 2, self.done)

    def done(self):
        self.sock.send(bytes(self.msg, encoding='utf-8'))
        self._ok = True
        self._value = self.sock
        self.env.schedule(self)
        self.env.unregister(self.sock)


class Realtime(Event):
    def __init__(self, env, sock):
        self.env = env
        self.sock = sock
        self.callbacks = []
        self._value = None
        env.register(sock, 1, self.done)

    def done(self):
        self._ok = True
        self._value = self.sock.recv(1024).decode('utf-8')
        self.env.schedule(self)
        self.env.unregister(self.sock)
        self.sock.close()


class Initialize(Event):
    def __init__(self, env, process):
        self.env = env
        self.callbacks = [process._resume]
        self._value = None
        self._ok = True
        env.schedule(self, URGENT)


class Process(Event):
    def __init__(self, env, generator):
        if not hasattr(generator, 'throw'):
            raise ValueError('%s is not a generator.' % generator)
        self.env = env
        self.callbacks = []
        self._value = PENDING
        self._generator = generator
        self._target = Initialize(env, self)

    @property
    def target(self):
        return self._target

    @property
    def is_alive(self):
        return self._value is PENDING

    def _resume(self, event):
        self.env._active_proc = self
        while True:
            try:
                if event._ok:
                    event = self._generator.send(event._value)
                else:
                    event._defused = True
                    exc = type(event._value)(*event._value.args)
                    exc.__cause__ = event._value
                    event = self._generator.throw(exc)
            except (StopIteration, StopProcess) as e:
                event = None
                self._ok = True
                self._value = e.args[0] if len(e.args) else None
                self.env.schedule(self)
                break
            if event.callbacks is not None:
                event.callbacks.append(self._resume)
                break
        self._target = event
        self.env._active_proc = None
