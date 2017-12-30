from connection import *
from typing import List
import multiprocessing
import threading
import os
import select
import logging

REQUIRED = ["board.py"]
SLEEP_TIME = 3

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
required_modules = list(
    map(lambda name: (name, os.stat(name).st_size), REQUIRED)
)


class Server:
    def __init__(self, host, port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((host, port))
        self.sock.listen()

        self.lock = threading.Lock()
        self.workers: List = []
        self.loop_thread = multiprocessing.Process(target=self._server_loop)

    @staticmethod
    def _send_files(names_of_files: List[str], client):
        send(len(names_of_files), client)
        for filename in names_of_files:
            with open(filename, 'r') as file:
                data = file.read()
                send(filename, client)
                send(data, client)

    def start_server(self):
        self.loop_thread.start()

    def stop_server(self):
        self.loop_thread.terminate()

    def _server_loop(self):
        while True:
            connection, address = self.sock.accept()
            logger.debug("accepted connection from :{}".format(address))

            try:
                def d():
                    required_modules = list(
                        map(lambda name: (name, os.stat(name).st_size),
                            REQUIRED)
                    )
                    send(required_modules, connection)
                    logger.debug("sent required modules: {}".format(REQUIRED))
                d()
                response = receive(connection)
                logger.debug("checking response '{}'".format(response))
                if response == MessageType.download:
                    logger.debug("sending files")
                    d = lambda: self._send_files(REQUIRED, connection)
                    d()
                    logger.debug("modules sent")
                    response = receive(connection)
                    logger.debug("received response {}".format(response))

                if response == MessageType.get_work:
                    logger.debug("client ready")
                    quantity = receive(connection)
                    with self.lock:
                        self.workers.append([connection, quantity, False])
                    logger.debug("worker added, workers:{}"
                                 .format(self.workers))
                else:
                    logger.warning("unexpected message '{}' from {}"
                                   .format(response, address))
                    send(MessageType.unexpected_message, connection)
                    connection.close()

            except IOError:
                logger.warning("connection lost - address: {}".format(address))

    def send_data_to_compute(self, data_to_send: List,
                             module_name: str, function_name: str) -> List:
        """objects in data_to_lend must have attribute id"""
        copy = []
        socket_sent = []
        ret = []
        num = 0

        while data_to_send:
            if not copy:
                logger.debug("copy from data_to_send")
                copy = data_to_send[:]

            with self.lock:
                logger.debug("locking")
                logger.debug("workers: {}".format(self.workers))
                for i, (conn, possible, used) in enumerate(self.workers):
                    if not used:
                        logger.debug("send to {}".format(str(conn)))
                        args_to_send = copy[:possible]
                        copy = copy[possible:]
                        self.workers[i][2] = True
                        socket_sent.append(conn)

                        send(MessageType.compute, conn)
                        send(args_to_send, conn)
                        send((module_name, function_name), conn)
                logger.debug("unlocking")

            logger.debug("checking sent messages")
            read, _write, errors = select.select(socket_sent, [],
                                                 socket_sent, SLEEP_TIME)

            with self.lock:
                logger.debug("locking")

                for error in errors:
                    logger.debug("there was a problem {}".format(str(error)))
                    socket_sent.remove(error)
                    for worker in self.workers:
                        if worker[0] == error:
                            worker[2] = False
                            break

                for readable in read:
                    logger.debug("received msg from {}".format(str(readable)))
                    socket_sent.remove(readable)
                    for worker in self.workers:
                        if worker[0] == readable:
                            worker[2] = False
                            break
                    try:
                        returned_data = receive(readable)
                    except IOError:
                        logger.warning(
                            "problem with read socket: {}".format(readable)
                        )
                        continue

                    data_to_send = [d for d in data_to_send
                                    if d.id != returned_data.id]
                    ret.append(returned_data)

                    logger.debug("received computed data num: {}".format(num))
                    num += 1

                logger.debug("unlocking")

        return ret
