import logging
import multiprocessing
from typing import Iterable, Callable, TypeVar, List

logger = logging.getLogger(__name__)

T = TypeVar('T')
M = TypeVar('M')


def fun(f: Callable[[T], M], q_in, q_out):
    while True:
        i, x = q_in.get()
        if i is None:
            break
        f_x = f(x)
        q_out.put((i, f_x))
        logger.debug("id: {}, status: {}".format(i, str(f_x)))


def parallel_map(map_function: Callable[[T], M], data: Iterable[T],
                 n_process: int = multiprocessing.cpu_count()) -> List[M]:
    q_in = multiprocessing.Queue(1)
    q_out = multiprocessing.Queue()

    processes = [
        multiprocessing.Process(target=fun, args=(map_function, q_in, q_out))
        for _ in range(n_process)
    ]

    for p in processes:
        p.daemon = True
        p.start()

    sent = [q_in.put((i, x)) for i, x in enumerate(data)]
    [q_in.put((None, None)) for _ in range(n_process)]
    res = [q_out.get() for _ in range(len(sent))]

    [p.join() for p in processes]

    return [x for i, x in sorted(res)]
