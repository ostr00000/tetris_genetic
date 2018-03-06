import itertools

from .connection import *
from typing import List, Callable, Any
import threading
import os
import select
import logging

SLEEP_TIME = 3
CLIENT_TIMEOUT = 1

socket.setdefaulttimeout(CLIENT_TIMEOUT)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class Server:
    def __init__(self, host, port,
                 required_dir: List[str],
                 required_files: List[str],
                 receive_function: Callable[[Any], Any] = None):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((host, port))
        self.sock.listen()
        self.sock.settimeout(SLEEP_TIME)

        logger.info("Server started on {}:{}".format(host, port))

        self.lock = threading.Lock()
        self.workers = {}
        self.loop_thread = threading.Thread(target=self._server_loop)
        self.end_flag = threading.Event()

        self.required_dir = required_dir
        self.required_files = list(map(
            lambda name: (name, os.stat(name).st_size), required_files
        ))

        self.receive_function = receive_function

    def _send_files(self, client):
        send(len(self.required_dir), client)
        for dir_name in self.required_dir:
            send(dir_name, client)

        send(len(self.required_files), client)
        for filename, _size in self.required_files:
            with open(filename, 'r') as file:
                data = file.read()
                send(filename, client)
                send(data, client)

    def start_server(self):
        self.loop_thread.start()

    def stop_server(self):
        self.end_flag.set()
        self.loop_thread.join()

    def _server_loop(self):
        while not self.end_flag.is_set():
            try:
                connection, address = self.sock.accept()
                logger.debug("accepted connection from :{}".format(address))
            except socket.timeout:
                logger.debug("no one has been connected")
                continue

            try:
                send((self.required_dir, self.required_files), connection)
                logger.debug("sent required dir: {} and files: {}"
                             .format(self.required_dir, self.required_files))

                response = receive(connection)
                if response == MessageType.download:
                    self._send_files(connection)
                    logger.debug("modules sent")

                    response = receive(connection)

                if response == MessageType.get_work:
                    quantity = receive(connection)
                    with self.lock:
                        self.workers[connection] = [quantity, False]
                    logger.debug("worker added - address: {}".format(address))
                else:
                    logger.warning("unexpected message '{}' from {}"
                                   .format(response, address))
                    send(MessageType.unexpected_message, connection)
                    connection.close()

            except TimeoutError:
                logger.warning("timeout error - address: {}".format(address))
            except IOError:
                logger.warning("socket broken - address: {}".format(address))

        self._close_connections()

    def send_data_to_compute(self, data_to_send: List,
                             module_name: str, function_name: str) -> List:
        data_to_send = [(i, d) for i, d in enumerate(data_to_send)]
        copy = []
        socket_sent = []
        ret = []

        while data_to_send:
            if not copy:
                logger.debug("copy from data_to_send")
                copy = data_to_send[:]

            with self.lock:
                for conn, val in self.workers.items():
                    (possible, used) = val
                    if not used:
                        logger.debug("send to {}".format(conn.getpeername()))
                        args_to_send = copy[:possible]
                        copy = copy[possible:]
                        self.workers[conn][1] = True
                        socket_sent.append(conn)

                        send(MessageType.compute, conn)
                        send(args_to_send, conn)
                        send((module_name, function_name), conn)

            logger.debug("wait for client messages {}".format(
                list(map(lambda x: x.getpeername(), socket_sent)))
            )
            read, _write, errors = select.select(socket_sent, [],
                                                 socket_sent, SLEEP_TIME)

            with self.lock:
                for readable in itertools.chain(read, errors):
                    logger.debug("received msg from {}"
                                 .format(readable.getpeername()))
                    socket_sent.remove(readable)
                    self.workers[readable][1] = False
                    logger.debug("status restored")

                    try:
                        received_data = receive(readable)
                        # logger.debug("received: {}".format(received_data))
                        returned_i, returned_data = list(zip(*received_data))
                    except (IOError, TimeoutError, ValueError):
                        logger.warning("problem with read socket: {}"
                                       .format(readable))
                        self.workers.pop(readable)
                        readable.close()
                        continue

                    data_to_send = [(i, d) for i, d in data_to_send
                                    if i not in returned_i]
                    ret.extend(returned_data)
                    if self.receive_function:
                        for returned_object in returned_data:
                            self.receive_function(returned_object)

                    logger.info("received computed data num: {}"
                                .format(len(returned_data)))

        return ret

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.end_flag.set()

    def _close_connections(self):
        for connection in self.workers.keys():
            send(MessageType.end, connection)
            connection.close()
