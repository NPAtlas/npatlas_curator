from enum import Enum


class ResolveEnum(Enum):
    """
    This class is an enumerator dictating how a checker compound
    should be handled during insertion, either from a checker problem
    or to facilitate updating a compounds information
    """

    NEW = 1
    REPLACE = 2
    KEEP = 3
    UPDATE = 4
    REJECT = 5
    SYNONYM = 6
