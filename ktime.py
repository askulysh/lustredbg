# get time functions

from pykdump.API import *

__all__ = ['get_seconds']

if (symbol_exists("xtime")):
    xtime = readSymbol("xtime")
    def get_seconds():
        return xtime.tv_sec
else :
    if (symbol_exists("wall_to_monotonic")):
        tk = readSymbol()
        def get_seconds():
            return tk.xtime.tv_sec
    else:
        tk = readSymbol("timekeeper")
        def get_seconds():
            try:
                return tk.xtime_sec
            except KeyError:
                return tk.xtime.tv_sec

