# ldlm_lock functions

from __future__ import print_function

from pykdump.API import *
from LinuxDump.BTstack import *
import fregsapi
from ktime import *
from lnet import *
import re

__LDLM_flags_c = '''
#define LDLM_FL_LOCK_CHANGED            0x0000000000000001
#define LDLM_FL_BLOCK_GRANTED           0x0000000000000002
#define LDLM_FL_BLOCK_CONV              0x0000000000000004
#define LDLM_FL_BLOCK_WAIT              0x0000000000000008
#define LDLM_FL_AST_SENT                0x0000000000000020
#define LDLM_FL_REPLAY                  0x0000000000000100
#define LDLM_FL_INTENT_ONLY             0x0000000000000200
#define LDLM_FL_HAS_INTENT              0x0000000000001000
#define LDLM_FL_FLOCK_DEADLOCK          0x0000000000008000
#define LDLM_FL_DISCARD_DATA            0x0000000000010000
#define LDLM_FL_NO_TIMEOUT              0x0000000000020000
#define LDLM_FL_BLOCK_NOWAIT            0x0000000000040000
#define LDLM_FL_TEST_LOCK               0x0000000000080000
#define LDLM_FL_CANCEL_ON_BLOCK         0x0000000000800000
#define LDLM_FL_NO_EXPANSION		0x0000000020000000
#define LDLM_FL_DENY_ON_CONTENTION      0x0000000040000000
#define LDLM_FL_AST_DISCARD_DATA        0x0000000080000000
#define LDLM_FL_FAIL_LOC                0x0000000100000000
#define LDLM_FL_SKIPPED                 0x0000000200000000
#define LDLM_FL_CBPENDING               0x0000000400000000
#define LDLM_FL_WAIT_NOREPROC           0x0000000800000000
#define LDLM_FL_CANCEL                  0x0000001000000000
#define LDLM_FL_LOCAL_ONLY              0x0000002000000000
#define LDLM_FL_FAILED                  0x0000004000000000
#define LDLM_FL_CANCELING               0x0000008000000000
#define LDLM_FL_LOCAL                   0x0000010000000000
#define LDLM_FL_LVB_READY               0x0000020000000000
#define LDLM_FL_KMS_IGNORE              0x0000040000000000
#define LDLM_FL_CP_REQD                 0x0000080000000000
#define LDLM_FL_CLEANED                 0x0000100000000000
#define LDLM_FL_ATOMIC_CB               0x0000200000000000
#define LDLM_FL_BL_AST                  0x0000400000000000
#define LDLM_FL_BL_DONE                 0x0000800000000000
#define LDLM_FL_NO_LRU                  0x0001000000000000
#define LDLM_FL_FAIL_NOTIFIED           0x0002000000000000
#define LDLM_FL_DESTROYED               0x0004000000000000
#define LDLM_FL_SERVER_LOCK             0x0008000000000000
#define LDLM_FL_RES_LOCKED              0x0010000000000000
#define LDLM_FL_WAITED                  0x0020000000000000
#define LDLM_FL_NS_SRV                  0x0040000000000000
#define LDLM_FL_EXCL                    0x0080000000000000
#define LDLM_FL_RESENT                  0x0100000000000000
'''

LDLM_flags = CDefine(__LDLM_flags_c)

def print_connection(conn) :
    print_nid(conn.c_peer.nid)

def print_ldlm_lock(ldlm_lock, prefix) :
    if ldlm_lock.l_export != 0 :
        conn = ldlm_lock.l_export.exp_imp_reverse.imp_connection
        remote = ("%s@%s" % (conn.c_remote_uuid.uuid, nid2str(conn.c_peer.nid)))
    elif ldlm_lock.l_conn_export != 0 :
        remote = ldlm_lock.l_conn_export.exp_obd.obd_name
    else :
        remote = "local lock"

    print("%s 0x%x/0x%x refc %u %s %s" % (prefix, ldlm_lock.l_handle.h_cookie,
                            ldlm_lock.l_remote_handle.cookie,
                            ldlm_lock.l_refc.counter, remote,
                            ldlm_lock.l_resource.lr_name.name))
    print(prefix, "flags:", dbits2str(ldlm_lock.l_flags, LDLM_flags))
    if ldlm_lock.l_req_mode == ldlm_lock.l_granted_mode :
        timeout = ""
        if ldlm_lock.l_callback_timeout != 0 :
            jiffies = readSymbol("jiffies")
            timeout = "will timeout in " + j_delay(jiffies,
                ldlm_lock.l_callback_timeout)
        print(prefix, "granted", timeout)
    else :
        print("%s enqueued %us ago" % (prefix,
                get_seconds() - ldlm_lock.l_last_activity))

def hash_for_each(hs, func) :
    buckets = hs.hs_buckets
    bucket_num = 1 << (hs.hs_cur_bits - hs.hs_bkt_bits)
    for ix in range(0, bucket_num) :
        bd = buckets[ix]
        if bd != 0 :
            a = int(bd.hsb_head)
            for offset in range(0, 1 << hs.hs_bkt_bits) :
                hlist = readSU("struct hlist_head", a + 8*2*offset)
                if hlist != 0 :
                    func(hlist)

def walk_res_hash2(hlist) :
    head = hlist.first

    while head != 0 :
        a = int(head) - 8 # lr_hash
        res = readSU("struct ldlm_resource", a)
        print("res %x %s refc %d %d" % (res, res.lr_name.name,
            res.lr_refcount.counter, res.lr_most_restr))
        head = head.next

def show_ns_locks(ns) :
    print("ns %x %s total granted %d" % (ns, ns.ns_obd.obd_name,
        ns.ns_pool.pl_granted.counter))
    hs = ns.ns_rs_hash
    hash_for_each(ns.ns_rs_hash, walk_res_hash2)

def ns_list(l, regexp) :
    nss = readSUListFromHead(l, "ns_list_chain", "struct ldlm_namespace")
    for ns in nss :
        print(ns)
        if re.match(regexp, ns.ns_obd.obd_name, re.I) :
            show_ns_locks(ns)

def show_namespaces(regexp) :
    print("Looking for CLI active name spaces")
    l = readSymbol("ldlm_cli_active_namespace_list")
    ns_list(l, regexp)

#    print("Looking for CLI inactive name spaces:")
#    l = readSymbol("ldlm_cli_inactive_namespace_list")
#    ns_list(l, regexp)

#    printf "Looking for SRV name spaces:\n"
#    srv_namespaces $arg0

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

def find_conflicting_lock(lock) :
    granted = readSUListFromHead(lock.l_resource.lr_granted,
                "l_res_link", "struct ldlm_lock")
    if len(granted) == 1 :
        return granted[0]
    else :
        print("TODO: granted > 1")
        if lock.l_resource.lr_type == 13 :
            bits = lock.l_policy_data.l_inodebits.bits
            for gr in granted :
                if bits & gr.l_policy_data.l_inodebits.bits != 0 :
                   return gr

        return nil

def show_completition_waiting_locks() :
    res = dict()
    (funcpids, functasks, alltaskaddrs) = get_threads_subroutines_slow()
    waiting_pids = funcsMatch(funcpids, "ldlm_completion_ast")
    for pid in waiting_pids :
        print(pid)
        addr = search_for_reg("RBX", pid, "schedule_timeout")
        if addr == 0 :
            addr = search_for_reg("RBX", pid, "schedule")
        lock = readSU("struct ldlm_lock", addr)
        print(lock)
        print_ldlm_lock(lock, "")
        conflict = find_conflicting_lock(lock)
        try :
            count = res[conflict][0]
            max_wait = res[conflict][1]
        except :
            count = 0
            max_wait = 0
        count = count + 1
        cur_wait = get_seconds() - lock.l_last_activity
        if max_wait < cur_wait :
            max_wait = cur_wait
        res[conflict] = [count, max_wait]
    print("--------------")
    for l in res :
        print("%d threads are waiting (max %ss) for" % (res[l][0], res[l][1]))
        print(l)
        print_ldlm_lock(l, "")

if ( __name__ == '__main__'):
    import argparse

    parser =  argparse.ArgumentParser()
    parser.add_argument("-l","--lock", dest="lock", default = 0)
    parser.add_argument("-n","--ns", dest="ns", default = 0)
    parser.add_argument("-g","--grep", dest="g", default = 0)
    parser.add_argument("-w","--compwait", dest="compl_waiting",
                        action='store_true')
    args = parser.parse_args()
    if args.lock != 0 :
        l = readSU("struct ldlm_lock", int(args.lock, 0))
        print_ldlm_lock(l, "")
    elif args.ns != 0 :
        ns = readSU("struct ldlm_namespace", int(args.ns, 0))
        show_ns_locks(ns)
    elif args.compl_waiting != 0 :
        show_completition_waiting_locks()
    elif args.g != 0 :
        show_namespaces(args.g)
    else :
        show_namespaces(r'.*')

