import uuid
from math import sqrt
from tetris_ai import Parameters, TetrisAI
from random import uniform
from typing import NamedTuple
import pickle
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

directory = "./candidates/"
suffix = ".candidate"


class Fitness(NamedTuple):
    won_games: int
    clean_lines: int


class Candidate:
    @staticmethod
    def normalize(parameters: Parameters) -> Parameters:
        """normalize vector of parameters -> total length of vector is |1|"""
        squares_sum = sum(x * x for x in parameters)
        length = sqrt(squares_sum)
        return Parameters(*(x / length for x in parameters))

    def __init__(self, parameters: Parameters = None, fitness: Fitness = None):
        p = parameters or Parameters(*(uniform(-1, 1) for _ in range(4)))
        self.parameters = Candidate.normalize(p)
        self.fitness = fitness
        self.id = uuid.uuid4()

    def fit(self, games_number, tetrominos_in_single_game):
        """calculate fitness value"""
        ai = TetrisAI(self.parameters)
        won, total_clean_lines = 0, 0
        for i in range(games_number):
            is_win, clean_lines = ai.play_game(tetrominos_in_single_game)
            if is_win:
                won += 1
            total_clean_lines += clean_lines

        self.fitness = Fitness(won, total_clean_lines)
        self.save()
        return self

    def __lt__(self, other):
        if not isinstance(other, Candidate):
            raise TypeError
        if self.fitness.clean_lines == other.fitness.clean_lines:
            return self.fitness.won_games < other.fitness.won_games
        return self.fitness.clean_lines < other.fitness.clean_lines

    def crossover(self, other):
        """create new candidate from to parent candidates"""
        if not isinstance(other, Candidate):
            raise TypeError

        div = self.fitness.clean_lines + other.fitness.clean_lines
        if div != 0:
            weight_a = self.fitness.clean_lines / div
            weight_b = other.fitness.clean_lines / div
        else:
            weight_a = weight_b = 0.5

        def average(gen_a: float, gen_b: float):
            ret = weight_a * gen_a + weight_b * gen_b
            return ret

        c_param = Parameters(*map(average, self.parameters, other.parameters))
        return Candidate(c_param)

    def __str__(self):
        ret = ""
        if self.fitness:
            ret += "won games:" + str(self.fitness.won_games) + " "
            ret += "clean lines:" + str(self.fitness.clean_lines) + " "
        ret += str(self.parameters)
        return ret

    def get_name(self):
        return str(self.id) + suffix

    def save(self):
        name = directory + self.get_name()
        with open(name, "wb") as file:
            pickle.dump(self, file, pickle.DEFAULT_PROTOCOL)
            logger.debug("saved candidate: {}".format(name))
