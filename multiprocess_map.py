from multiprocess import parallel_map
from typing import Tuple, List
from candidate import Candidate
import logging

logger = logging.getLogger(__name__)


def map_function(candid_games_tetrominos: Tuple[Candidate, int, int]):
    if isinstance(candid_games_tetrominos, int):
        print("not iterable")
    logger.debug("map function with arg: {}".format(candid_games_tetrominos))
    candid, games, tetrominos = candid_games_tetrominos
    return candid.fit(games, tetrominos)


def parallel_map_fun(candid_game_tetromino: List[Tuple[Candidate, int, int]]):
    logger.debug("parallel map fun")
    return parallel_map(map_function, candid_game_tetromino)
