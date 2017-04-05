# get time functions

from pykdump.API import *

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

