# get time functions

from pykdump.API import *

def ktime_get_seconds() :
    return ktime_get() / 1000000000

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
        if (symbol_exists("timekeeper")) :
            tk = readSymbol("timekeeper")
        else :
            tk_core = readSymbol("tk_core")
            tk = tk_core.timekeeper
        def get_seconds():
            try:
                return tk.xtime_sec
            except KeyError:
                return tk.xtime.tv_sec
        def ktime_get():
                return ((tk.xtime_sec +
                        tk.wall_to_monotonic.tv_sec)*1000000000 +
                        tk.wall_to_monotonic.tv_nsec);

def j_delay(ts, jiffies,maxhours = 20):
    v = (jiffies - ts) & INT_MASK
    if (v > INT_MAX):
        print(v)
        v = "     n/a"
    elif (v > HZ*3600*maxhours):
        v = ">20hours"
    else:
        v = "%8.2f s" % (float(v)/HZ)
    return v

