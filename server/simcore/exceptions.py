class StopSimulation(Exception):
    @classmethod
    def callback(cls, event):
        if event.ok:
            raise cls(event.value)
        else:
            raise event.value


class StopProcess(Exception):
    def __init__(self, value):
        super(StopProcess, self).__init__(value)

    def __str__(self):
        return '%s(%r)' % (self.__class__.__name__, self.value)

    @property
    def value(self):
        return self.args[0]


class EmptySchedule(Exception):
    pass
