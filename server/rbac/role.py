from enum import Flag, auto


class Role(Flag):
    READ = auto()
    WRITE = auto()
    EXECUTE = auto()
