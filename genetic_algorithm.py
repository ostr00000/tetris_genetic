from tetris.tetris_ai import Parameters
from random import random, randrange, uniform
from typing import List, Tuple
from multiprocess_map import parallel_map_fun
from python_socket_client_server.server import Server
import pickle
import logging
import os
from candidate import Candidate, directory

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
old_filename = "old.genetic"

DEFAULT_HOST, DEFAULT_PORT = 'localhost', 45054


class GeneticAlgorithm:
    fit_types = {
        "single": 0,
        "multi": 1,
        "socket": 2
    }

    REQUIRED_DIR = [
        "tetris/"
    ]

    REQUIRED_FILES = [
        "multiprocess_map.py",
        "multiprocess.py",
        "candidate.py",
        "tetris/__init__.py",
        "tetris/tetris_ai.py",
        "tetris/board.py",
        "tetris/tetromino.py",
    ]

    @staticmethod
    def receive_function(c: Candidate):
        c.save()

    def __init__(self,
                 num_of_population: int,
                 games_number: int = 100,
                 tetrominos_in_single_game: int = 500,
                 parents_num_in_tournament: int = 100,
                 offsprings_num: int = 300,
                 mutation_chance: float = 0.05,
                 mutation_max_value: float = 0.2,
                 load_files: bool = True,
                 fit_type: str = "multi"):

        assert num_of_population >= parents_num_in_tournament
        assert num_of_population >= offsprings_num

        self.population: List[Candidate] = None
        self.offsprings: List[Candidate] = None
        self.num_of_population = num_of_population
        self.games_number = games_number
        self.tetrominos_in_single_game = tetrominos_in_single_game
        self.parents_num_in_tournament = parents_num_in_tournament
        self.offsprings_num = offsprings_num
        self.mutation_chance = mutation_chance
        self.mutation_max_value = mutation_max_value
        self.load_files = load_files

        if load_files:
            self._compare_last_algorithm()

        if fit_type not in GeneticAlgorithm.fit_types:
            raise ValueError("wrong fit_type")
        else:
            self.fit_type: int = GeneticAlgorithm.fit_types[fit_type]

        if fit_type == "socket":
            self._start_socket()

    def _compare_last_algorithm(self):
        if old_filename in os.listdir("."):
            with open(old_filename, "rb") as old_file:
                old_alg = pickle.load(old_file)
                assert old_alg == self
                logger.debug("saved candidates are valid")

        with open(old_filename, "wb") as new_file:
            pickle.dump(self, new_file)

    def __eq__(self, other):
        if not isinstance(other, GeneticAlgorithm):
            return False
        return self.__dict__ == other.__dict__

    def _generate_population(self):
        """create random population or load from files"""

        self.population: List[Candidate] = []
        if self._is_saved():
            self._load_from_files()

        new_population = []
        for _ in range(self.num_of_population - len(self.population)):
            new_population.append(Candidate(auto_save=self.load_files))

        self.population.extend(self._fit_all(new_population))

    def _is_saved(self):
        if not os.path.exists(directory):
            os.mkdir(directory)
        return self.load_files and os.listdir(directory)

    def _load_from_files(self):
        for filename in os.listdir(directory):
            assert filename.endswith(".candidate")
            with open(directory + filename, "rb") as file:
                candidate: Candidate = pickle.load(file)
                logger.debug("load candidate: {}".format(filename))
                self.population.append(candidate)
            if len(self.population) == self.num_of_population:
                break

    def _fit_all(self, candidates: List[Candidate]) -> List[Candidate]:
        """calculate fitness value for candidates"""

        #  one computer one thread
        if self.fit_type == GeneticAlgorithm.fit_types["single"]:
            ret = []
            for i, candidate in enumerate(candidates):
                ret.append(candidate.fit(self.games_number,
                                         self.tetrominos_in_single_game))
                logger.debug("iteration: {}, status: {}".format(i, candidate))
            return ret

        # one computer many threads
        elif self.fit_type == GeneticAlgorithm.fit_types["multi"]:
            g, t = self.games_number, self.tetrominos_in_single_game
            candidates = list(map(lambda x: (x, g, t), candidates))
            return parallel_map_fun(candidates)

        # many computers many threads
        elif self.fit_type == GeneticAlgorithm.fit_types["socket"]:
            g, t = self.games_number, self.tetrominos_in_single_game

            for c in candidates:
                c.auto_save = False

            candidates = list(map(lambda x: (x, g, t), candidates))
            candidates = self.server.send_data_to_compute(
                candidates, "multiprocess_map", "parallel_map_fun"
            )
            if self.load_files:
                for c in candidates:
                    c.save()
            return candidates

    def _is_end_condition(self) -> bool:
        """test if algorithm can be ended"""

        def has_won(candidate: Candidate) -> bool:
            return candidate.fitness.won_games == self.games_number

        return all(map(has_won, self.population))

    def _select_one_parent(self) -> Candidate:
        """select parent by tournament selection"""
        selected = []
        for i in range(self.parents_num_in_tournament):
            randomised_id = randrange(0, self.num_of_population)
            selected.append(self.population[randomised_id])

        return max(selected)

    def _create_offsprings(self):
        """create new offsprings selecting all parents independently"""
        offsprings = []
        for i in range(self.offsprings_num):
            parent_a = self._select_one_parent()
            parent_b = self._select_one_parent()
            child = parent_a.crossover(parent_b)
            offsprings.append(child)

        self.offsprings: List[Candidate] = offsprings

    def _mutate_offsprings(self):
        """can change parameters of offsprings"""
        for child_id in range(len(self.offsprings)):
            if random() < self.mutation_chance:
                mutation: float = uniform(-1, 1) * self.mutation_max_value
                insert_index = randrange(0, 4)

                t4 = Tuple[float, float, float, float]
                old_par: t4 = self.offsprings[child_id].parameters
                args: t4 = (
                    old_par[:insert_index]
                    + (old_par[insert_index] + mutation,)
                    + old_par[insert_index + 1:]
                )
                self.offsprings[child_id] = \
                    Candidate(Parameters(*args), auto_save=self.load_files)

    def _select_survivors(self):
        """replace worst candidate with offsprings"""
        self.population.sort(reverse=True)
        to_delete = self.population[-self.offsprings_num:]
        if self.load_files:
            self._delete_files(to_delete)
        self.population = self.population[:-self.offsprings_num]
        self.population.extend(self.offsprings)
        self.offsprings = None

    @staticmethod
    def _delete_files(to_delete: List[Candidate]):
        for candidate in to_delete:
            filename = directory + candidate.get_name()
            logger.debug("deleting file: {}".format(filename))
            os.remove(filename)

    def __str__(self):
        if self.population:
            counter = 0
            for pop in self.population:
                counter += pop.fitness.won_games

            total = (len(self.population) * self.games_number)
            avr = float(counter) / total
            return str(avr) + "=" + str(counter) + "/" + str(total)
        else:
            return str(self.__dict__)

    def find_best_parameters(self) -> Parameters:
        """find best parameters for current settings"""
        self._generate_population()

        generation = 0
        while not self._is_end_condition():
            logger.info("{} game won: {}".format(generation, self))
            generation += 1

            self._create_offsprings()
            self._mutate_offsprings()
            self.offsprings = self._fit_all(self.offsprings)
            self._select_survivors()

        best_candidate: Candidate = max(self.population)
        self.population = None
        return best_candidate.parameters

    def _start_socket(self):
        self.server = Server(DEFAULT_HOST, DEFAULT_PORT,
                             self.REQUIRED_DIR, self.REQUIRED_FILES,
                             GeneticAlgorithm.receive_function)
        self.server.start_server()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.fit_type == GeneticAlgorithm.fit_types["socket"]:
            self.server.stop_server()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    logger.addHandler(logging.FileHandler('./console.log', mode='w'))

    with GeneticAlgorithm(num_of_population=100,
                          games_number=100,
                          tetrominos_in_single_game=500,
                          parents_num_in_tournament=10,
                          offsprings_num=30,
                          mutation_chance=0.05,
                          mutation_max_value=0.2,
                          fit_type="multi") as ga:
        best = ga.find_best_parameters()
        logger.info("best result: {}".format(best))
