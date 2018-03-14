# osd functions

from __future__ import print_function

from pykdump.API import *
from LinuxDump.BTstack import *
import fregsapi
from ktime import *

def osd_oti_get(env) :
    osd_key = readSymbol("osd_key")

    return readSU("struct osd_thread_info",
            env.le_ctx.lc_value[osd_key.lct_index])

def search_for_reg(r, pid, func) :
    #     with DisasmFlavor('att'):
    try:
        stacklist = exec_bt("bt %d" % pid, MEMOIZE=False)
    except:
        print("Unable to get stack trace")
        return 0
    for s in stacklist:
        fregsapi.search_for_registers(s)
        for f in s.frames:
            if f.func == func :
                return f.reg[r][0]
    return 0

def show_io() :
    res = dict()
    count = 0
    min_start = 100000000000
    sum_wait = 0
    jiffies = readSymbol("jiffies")

    (funcpids, functasks, alltaskaddrs) = get_threads_subroutines_slow()
    waiting_pids = funcsMatch(funcpids, "osd_read_prep")
    for pid in waiting_pids :
        print(pid)
        addr = search_for_reg("RDI", pid, "osd_read_prep")
        lu_env = readSU("struct lu_env", addr)
        oti = osd_oti_get(lu_env)
        iobuf = oti.oti_iobuf
        print(iobuf)
        if iobuf.dr_numreqs.counter != 0 :
            print("PID %d is waiting for %ss" %
                    (pid, j_delay(iobuf.dr_start_time, jiffies)))
            sum_wait = sum_wait + iobuf.dr_start_time
            count = count + 1
            if iobuf.dr_start_time < min_start :
                min_start = iobuf.dr_start_time
    print("--------------")
    print("%d threads are waiting for I/O max: %s avg: %s" %
            (count, j_delay(min_start, jiffies), j_delay(sum_wait, jiffies)))

if ( __name__ == '__main__'):
    import argparse

    parser =  argparse.ArgumentParser()
    parser.add_argument("-w","--iowait", dest="iowait",
                        action='store_true')
    parser.add_argument("-e","--env", dest="env", default = 0)
    parser.add_argument("-k","--key", dest="key", default = "")
    args = parser.parse_args()
    if args.iowait != 0 :
        show_io()
    elif args.env != 0 and args.key != "":
        env = readSU("struct lu_env", int(args.env, 16))
        key = readSymbol(args.key)
        print(key)
        if key.lct_tags == 256 :
            val = env.le_ses.lc_value[key.lct_index]
        else :
            val = env.le_ctx.lc_value[key.lct_index]
        print("%x" % val)

