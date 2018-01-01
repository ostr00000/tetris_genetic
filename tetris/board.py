import numpy as np
from .tetromino import Tetromino
import matplotlib.pyplot as plt
from typing import List


class Board:
    def __init__(self, height=20, width=10):
        self.height: int = height
        self.width: int = width
        self.cells = np.zeros(shape=(height, width), dtype=int)
        self.highest_block = np.zeros(width, dtype=int)
        self.holes: List[int] = np.zeros(width, dtype=int)
        self.counter: int = 0
        self.clean_lines: int = 0

    class FullBoardError(Exception):
        pass

    def get_aggregate_height(self) -> int:
        """return sum of highest block on board"""
        return sum(self.highest_block)

    def get_completed_lines(self) -> int:
        """return number of cleaned lines"""
        return self.clean_lines

    def get_num_holes(self) -> int:
        """return all holes, holes are empty field below full field"""
        return sum(self.holes)

    def get_bumpiness(self) -> int:
        """return sum of height difference from adjacent columns"""
        ret = 0
        for i in range(self.width - 1):
            ret += abs(self.highest_block[i]
                       - self.highest_block[i + 1])
        return ret

    def _fill(self, position, height, shape):
        for i, row in enumerate(shape):
            for j, col in enumerate(row):
                cur_position = position + j
                cur_height = height - i
                if col == 'x':
                    if self.cells[cur_height, cur_position] != 0:
                        print("stop")
                    assert self.cells[cur_height, cur_position] == 0
                    self.cells[cur_height, cur_position] = self.counter

                    self._repair_holes(cur_height + 1, cur_position)
                    if cur_height + 1 > self.highest_block[cur_position]:
                        self.highest_block[cur_position] = cur_height + 1

    def add(self, tetromino: Tetromino, left_position: int):
        """
        add new tetromino on board,
        left_position - position where left side of tetromino will
        be placed on board
        """
        assert left_position >= 0
        t_width = len(tetromino.get_shape()[0])
        assert left_position + t_width <= self.width

        lowest_positions = tetromino.get_highest_positions()
        ran = range(left_position, left_position + t_width)
        max_height = max(lowest_positions[i] + self.highest_block[pos]
                         for i, pos in enumerate(ran))
        max_height -= 1

        if max_height >= self.height:
            raise Board.FullBoardError()

        self.counter += 1
        self._fill(left_position, max_height, tetromino.get_shape())
        self._repair_full_rows(max_height)
        return self

    def gen_insert_position(self, tetromino: Tetromino):
        """generate all possible positions form concrete tetromino"""
        tet_width = len(tetromino.get_shape()[0])
        for start_pos in range(self.width - tet_width + 1):
            yield start_pos

    def __str__(self):
        ret = ''
        for row in reversed(self.cells):
            for col in row:
                ret += str(col).zfill(3) + ' '
            ret += '\n'
        return ret

    def _repair_full_rows(self, height):
        is_full_row = False

        for i in range(4):
            suspected_row = height - i
            if (suspected_row >= 0
                and all(self.cells[suspected_row, j] != 0
                        for j in range(self.width))):
                self.cells = np.delete(self.cells, suspected_row, 0)
                empty = np.zeros(shape=(1, self.width), dtype=int)
                self.cells = np.append(self.cells, empty, axis=0)

                self.clean_lines += 1
                is_full_row = True

        if is_full_row:
            self._repair_highest_block()

    def _repair_holes(self, below_height, position):
        self.holes[position] = 0
        for i in range(below_height):
            if self.cells[i, position] == 0:
                self.holes[position] += 1

    def _repair_highest_block(self):
        for i in range(self.width):
            start_height = self.highest_block[i] - 1
            for j in range(start_height, -1, -1):
                if self.cells[j, i] != 0:
                    self.highest_block[i] = j + 1
                    break
            else:
                self.highest_block[i] = 0
            self._repair_holes(self.highest_block[i], i)

    def plot(self):
        plt.matshow(self.cells[::-1, :])
        plt.show()


if __name__ == "__main__":
    pass
