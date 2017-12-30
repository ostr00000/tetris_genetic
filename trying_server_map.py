import typing


def map_it(data: typing.List, arg_num: int):
    return [x ** 2 + arg_num for x in data]

