import unittest
from tetris.board import Board
from tetris.tetromino import Tetromino
from tetris.tetris_ai import TetrisAI, Parameters
from candidate import Candidate, Fitness
from genetic_algorithm import GeneticAlgorithm, DEFAULT_HOST, DEFAULT_PORT
from python_socket_client_server import client
from multiprocessing import Process


class TetrominoTest(unittest.TestCase):
    def setUp(self):
        self.all_tetrominos = Tetromino.shape.keys()

    def test_eq(self):
        """test equal function"""
        t1 = Tetromino("O")
        t2 = Tetromino("O")
        t3 = Tetromino("I")
        t4 = Tetromino("I")

        self.assertEqual(t1, t2)
        t2.next_rotation()
        self.assertEqual(t1, t2)

        self.assertNotEqual(t1, t3)
        self.assertEqual(t3, t4)
        t4.next_rotation()
        self.assertNotEqual(t3, t4)

        for a_symbol in self.all_tetrominos:
            for b_symbol in self.all_tetrominos:
                a = Tetromino(a_symbol)
                b = Tetromino(b_symbol)
                if a_symbol == b_symbol:
                    self.assertEqual(a, b)
                else:
                    for bb in b.gen_rotation():
                        self.assertNotEqual(a, bb)

    def test_next_rotation(self):
        """test rotation function"""
        for symbol, rotations in zip("ISZTJOL", [2, 2, 2, 4, 4, 1, 4]):
            t1 = Tetromino(symbol)
            t2 = Tetromino(symbol)
            self.assertEqual(t1, t2)

            for i in range(rotations - 1):
                t2.next_rotation()
                self.assertNotEqual(t1, t2)

            t2.next_rotation()
            self.assertEqual(t1, t2)


class BoardTests(unittest.TestCase):
    def test_add(self):
        """test exception if board is full"""
        board = Board(10, 3)
        t = Tetromino("O")

        for i in range(5):
            board.add(t, 0)

        with self.assertRaises(Board.FullBoardError):
            board.add(t, 0)

    def test_gen_position(self):
        """test possible to insert position"""
        t1 = Tetromino("O")
        t2 = Tetromino("I")
        for i in (1, 2, 3, 5, 10, 20, 50):
            pos = list(Board(10, i).gen_insert_position(t1))
            self.assertEqual(pos, list(range(i - 1)))

            pos = list(Board(10, i).gen_insert_position(t2))
            self.assertEqual(pos, list(range(i - 3)))

    def test_clean(self):
        """test remove blocks from board"""
        t = Tetromino("I")
        b = Board(10, 4)

        for i in range(12):
            b.add(t, 0)
            self.assertEqual(b.highest_block[0], 0)
            self.assertEqual(b.highest_block[1], 0)
            self.assertEqual(b.highest_block[2], 0)
            self.assertEqual(b.highest_block[3], 0)

    def test_height(self):
        """test sum of all heights"""
        b = Board()
        b.add(Tetromino("T"), 0)
        self.assertEqual(b.get_aggregate_height(), 6)

        b = Board()
        t = Tetromino("T").next_rotation()
        self.assertEqual(b.add(t, 0).get_aggregate_height(), 5)

        b = Board()
        t = Tetromino("I").next_rotation()
        for i in range(1, 6):
            b.add(t, 0)
            self.assertEqual(b.get_aggregate_height(), 4 * i)

        b = Board(10, 4)
        self.assertEqual(b.add(Tetromino("S"), 0).get_aggregate_height(), 5)
        self.assertEqual(b.add(t, 3).get_aggregate_height(), 9)
        t = Tetromino("L").next_rotation().next_rotation()
        self.assertEqual(b.add(t, 0).get_aggregate_height(), 4)
        self.assertEqual(b.add(Tetromino("I"), 0).get_aggregate_height(), 4)

        b = Board(20, 3)
        t = Tetromino("I").next_rotation()
        self.assertEqual(b.add(t, 0).get_aggregate_height(), 4)
        self.assertEqual(b.add(t, 0).get_aggregate_height(), 8)
        self.assertEqual(b.add(Tetromino("O"), 1).get_aggregate_height(), 6)

    def test_lines(self):
        """test completed lines counter"""
        t1 = Tetromino("I")
        t2 = Tetromino("O")
        b = Board(10, 4)

        self.assertEqual(b.add(t1, 0).get_completed_lines(), 1)
        self.assertEqual(b.add(t2, 0).get_completed_lines(), 1)
        self.assertEqual(b.add(t1, 0).get_completed_lines(), 2)
        self.assertEqual(b.add(t2, 2).get_completed_lines(), 4)
        self.assertEqual(b.add(t1, 0).get_completed_lines(), 5)

    def test_holes(self):
        """test sum of unfilled places for block"""
        t = Tetromino("Z")
        b = Board(10, 6)

        self.assertEqual(b.add(t, 0).get_num_holes(), 1)
        self.assertEqual(b.add(t, 0).get_num_holes(), 3)
        t.next_rotation()
        self.assertEqual(b.add(t, 3).get_num_holes(), 4)

        b = Board(10, 5)
        t1 = Tetromino("O")
        t2 = Tetromino("I")

        self.assertEqual(b.add(t1, 0).get_num_holes(), 0)
        self.assertEqual(b.add(t2, 0).get_num_holes(), 4)
        b.add(t2.next_rotation(), 4)
        self.assertEqual(b.get_num_holes(), 0)

    def test_bumpiness(self):
        """test height difference in connected columns"""
        t = Tetromino("I").next_rotation()
        b = Board(10, 4)

        self.assertEqual(b.add(t, 0).get_bumpiness(), 4)
        self.assertEqual(b.add(t, 2).get_bumpiness(), 12)
        self.assertEqual(b.add(t, 1).get_bumpiness(), 4)
        self.assertEqual(b.add(t, 3).get_bumpiness(), 0)


class TetrisAITest(unittest.TestCase):
    def test_height(self):
        """ai want to have height column"""
        b = Board(20, 2)
        t = Tetromino("I").next_rotation()
        ai = TetrisAI(Parameters(1, 0, 0, 0))

        for _ in range(3):
            b = ai.choose_best_option(b, t)

        left, right = b.highest_block[0], b.highest_block[1]

        self.assertEqual(max(left, right), 12)
        self.assertEqual(min(left, right), 0)

        self.assertEqual(b.get_aggregate_height(), 12)
        self.assertEqual(b.get_num_holes(), 0)
        self.assertEqual(b.get_bumpiness(), 12)
        self.assertEqual(b.get_completed_lines(), 0)

    def test_lines(self):
        """
        ai want to clean lines

        test 5 "I" tetrominos on board with width equal to 5
         -> should be 4 cleaned lines
        """
        b = Board(20, 5)
        t = Tetromino("I")
        ai = TetrisAI(Parameters(0, 1, 0, 0))

        for _ in range(5):
            b = ai.choose_best_option(b, t)

        self.assertEqual(b.get_aggregate_height(), 0)
        self.assertEqual(b.get_num_holes(), 0)
        self.assertEqual(b.get_bumpiness(), 0)
        self.assertEqual(b.get_completed_lines(), 4)

    def test_holes(self):
        """
        ai want to have maximal number of holes
        3333o
        o2222
        oooo1
        oooo1
        oooo1
        oooo1
        """
        b = Board(20, 5)
        t = Tetromino("I")
        ai = TetrisAI(Parameters(0, 0, 1, 0))

        for _ in range(3):
            b = ai.choose_best_option(b, t)

        self.assertEqual(b.get_aggregate_height(), 29)
        self.assertEqual(b.get_num_holes(), 17)
        self.assertEqual(b.get_bumpiness(), 1)
        self.assertEqual(b.get_completed_lines(), 0)

    def test_bumpiness(self):
        """ai want to have maximal number of bumpiness"""
        b = Board(5, 7)
        t = Tetromino("I")
        ai = TetrisAI(Parameters(0, 0, 0, 1))

        for _ in range(3):
            b = ai.choose_best_option(b, t)

        self.assertEqual(b.get_aggregate_height(), 12)
        self.assertEqual(b.get_num_holes(), 0)
        self.assertEqual(b.get_bumpiness(), 24)
        self.assertEqual(b.get_completed_lines(), 0)


class CandidateTest(unittest.TestCase):
    def test_normalize(self):
        p_n = Candidate.normalize(Parameters(4, 4, 4, 4))
        for a, b in zip(p_n, Parameters(0.5, 0.5, 0.5, 0.5)):
            self.assertAlmostEqual(a, b)

        p_n = Candidate.normalize(Parameters(4, 0, 0, 0))
        for a, b in zip(p_n, Parameters(1, 0, 0, 0)):
            self.assertAlmostEqual(a, b)

    def test_crossover(self):
        parent1 = Candidate(Parameters(2, 9, 12, -4), Fitness(0, 10))
        parent2 = Candidate(Parameters(4, 2, 9, 12), Fitness(0, 10))
        child = parent1.crossover(parent2)
        parameters = Candidate.normalize(Parameters(3, 5.5, 10.5, 4))

        for c, t in zip(child.parameters, parameters):
            self.assertAlmostEqual(c, t)

    def test_fit(self):
        c = Candidate(Parameters(-1, 1, -1, -1))

        c.fit(1, 1)
        self.assertEqual(c.fitness.clean_lines, 0)
        self.assertEqual(c.fitness.won_games, 1)

        c.fit(10, 1)
        self.assertEqual(c.fitness.clean_lines, 0)
        self.assertEqual(c.fitness.won_games, 10)

        c.fit(7, 4)
        self.assertEqual(c.fitness.won_games, 7)


class GeneticAlgorithmTest(unittest.TestCase):
    def test_generate_population(self):
        with GeneticAlgorithm(100, games_number=1, tetrominos_in_single_game=1,
                              offsprings_num=10, load_files=False) as ga:
            self.assertEqual(ga.population, None)
            ga._generate_population()
            self.assertEqual(len(ga.population), 100)

    @staticmethod
    def client_work():
        c = client.Client(DEFAULT_HOST, DEFAULT_PORT)
        c.start_client()

    def test_fit_all(self):
        """test all types of fit function"""
        p = Process(target=self.client_work, name="client")

        for t in GeneticAlgorithm.fit_types.keys():
            with GeneticAlgorithm(10, offsprings_num=1, fit_type=t,
                                  parents_num_in_tournament=1,
                                  games_number=3, load_files=False,
                                  tetrominos_in_single_game=5) as ga:
                if t == "socket":
                    p.start()
                candidates = ga._fit_all([Candidate() for _ in range(10)])

                self.assertEqual(len(candidates), 10)
                for candidate in candidates:
                    self.assertIsNotNone(candidate.fitness)

        p.join()

    def test_end_condition(self):
        """genetic algorithm end when all games are won"""
        with GeneticAlgorithm(10, offsprings_num=1,
                              parents_num_in_tournament=1,
                              games_number=1, load_files=False,
                              tetrominos_in_single_game=1) as ga:
            ga._generate_population()
            ga.population = ga._fit_all(ga.population)
            self.assertTrue(ga._is_end_condition())

            c: Candidate = ga.population[0]
            c.fitness = Fitness(0, 0)
            self.assertFalse(ga._is_end_condition())

    def test_create_offsprings(self):
        """new offspring should have parents traits"""
        with GeneticAlgorithm(2, offsprings_num=1,
                              parents_num_in_tournament=2,
                              games_number=1, load_files=False,
                              tetrominos_in_single_game=1) as ga:
            ga.population = [Candidate(Parameters(1, 0, 0, 0)),
                             Candidate(Parameters(0, 0, 0, 1))]
            ga.population = ga._fit_all(ga.population)
            ga._create_offsprings()
            offspring: Candidate = ga.offsprings[0]

            available = [ga.population[0].parameters,
                         ga.population[1].parameters,
                         Candidate(Parameters(1, 0, 0, 1)).parameters]

            self.assertIn(offspring.parameters, available)

    def test_mutate_offsprings(self):
        with GeneticAlgorithm(2, parents_num_in_tournament=1, offsprings_num=1,
                              mutation_chance=1.1, load_files=False,
                              mutation_max_value=1) as ga:
            original = Candidate(Parameters(1, 1, 1, 1))
            ga.offsprings = [original]
            ga._mutate_offsprings()

            self.assertNotEqual(original.parameters,
                                ga.offsprings[0].parameters)

    def test_parameters_influence(self):
        a = Candidate(Parameters(1, 0, 1, 1))
        b = Candidate(Parameters(-1, 1, -1, -1))

        with GeneticAlgorithm(10, offsprings_num=2, games_number=5,
                              tetrominos_in_single_game=300, load_files=False,
                              parents_num_in_tournament=2) as ga:

            [a, b] = ga._fit_all([a, b])

        self.assertGreaterEqual(b.fitness.won_games, a.fitness.won_games)
        self.assertGreaterEqual(b.fitness.clean_lines, a.fitness.clean_lines)


if __name__ == "__main__":
    unittest.main()
