# osd functions

from __future__ import print_function

from pykdump.API import *
from LinuxDump.BTstack import *
import LinuxDump.fregsapi
from ktime import *
import ptlrpc as ptlrpc
import obd as obd
import mdt as mdt

def osd_oti_get(env) :
    osd_key = readSymbol("osd_key")

    return readSU("struct osd_thread_info",
            env.le_ctx.lc_value[osd_key.lct_index])

def print_osd_object(osd_obj, prefix) :
    try :
        if osd_obj.oo_inode != 0 :
            inode = readSU("struct inode", osd_obj.oo_inode)
            print(prefix, inode, "ino", osd_obj.oo_inode.i_ino,
                  "nlink", osd_obj.oo_inode.i_nlink,
                  "size", osd_obj.oo_inode.i_size)
    except :
        try :
            print(prefix, "dnode", osd_obj.oo_dn)
        except :
            pass

def show_ofd(ofd, prefix) :
    loh = ofd.ofo_header
    obd.print_loh(loh, prefix)
    print(prefix, "%s parent %s" % (ofd, obd.fid2str(ofd.ofo_ff.ff_parent)))
    for layer in readSUListFromHead(loh.loh_layers, "lo_linkage",
                                    "struct lu_object") :
          mdt.print_generic_mdt_obj(layer, prefix + "    ")

def search_for_reg(r, pid, func) :
    with DisasmFlavor('att'):
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

def show_bio(bio) :
    try :
        disk = bio.bi_disk
    except :
        disk = bio.bi_bdev.bd_disk
    queue = disk.queue
    mddev = readSU("struct mddev", queue.queuedata)
    print(bio, disk, mddev)
    print(disk.disk_name)

def buffer_head2bio(bh):
    from LinuxDump.Slab import get_slab_addrs
    try:
        (alloc, free) = get_slab_addrs("kmalloc-256")
    except crash.error as val:
        print (val)
        return
    for o in alloc:
        bio = readSU("struct bio", o)
        if bio.bi_private == bh :
            return bio
    return None

def search_for_bio(stack) :
    addr = ptlrpc.search_stack_for_reg("RDI", stack, "generic_make_request")
    if addr == 0:
        return
    print()
    bio = readSU("struct bio", addr)
    print(bio)
    show_bio(bio)

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
    parser.add_argument("-b","--bio", dest="bio", default = 0)
    parser.add_argument("-B","--buffer_head", dest="buffer_head", default = 0)
    parser.add_argument("-f","--ofd", dest="ofd", default = 0)
    args = parser.parse_args()
    if args.iowait != 0 :
        show_io()
    elif args.env != 0 and args.key != "":
        env = readSU("struct lu_env", int(args.env, 16))
        key = readSymbol(args.key)
        print(key)
        if key.lct_tags == 16 or key.lct_tags == 256 :
            val = env.le_ses.lc_value[key.lct_index]
        else :
            val = env.le_ctx.lc_value[key.lct_index]
        print("%x" % val)
    elif args.bio != 0:
        bio = readSU("struct bio", int(args.bio, 16))
        show_bio(bio)
    elif args.buffer_head != 0 :
        bh = readSU("struct buffer_head", int(args.buffer_head, 16))
        bio = buffer_head2bio(bh)
        print(bio)
        show_bio(bio)

    elif args.ofd !=0 :
        ofd = readSU("struct ofd_object", int(args.ofd, 16))
        show_ofd(ofd, "")

