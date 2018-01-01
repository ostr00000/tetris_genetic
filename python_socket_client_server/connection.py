import socket
import struct
import logging
import pickle

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class MessageType:
    download = 'download'
    get_work = 'work'
    unexpected_message = "server received unexpected message"
    end = 'end'
    compute = 'compute'


def send(msg, sock: socket.SocketType):
    msg = pickle.dumps(msg)
    val = struct.pack('!i', len(msg))
    try:
        sock.sendall(val)
        sock.sendall(msg)
    except BrokenPipeError:
        return


def receive(sock: socket.SocketType):
    buf = b''
    while len(buf) < 4:
        chunk = sock.recv(4)
        if not chunk:
            raise IOError("socket connection broken")
        buf += chunk
    length = struct.unpack('!i', buf[:4])[0]
    bytes_recd = len(buf) - 4

    while bytes_recd < length:
        chunk = sock.recv(min(length - bytes_recd, 2048))
        if not chunk:
            raise IOError("socket connection broken")
        buf += chunk
        bytes_recd = bytes_recd + len(chunk)

    return pickle.loads(buf[4:])
