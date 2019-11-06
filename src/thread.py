import _thread

class Thread:
    def __init__(self, f, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self._f = self._decorator(f)
        self._ret = []
        self._finished = False
        self._started = False

    def start(self):
        self._f()
        self._started = True

    def result(self):
        if self._finished and len(self._ret) > 0:
            return self._ret.pop()

        return None

    def is_finished(self):
        return self._finished

    def is_started(self):
        return self._started

    def _decorator(self, f):

        def wrapped_f(*args, **kwargs):
            res = f(*args, **kwargs)
            self._ret.append(res)
            self._finished = True

        def wrapper():
            _thread.start_new_thread(wrapped_f, self.args, self.kwargs)

        return wrapper