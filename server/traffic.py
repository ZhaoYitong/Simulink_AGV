from socketserver import BaseRequestHandler, ThreadingTCPServer
from utils import AStarGraph, BUFFER_LANE, MAX_CELL_X
from queue import Queue
import threading
import logging
import time
import sys

logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s', level=logging.DEBUG)
log = logging.getLogger(__name__)


class CommandHandler(BaseRequestHandler):
    def handle(self):
        recv_data = self.request.recv(1024).decode('utf-8')
        if not recv_data.strip():
            self.request.close()
            return
        parts = recv_data.split(' ', 1)
        cmd = parts[0]
        try:
            line = parts[1]
        except IndexError:
            line = ''
        try:
            meth = self.__getattribute__('do_' + cmd)
            meth(line)
        except AttributeError:
            pass


class ConnAGV(object):
    def __init__(self, name, request):
        self.name = name
        self.request = request
        self.recv_buffer = Queue()


class AGVHandler(CommandHandler):
    def do_clock(self, line):
        log.debug("AGVHandler: Remote Clock connected.")
        while True:
            self.request.sendall(bytes('{"now": %s}' % self.server.now, encoding='utf-8'))
            time.sleep(0.5)

    def do_sync(self, line):
        now = line.strip()
        self.server.now = now

    def do_login(self, line):
        name = line.strip()
        conn_agv = ConnAGV(name, self.request)
        self.server.agvs[name] = conn_agv
        log.info("AGVHandler: <%s> connected.", name)
        while True:
            recv_data = self.request.recv(1024).decode('utf-8')
            conn_agv.recv_buffer.put(recv_data)

    def do_setcell(self, line):
        parts = line.split()
        try:
            cell, priority = int(parts[0]), int(parts[1])

        except IndexError:
            self.request.sendall(bytes('error cmd %s' % line, encoding='utf-8'))
            log.error('AGVHandler: setcell get invalid  command %s.', line)
            self.request.close()
            return
        self.server.set_cell_cur_priority(cell, priority)
        log.info('AGVHandler: current priority of cell %s updated to %s.', cell, priority)
        self.request.close()

    def do_go(self, line):
        parts = line.split()
        try:
            agv, priority, start_cell, end_cell, speed, flag = parts[0], int(parts[1]), int(parts[2]), int(parts[3]), int(parts[4]), int(parts[5])
        except IndexError:
            self.request.sendall(bytes('error cmd %s' % line, encoding='utf-8'))
            return
        position = self.server.go_agv(agv, priority, start_cell, end_cell, speed, flag)
        self.request.sendall(bytes(str(position), encoding='utf-8'))
        log.info('AGVHandler: %s went from %s to %s.', agv, start_cell, end_cell)
        self.request.close()


class TrafficDispatcher(ThreadingTCPServer):
    def __init__(self, server_address, handler):
        super().__init__(server_address, handler)
        self.now = 0.0
        self.agvs = {}
        self.graph = AStarGraph()
        self._cell_cur_priority = {}
        self._mutex = threading.Lock()

    def set_cell_cur_priority(self, cell, priority):
        self._mutex.acquire()
        self._cell_cur_priority[cell] = priority
        self._mutex.release()

    def get_path(self, start_cell, end_cell):
        path, cost = self.graph.search(start_cell, end_cell)
        split = -1
        for i, cell in enumerate(path):
            if MAX_CELL_X * BUFFER_LANE + 1 <= cell <= MAX_CELL_X * (BUFFER_LANE + 1):
                split = i
                break
        return split, path

    def go_agv(self, agv, priority, start_cell, end_cell, speed, flag):
        """阻塞调用"""
        conn_agv = self.agvs[agv]
        if flag == -1:
            end_cell = self.graph.get_free()
            log.debug('Current barries: %s:', self.graph.barriers)

        if start_cell is None or end_cell is None:
            log.error("%s receive wrong cell, start_cell: %s, end_cell: %s.", agv, start_cell, end_cell)

        try:
            split, path = self.get_path(start_cell, end_cell)
            log.info('Calculate path for %s <start_cell: %s, end_cell: %s, split: %s, path: %s>.', agv, start_cell, end_cell, split, path)
        except Exception as e:
            log.error("Fatal path error: %s, start_cell: %s, end_cell: %s.", e, start_cell, end_cell)
            return -1

        if split > 0:
            self.graph.set_barrier(path[split])  # 封锁该缓冲车道
            log.info('Map cell %s is blocked, current barries: %s.', path[split], self.graph.barriers)
            conn_agv.request.sendall(bytes('{"path": %s, "speed": %s, "flag": %s}' % (path[:split+1], speed, flag), encoding='utf-8'))
            log.debug('Send path to %s %s, flag is %s.', agv, path[:split+1], flag)
            response = conn_agv.recv_buffer.get()
            log.debug('%s response %s.', agv, response)
            if response != str(path[split]):
                log.error('%s response wrong cell %s.', agv, response)
                raise ValueError("%s response wrong cell %s." % (agv, response))

        if flag != -1:
            log.info('%s priority %s while end cell %s priority %s.', agv, priority, end_cell, self._cell_cur_priority[end_cell])
            while priority > self._cell_cur_priority[end_cell]:  # 等轮到该agv前去交接
                pass

        if flag != -1 and split < len(path) - 1:
            split = 0 if split == -1 else split
            conn_agv.request.sendall(bytes('{"path": %s, "speed": %s, "flag": %s}' % (path[split:], speed, flag), encoding='utf-8'))
            log.debug('Send path to %s %s, flag is %s.', agv, path[split:], flag)
            response = conn_agv.recv_buffer.get()
            log.debug('%s response %s.', agv, response)
            if response != str(path[-1]):
                log.error('%s response wrong cell %s.', agv, response)
                raise ValueError("%s response wrong cell %s." % (agv, response))
            if split > 0:
                self.graph.remove_barrier(path[split])  # 解除封锁
                log.info('Map cell %s is released, current barries: %s.', path[split], self.graph.barriers)

        return end_cell


if __name__ == '__main__':
    port = int(sys.argv[1])
    traffic_dispatcher = TrafficDispatcher(('0.0.0.0', port), AGVHandler)
    traffic_dispatcher.serve_forever()
