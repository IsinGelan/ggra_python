
from random import randint
from time import perf_counter
from typing import Any, Callable, Iterable, Iterator

#=================================
# Decorators
def call_info(fun):
    """Information about what args and kwargs the function was called with"""
    def wrapper(*args, **kwargs):
        print(f">> Calling function {fun.__name__!r} with args {args} and kwargs {kwargs}")
        return fun(*args, **kwargs)
    return wrapper

def time_info(process_description: str):
    """Gives information about how long a function took to execute.\n
    process_description will be printed in the respective message.\n
    Can be something like 'Calculating prime factors'\n
    produces message like '>> Calculating prime factors took 0.0021s in function <function_name>'"""
    def decorator(fun):
        def wrapper(*args, **kwargs):
            s = perf_counter()
            res = fun(*args, **kwargs)
            e = perf_counter()
            print(f">> {process_description:<15} took {e-s:.4f}s in function {fun.__name__!r}")
            return res
        return wrapper
    return decorator

#=================================
# Useful functions
def alltrue(*args) -> bool:
    return all(args)

def anytrue(*args) -> bool:
    return any(args)

def index_where(iterator: list, predicate: Callable[[Any], bool]) -> int | None:
    """Returns the first index, where predicate is true. If no such element exists, None is returned"""
    for i, elem in enumerate(iterator):
        if predicate(elem):
            return i
    return None

def first_where(iterator: Iterator, predicate: Callable[[Any], bool], default = None):
    for obj in iterator:
        if predicate(obj):
            return obj
    return default

def separate(iterable: Iterable, predicate: Callable[[Any], bool]) -> tuple[list, list]:
    """Like filter, but returns list where predicate is True and one where it is False"""
    a, b = [], []
    for obj in iterable:
        if predicate(obj):
            a.append(obj)
            continue
        b.append(obj)
    return a, b

#=================================
#Fixes
def shuffle(obj: Iterable) -> Iterator:
    """Man könnte auch py.random shuffle benutzen, aber dies liefert keinen Iterator"""
    objlen  = len(obj)
    remlen  = objlen
    remaining = list(range(objlen))
    for _ in range(objlen):
        ii  = randint(0, remlen-1)
        i   = remaining.pop(ii)
        remlen -= 1
        yield obj[i]

#=================================
#Für Schönheit
def ind(size: int): return " "*size

def expanded_obj_repr_lines(obj_repr: str, indent: int = 2) -> Iterator[str]:
    """Iterator of all lines that make up the expanded version of the representation string.
    Works with repr strings as produced by dataclasses or native Python objects."""
    current_indent = 0
    consumed_until = -1
    yield_later = False # so [] for example is not displayed as multiple lines
    in_string   = None  # so string "random(stuff)" does not get split at the backets
    for i, char in enumerate(obj_repr):
        if char == "\"" and in_string is None:
            in_string = "\""
            continue
        if char == "'" and in_string is None:
            in_string = "'"
            continue
        if char == in_string:
            in_string = None
            continue
        if in_string:
            continue

        if char in "([{" and obj_repr[i+1] in ")]}":
            yield_later = True
            continue
        if char in "([{":
            yield ind(current_indent) + obj_repr[consumed_until+1:i+1]
            consumed_until = i
            current_indent += indent
            continue
        if char in ")]}" and yield_later:
            yield_later = False
            continue
        if char in ")]}":
            yield ind(current_indent) + obj_repr[consumed_until+1:i]
            consumed_until = i - 1
            current_indent -= indent
            continue

        if char == ",":
            yield ind(current_indent) + obj_repr[consumed_until+1:i+1]
            consumed_until = i + 1
            continue
    yield obj_repr[consumed_until+1:]
