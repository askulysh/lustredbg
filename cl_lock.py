# cl_lock functions

from __future__ import print_function

from pykdump.API import *
from LinuxDump.BTstack import *

import fregsapi
import ldlm_lock as ldlm

vvp_lock_ops = readSymbol("vvp_lock_ops")
lov_lock_ops = readSymbol("lov_lock_ops")
lovsub_lock_ops = readSymbol("lovsub_lock_ops")
osc_lock_ops = readSymbol("osc_lock_ops")

def print_osc_lock(osc_lock, prefix) :
    print(prefix, "state: ", osc_lock.ols_state, "holds: ", osc_lock.ols_hold,
            "\n", prefix, "flags:", dbits2str(osc_lock.ols_flags, ldlm.LDLM_flags))
    try:
        ldlm_lock = osc_lock.ols_dlmlock
    except KeyError:
        ldlm_lock = osc_lock.ols_lock
    print(prefix, ldlm_lock)
    if ldlm_lock != 0 :
        ldlm.print_ldlm_lock(ldlm_lock, prefix + "\t")

def print_lov_lock_sub(lov_lock_sub, prefix) :
    print(prefix, lov_lock_sub)
    lovsub_lock = readSU("struct lovsub_lock", lov_lock_sub.sub_lock)
    print(prefix, lovsub_lock.lss_cl)
    print_cl_lock(lovsub_lock.lss_cl.cls_lock, prefix + "\t")

def print_lov_lock(lov_lock, prefix):
    for i in range(0, lov_lock.lls_nr) :
        print_lov_lock_sub(lov_lock.lls_sub[i], prefix)

def print_cl_lock(cl, prefix):
    print(prefix, cl)
    for layer in readSUListFromHead(cl.cll_layers, "cls_linkage",
            "struct cl_lock_slice") :
        if layer.cls_ops == vvp_lock_ops :
            print(prefix, "vvp", layer)
        if layer.cls_ops == lovsub_lock_ops :
            print(prefix, "lovsub", layer)
        if layer.cls_ops == osc_lock_ops :
            osc_lock = readSU("struct osc_lock", layer)
            print(prefix, "osc", osc_lock)
            print_osc_lock(osc_lock, prefix + "\t")
        if layer.cls_ops == lov_lock_ops :
            lov_lock = readSU("struct lov_lock", layer)
            print(prefix, "lov", lov_lock)
            print_lov_lock(lov_lock, prefix + "\t")

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

def print_waiting_cl_locks() :
    (funcpids, functasks, alltaskaddrs) = get_threads_subroutines_slow()
    waiting_pids = funcsMatch(funcpids, "cl_lock_state_wait")
    for pid in waiting_pids :
        print(pid)
        addr = search_for_reg("RSI", pid, "cl_lock_state_wait")
        cl_lock = readSU("struct cl_lock", addr)
        print_cl_lock(cl_lock, "")

if ( __name__ == '__main__'):
    import argparse

    parser =  argparse.ArgumentParser()
    parser.add_argument("-l","--lock", dest="cl", default = 0)
    parser.add_argument("-o","--lov", dest="lov", default = 0)
    parser.add_argument("-s","--osc", dest="osc", default = 0)
    args = parser.parse_args()
    if args.cl != 0 :
        cl_lock = readSU("struct cl_lock", int(args.cl, 0))
        print_cl_lock(cl_lock, "")
    elif args.lov != 0 :
        lov_lock = readSU("struct lov_lock", int(args.lov, 0))
        print_lov_lock(lov_lock, "")
    elif args.osc != 0 :
        osc_lock = readSU("struct osc_lock", int(args.osc, 0))
        print_osc_lock(osc_lock, "")
    else :
        print_waiting_cl_locks()

