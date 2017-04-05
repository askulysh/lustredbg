# ptlrpc functions

from __future__ import print_function

from pykdump.API import *
from ktime import *

max_req = 10

def print_req_flags(req) :
    s  = ""
    if req.rq_intr :
        s = s + "|Intrrupted"
    if req.rq_replied :
        s = s + "|Replied"
    if req.rq_err :
        s = s + "|Error"
    if req.rq_net_err :
        s = s + "|NetError"
    if req.rq_timedout :
        s = s + "|Timedout"
    if req.rq_resend :
        s = s + "|Resend"
    if req.rq_restart :
        s = s + "|Restart"
    if req.rq_replay :
        s = s + "|Replay"
    if req.rq_waiting :
        s = s + "|Waiting"
    return s

def phase2str(phase) :
    return {
        -339681792 : 'NEW',
        -339681791 : 'RPC',
        -339681790 : 'BULK',
        -339681789 : 'INTERPRET',
        -339681788 : 'COMPLETE',
        -339681787 : 'UNREG_RPC',
        -339681786 : 'UNREG_BULK',
        -339681785 : 'UNDEFINED',
    } [phase]

def req_sent(req) :
    if req.rq_sent != 0 :
        return ("sent %4ds ago dl in %5ds" %
            (get_seconds() - req.rq_sent, req.rq_deadline - get_seconds()))
    else :
        return "Waiting...                  "

def show_ptlrpc_set(s) :
    print("set %x new %d remaining %d" % (s,
        s.set_new_count.counter, s.set_remaining.counter))
#    requests = readSUListFromHead(s.set_requests,
#            "rq_cli.cr_set_chain", "struct ptlrpc_request")
#    print(requests)

    i = 0
    head = s.set_requests

    while head.next != s.set_requests :
        head = head.next
        a = int(head) - 224 # rq_cli.cr_set_chain
        req = readSU("struct ptlrpc_request", a)
        print("%x x%d %s %s %4d %s %s" %
            (req, req.rq_xid,
            req.rq_import.imp_obd.obd_name,req_sent(req), req.rq_status,
            phase2str(req.rq_phase), print_req_flags(req)))
        i = i + 1
        if i == max_req :
            break

def show_ptlrpcd_ctl(ctl) :
    pc_set = ctl.pc_set
    show_ptlrpc_set(ctl.pc_set)

def show_ptlrpcds() :
    try:
        ptlrpcds_num = readSymbol("ptlrpcds_num")
    except TypeError:
        ptlrpcds_num = 1
    ptlrpcds = readSymbol("ptlrpcds")
    for i in xrange(0, ptlrpcds_num) :
        print("cpt %d" % i)
        ptlrpcd = ptlrpcds[i]
        for t in xrange(0, ptlrpcd.pd_nthreads) :
            show_ptlrpcd_ctl(ptlrpcd.pd_threads[t])

    print("recovery:");
    try:
        ptlrpcd_rcv = readSymbol("ptlrpcd_rcv")
    except TypeError:
        ptlrpcd_rcv = ptlrpcds[0].pd_thread_rcv
    show_ptlrpcd_ctl(ptlrpcd_rcv)

if ( __name__ == '__main__'):
    import argparse

    parser =  argparse.ArgumentParser()
    parser.add_argument("-r","--request", dest="req", default = 0)
    parser.add_argument("-s","--set", dest="set", default = 0)
    parser.add_argument("-n","--num", dest="n", default = 0)
    args = parser.parse_args()
    if args.n != 0 :
        max_req = n
    if args.req != 0 :
        show_ptlrpc_request(args.req)
    elif args.set != 0 :
        s = readSU("struct ptlrpc_request_set", int(args.set, 0))
        show_ptlrpc_set(s)
    else :
        show_ptlrpcds()