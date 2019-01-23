from functools import wraps
import math

BAY_NUM = 9
MAX_CELL_X = 40
MAX_CELL_Y = 12
BUFFER_LANE = 5


def lane2position(position, lane):
    if position < MAX_CELL_X:
        return (lane - 1) * MAX_CELL_X + position
    else:
        return lane


def position2xy(position):
    x = position % MAX_CELL_X - 1
    y = math.floor(position / MAX_CELL_X)
    return x, y


def xy2position(x, y):
    return y * MAX_CELL_X + x + 1


def fix_path(search_func):
    @wraps(search_func)
    def decorated(*args, **kwargs):
        start_point, end_point = args[1], args[2]
        search_start, search_end = start_point, end_point
        start_fix, end_fix = [], []
        if 0 < start_point <= MAX_CELL_X * BUFFER_LANE:
            search_start -= 2
            start_fix = [start_point, start_point - 1]
        if MAX_CELL_X * MAX_CELL_Y + 1 <= start_point <= MAX_CELL_X * (MAX_CELL_Y + 1):
            search_start -= MAX_CELL_X * 2
            start_fix = [start_point, start_point - MAX_CELL_X]
        if 0 < end_point <= MAX_CELL_X * BUFFER_LANE:
            search_end += 2
            end_fix = [end_point + 1, end_point]
        if MAX_CELL_X * MAX_CELL_Y + 1 <= end_point <= MAX_CELL_X * (MAX_CELL_Y + 1):
            search_end -= MAX_CELL_X * 2
            end_fix = [end_point - MAX_CELL_X, end_point]

        raw_path, cost = search_func(args[0], position2xy(search_start), position2xy(search_end), **kwargs)
        fixed_path = start_fix + [xy2position(x, y) for x, y in raw_path] + end_fix

        pos_xy = []
        point_turn = []
        for item in fixed_path:
            pos_xy.append(position2xy(item))
        for index in range(len(pos_xy) - 2):
            A1 = pos_xy[index]
            B1 = A2 = pos_xy[index + 1]
            B2 = pos_xy[index + 2]
            vector_algorithm = (B1[0] - A1[0]) * (B2[0] - A2[0]) + (B1[1] - A1[1]) * (B2[1] - A2[1])
            if vector_algorithm == 0:
                point_turn.append(xy2position(B1[0], B1[1]))

        for ii in point_turn:
            if ii in fixed_path:
                fixed_path.remove(ii)

        return fixed_path, cost
    return decorated


def display(path):
    mat = [[0 for j in range(MAX_CELL_X)] for i in range(MAX_CELL_Y + 1)]
    for cell in path:
        x, y = position2xy(cell)
        mat[y][x] = 1
    for line in mat:
        for cell in line:
            if cell == 1:
                print('*', end='')
            else:
                print('-', end='')
        print()


class AStarGraph(object):
    # Define a class board like grid with two barriers
    MAX_COST = 1000

    def __init__(self):
        # set barriers to empty, change the AdjMatr in  procession
        self._barriers = []
        self.adj_matrix = self.AdjMatr(MAX_CELL_X)

    @property
    def barriers(self):
        return self._barriers

    def set_barrier(self, cell):
        self._barriers.append(position2xy(cell))

    def get_free(self):
        for i in range(BUFFER_LANE * MAX_CELL_X + 1, (BUFFER_LANE + 1) * MAX_CELL_X):
            if position2xy(i) not in self._barriers:
                return i

    def remove_barrier(self, cell):
        self._barriers.remove(position2xy(cell))

    def AdjMatr(self, y):  # y：num of col
        # trail = 11  # NUMBER OF TRAIL ---
        NumOfNode = 11 * y
        list = [[] for _ in range(NumOfNode)]
        for i in range(NumOfNode):
            for j in range(NumOfNode):
                list[i].append(float('inf'))
        # Notes: list direction
        # like node 1 -> node 2 and node 2 /-> node 1
        #  =>  list[0][1] = 1 and list[1][0] = inf
        # trail index about direction
        # # Slash route only up and down
        Left = [1, 2, 3, 4, 5, 8, 10]
        Right = [7, 9, 11]
        for k in Left:  # left
            for h in range(1, y):
                list[y * (k - 1) + h][y * (k - 1) + h - 1] = 1
        for L in Right:  # right
            for m in range(0, y - 1):
                list[y * (L - 1) + m][y * (L - 1) + m + 1] = 1
        for n in range(1, y + 1):  # down & up
            for o in range(1, 11):
                list[n - 1 + y * (o - 1)][n - 1 + y * o] = 1
            for q in range(2, 11 + 1):
                list[n - 1 + y * (q - 1)][n - 1 + y * (q - 2)] = 1
        '''
        print(len(list))
        for item in list:
            print(item)

        print("22222222222222222222222222222222222222222222222222222222222222")
        '''
        return list

    def heuristic(self, start, goal):
        # Use Chebyshev(Пафну́тий Льво́вич ) distance heuristic if we can move one square either
        # adjacent or diagonal
        D = 1
        D2 = 1
        dx = abs(start[0] - goal[0])
        dy = abs(start[1] - goal[1])
        return D * (dx + dy) + (D2 - 2 * D) * min(dx, dy)


    def heuristic_Eu(self,start,goal):
        # Use Euclidean distance
        dx = abs(start[0] - goal[0])
        dy = abs(start[1] - goal[1])
        return  pow(dx,2)+pow(dy,2)

    def heruistic_Man(self,start,goal):
        # Use Manhattan distance
        dx = abs(start[0] - goal[0])
        dy = abs(start[1] - goal[1])
        return dx + dy

    def get_vertex_neighbours(self, pos):
        n = []
        # Moves allow link a chess king
        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            x2 = pos[0] + dx
            y2 = pos[1] + dy

            if (x2>=0) and (x2<=MAX_CELL_X-1) and (y2>=0) and (y2<=MAX_CELL_Y-1-1): # para border
                # MAX_CELL_Y
                '''
                node_cur = pos[1]*40 + pos[0] + 1
                node_next = y2*40 + x2 + 1
                '''
                node_cur = pos[1]*MAX_CELL_X + pos[0] + 1
                node_next = y2*MAX_CELL_X + x2 +1
                if (node_next<=MAX_CELL_X*(MAX_CELL_Y-1)-1) and (node_next>=0) and (node_cur<=MAX_CELL_X*(MAX_CELL_Y-1)-1) and (node_cur>=0):
                    '''
                    print("cur:", pos[0], pos[1])
                    print("next:", x2, y2)
                    print("node_cur",node_cur)
                    print("node_next",node_next)
                    '''
                    if self.adj_matrix[node_cur][node_next] == 1:
                        '''
                        print("afterIf_cur:", pos[0], pos[1])
                        print("afterIf_next:", x2, y2)
                        print("afterIf_node_cur", node_cur)
                        print("afterIf_node_next", node_next)
                        '''
                        n.append((x2, y2))
                    else:
                        continue
                else:
                    continue
        return n

    def move_cost(self, a, b):
        # if the final cost is MAX_COST -> mission failed
        if b in self.barriers:
            return self.MAX_COST  # Extremely high cost to enter barrier squares
        return 1  # Normal movement cost

    @fix_path
    def search(self, start, end):
        G = {}  # Actual movement cost to each position from the start position
        F = {}  # Estimated movement cost of start to end going via this position
        # Initialize starting values
        G[start] = 0
        F[start] = self.heuristic(start, end)

        closedVertices = set()
        openVertices = set([start])
        cameFrom = {}
        while len(openVertices) > 0:
            # Get the vertex in the open list with the lowest F score
            current = None
            currentFscore = None
            for pos in openVertices:
                if current is None or F[pos] < currentFscore:
                    currentFscore = F[pos]
                    current = pos

            # Check if we have reached the goal
            if current == end:
                # Retrace our route backward
                path = [current]
                while current in cameFrom:
                    current = cameFrom[current]
                    path.append(current)
                path.reverse()
                return path, F[end]  # Done!

            # Mark the current vertex as closed
            openVertices.remove(current)
            closedVertices.add(current)

            # Update scores for vertices near the current position
            for neighbour in self.get_vertex_neighbours(current):
                if neighbour in closedVertices:
                    continue  # We have already processed this node exhaustively
                candidateG = G[current] + self.move_cost(current, neighbour)

                if neighbour not in openVertices:
                    openVertices.add(neighbour)  # Discovered a new vertex
                elif candidateG >= G[neighbour]:
                    continue  # This G score is worse than previously found

                # Adopt this G score
                cameFrom[neighbour] = current
                G[neighbour] = candidateG
                H = self.heuristic(neighbour, end)
                F[neighbour] = G[neighbour] + H

        return [], 1001
        # raise RuntimeError("A* failed to find a solution")


if __name__ == "__main__":
    import time

    # print(lane2position(10, 2), lane2position(482, 482))
    # print(position2xy(201))
    graph = AStarGraph()
    graph.set_barrier(201)

    print(graph.get_free())

    now = time.time()
    # result, _ = graph.search(50, 510)
    # result1, _ = graph.search(215, 481)
    # result2, _ = graph.search(215, 515)
    # result3, _ = graph.search(70, 215)
    # result4, _ = graph.search(491, 50)
    # result5, _ = graph.search(518, 489)
    # result6, _ = graph.search(70, 50)
    # result7, _ = graph.search(50, 70)
    # result8, _ = graph.search(481, 519)
    result9, _ = graph.search(70, 201)
    print(time.time() - now)

    # print(result)
    # display(result)
    # print(result1)
    # display(result1)
    # print(result2)
    # display(result2)
    # print(result3)
    # display(result3)
    # print(result4)
    # display(result4)
    # print(result5)
    # display(result5)
    # print(result6)
    # display(result6)
    # print(result7)
    # display(result7)
    # display(result8)
    # print(result8)
    print(result9)
    display(result9)
