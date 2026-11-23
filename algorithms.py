from __future__ import annotations


def count_recipients(recipients: list[int]) -> dict[int, int]:
    counts: dict[int, int] = {}
    for player_id in recipients:
        if player_id in counts:
            counts[player_id] += 1
        else:
            counts[player_id] = 1
    return counts


class MyStack:
    def __init__(self, data=None):
        self.data = [] if data is None else data

    def push(self, value):
        self.data.append(value)

    def pull(self):
        if self.empty():
            return None
        value = self.data[len(self.data) - 1]
        self.data.pop(len(self.data) - 1)
        return value

    def empty(self):
        return len(self.data) == 0


class MyQueue:
    def __init__(self, size):
        if size < 1:
            raise ValueError("Queue size must be positive")
        self.data = [None] * size
        self.tail = -1
        self.head = -1
        self.absent = True
        self.complete = False

    def enque(self, value):
        if self.full():
            return False
        self.data[self.head] = value
        self.head -= 1
        if self.head < -len(self.data):
            self.head = -1
        if self.absent:
            self.absent = False
        if self.head == self.tail:
            self.complete = True
        return True

    def deque(self):
        if self.empty():
            return None
        value = self.data[self.tail]
        self.data[self.tail] = None
        self.tail -= 1
        if self.tail < -len(self.data):
            self.tail = -1
        if self.complete:
            self.complete = False
        if self.tail == self.head:
            self.absent = True
        return value

    def empty(self):
        return self.absent

    def full(self):
        return self.complete

    def front(self):
        if self.empty():
            return None
        return self.data[self.tail]


def rotate_judges_left(judge_queue, positions: int = 1) -> None:
    if positions < 0:
        raise ValueError("positions cannot be negative")
    for i in range(positions):
        first_judge = judge_queue.deque()
        judge_queue.enque(first_judge)


def _comes_before(first_id: int, second_id: int, players) -> bool:
    first_score = players[first_id].score
    second_score = players[second_id].score
    if first_score != second_score:
        return first_score > second_score
    return first_id < second_id


def _partition_player_indices(indices: list[int], players, low: int, high: int) -> int:
    pivot_position = (low + high) // 2
    indices[pivot_position], indices[high] = indices[high], indices[pivot_position]
    pivot_id = indices[high]
    boundary = low - 1
    for current in range(low, high):
        if _comes_before(indices[current], pivot_id, players):
            boundary += 1
            indices[boundary], indices[current] = indices[current], indices[boundary]
    pivot_final = boundary + 1
    indices[pivot_final], indices[high] = indices[high], indices[pivot_final]
    return pivot_final


def _quicksort_indices(indices: list[int], players, low: int, high: int) -> None:
    if low >= high:
        return
    pivot_final = _partition_player_indices(indices, players, low, high)
    _quicksort_indices(indices, players, low, pivot_final - 1)
    _quicksort_indices(indices, players, pivot_final + 1, high)


def quicksort_player_indices(players) -> list[int]:
    indices: list[int] = []
    for player_id in range(len(players)):
        indices.append(player_id)
    if len(indices) > 1:
        _quicksort_indices(indices, players, 0, len(indices) - 1)
    return indices
