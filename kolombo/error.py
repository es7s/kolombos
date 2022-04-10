
class BufferWait(Exception):
    def __init__(self):
        super().__init__('Not enough data to detach')


class SegmentError(Exception): pass


class ArgumentError(Exception):
    USAGE_MSG = "Run the app with '--help' argument to see the usage"
