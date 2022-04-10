class WaitRequest(Exception):
    pass


class SegmentError(Exception):
    pass


class ArgumentError(Exception):
    USAGE_MSG = "Run the app with '--help' argument to see the usage"
