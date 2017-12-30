import server
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def main():
    server.REQUIRED = ["trying_server_map.py"]
    s = server.Server("localhost", 50559)
    s.start_server()

    data = list(range(100))

    ret = s.send_data_to_compute(data, server.REQUIRED[0][:-3], "map_it")
    print(ret)

    s.stop_server()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    main()
