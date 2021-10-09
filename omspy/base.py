from typing import Callable


def pre(func: Callable) -> Callable:
    """
    Decorator to run before a function call
    """
    name = func.__name__

    def f(*args, **kwargs):
        self = args[0]
        override = self.get_override(name)
        if override:
            kwargs = self.rename(kwargs, override)
        return func(*args, **kwargs)

    return f


def post(func: Callable) -> Callable:
    """
    Decorator to run after a function call
    """
    name = func.__name__

    def f(*args, **kwargs):
        self = args[0]
        override = self.get_override(name)
        response = func(*args, **kwargs)
        if override:
            if isinstance(response, list):
                return [self.rename(r, override) for r in response]
            elif isinstance(response, dict):
                return self.rename(response, override)
        return response

    return f
