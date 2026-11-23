from __future__ import annotations


def ascii_hash(text: str) -> int:
    # add up the ascii code of every letter
    total = 0
    for char in text:
        total += ord(char)
    return total


class Node:
    def __init__(self, key, value):
        self.key = key
        self.value = value
        self.next = None


class CardHashTable:
    def __init__(self, size):
        self.table = []
        for i in range(size):
            self.table.append(None)

    def put(self, key, value):
        # hash + modulo gives the position of the key in the table
        position = ascii_hash(key) % len(self.table)
        cell = self.table[position]
        new_node = Node(key, value)
        if cell is None:
            # empty position, the new node is the first one
            self.table[position] = new_node
            return
        # walk the linked list; replace the value if the key already exists
        current_node = cell
        prev_node = None
        while current_node is not None:
            if current_node.key == key:
                current_node.value = value
                return
            prev_node = current_node
            current_node = current_node.next
        prev_node.next = new_node

    def get(self, key):
        # 1. find the position with hash + modulo
        # 2. walk the linked list looking for the key
        position = ascii_hash(key) % len(self.table)
        current_node = self.table[position]
        while current_node is not None:
            if current_node.key == key:
                return current_node.value
            current_node = current_node.next
        return None


def merge(arr1, arr2, key):
    solution = []
    p1 = 0
    p2 = 0
    while p1 < len(arr1) and p2 < len(arr2):
        # the element with the smaller key goes into the solution first
        if key(arr1[p1]) <= key(arr2[p2]):
            solution.append(arr1[p1])
            p1 += 1
        else:
            solution.append(arr2[p2])
            p2 += 1
    # one of the two arrays is exhausted, copy the rest of the other one
    while p1 < len(arr1):
        solution.append(arr1[p1])
        p1 += 1
    while p2 < len(arr2):
        solution.append(arr2[p2])
        p2 += 1
    return solution


def msort(arr, key):
    if len(arr) < 2:
        return arr
    # divide it in half
    mid = len(arr) // 2
    left_half = []
    right_half = []
    for i in range(len(arr)):
        if i < mid:
            left_half.append(arr[i])
        else:
            right_half.append(arr[i])
    # sort both halves recursively, then merge them
    left_half_sorted = msort(left_half, key)
    right_half_sorted = msort(right_half, key)
    return merge(left_half_sorted, right_half_sorted, key)
