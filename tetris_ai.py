from board import Board, Tetromino
from typing import Tuple, NamedTuple, Union
from copy import deepcopy


class Vector(NamedTuple):
    height: int
    lines: int
    holes: int
    bumpiness: int
    board: Board = None
    tetromino: Tetromino = None
    position: int = None


class Parameters(NamedTuple):
    height: float
    lines: float
    holes: float
    bumpiness: float


class TetrisAI:
    class EndGameException(Exception):
        def __init__(self, clean_lines):
            self.clean_lines = clean_lines

    def __init__(self, parameters: Parameters):
        self.parameters = parameters

    @staticmethod
    def _add(board: Board, tetromino: Tetromino, position: int,
             lines_before: int = 0) -> Vector:
        """add new tetromino on board and returns information about move"""
        board = deepcopy(board)
        try:
            board.add(tetromino, position)
        except Board.FullBoardError:
            return TetrisAI._get_max_vector_x(board)

        height = board.get_aggregate_height()
        lines = board.get_completed_lines() - lines_before
        holes = board.get_num_holes()
        bumpiness = board.get_bumpiness()

        return Vector(height, lines, holes, bumpiness,
                      board, tetromino, position)

    @staticmethod
    def _get_max_vector_x(board: Board) -> Vector:
        big_number = board.height * board.width
        return Vector(big_number, 0, big_number, big_number)

    def choose_best_option(self, board: Board, tetromino: Tetromino,
                           ret_pos_and_rot: bool = False) \
            -> Union[Board, Tuple[int, int]]:
        """
        chose next best (board | position and rotation) depending on:
        current board, new tetromino and ai_parameters
        """

        def calc_metric(values: Vector) -> float:
            if not values.board:
                return -100
            height, lines, holes, bumpiness = values[:4]
            a, b, c, d = self.parameters
            return height * a + lines * b + holes * c + bumpiness * d

        completed_lines = board.get_completed_lines()
        best_result: Vector = TetrisAI._get_max_vector_x(board)

        for tetromino in tetromino.gen_rotation():
            for position in board.gen_insert_position(tetromino):
                result = self._add(board, tetromino, position, completed_lines)
                best_result = max((result, best_result), key=calc_metric)

        if ret_pos_and_rot:
            return best_result.position, best_result.tetromino.rotation
        return best_result.board

    def play_game(self, number_of_tetrominos: int) -> Tuple[bool, int]:
        """simulate game until tetrominos will be ended or game is over"""
        board = Board()

        for _ in range(number_of_tetrominos):
            tetromino = Tetromino()
            best_result = self.choose_best_option(board, tetromino)
            if not best_result:
                return False, board.clean_lines
            board = best_result

        return True, board.clean_lines


if __name__ == "__main__":
    pass
