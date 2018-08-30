# ldlm_lock functions

from __future__ import print_function

from pykdump.API import *
from LinuxDump.BTstack import *
import fregsapi
from ktime import *
from lnet import *
from ptlrpc import *
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

__MDS_INODELOCK_c = '''
#define MDS_INODELOCK_LOOKUP 0x000001
#define MDS_INODELOCK_UPDATE 0x000002
#define MDS_INODELOCK_OPEN   0x000004
#define MDS_INODELOCK_LAYOUT 0x000008
#define MDS_INODELOCK_PERM   0x000010
#define MDS_INODELOCK_XATTR  0x000020
'''
MDS_INODELOCK = CDefine(__MDS_INODELOCK_c)

ldlm_type_c = '''
enum ldlm_type {
	LDLM_PLAIN	= 10,
	LDLM_EXTENT	= 11,
	LDLM_FLOCK	= 12,
	LDLM_IBITS	= 13,
	LDLM_MAX_TYPE
};
'''
ldlm_types = CEnum(ldlm_type_c)

ldlm_mode_c = '''
enum ldlm_mode {
	LCK_MINMODE	= 0,
	LCK_EX		= 1,
	LCK_PW		= 2,
	LCK_PR		= 4,
	LCK_CW		= 8,
	LCK_CR		= 16,
	LCK_NL		= 32,
	LCK_GROUP	= 64,
	LCK_COS		= 128,
	LCK_MAXMODE
};
'''
ldlm_modes = CEnum(ldlm_mode_c)

LCK_COMPAT_EX = ldlm_modes.LCK_NL
LCK_COMPAT_PW = LCK_COMPAT_EX | ldlm_modes.LCK_CR
LCK_COMPAT_PR = LCK_COMPAT_PW | ldlm_modes.LCK_PR
LCK_COMPAT_CW = LCK_COMPAT_PW | ldlm_modes.LCK_CW
LCK_COMPAT_CR = LCK_COMPAT_CW | ldlm_modes.LCK_PR | ldlm_modes.LCK_PW
LCK_COMPAT_NL = LCK_COMPAT_CR | ldlm_modes.LCK_EX | ldlm_modes.LCK_GROUP
LCK_COMPAT_GROUP = ldlm_modes.LCK_GROUP | ldlm_modes.LCK_NL
LCK_COMPAT_COS = ldlm_modes.LCK_COS

lck_compat_array = {
        ldlm_modes.LCK_EX : LCK_COMPAT_EX,
        ldlm_modes.LCK_PW : LCK_COMPAT_PW,
        ldlm_modes.LCK_PR : LCK_COMPAT_PR,
        ldlm_modes.LCK_CW : LCK_COMPAT_CW,
        ldlm_modes.LCK_CR : LCK_COMPAT_CR,
        ldlm_modes.LCK_NL : LCK_COMPAT_NL,
        ldlm_modes.LCK_GROUP : LCK_COMPAT_GROUP,
        ldlm_modes.LCK_COS : LCK_COMPAT_COS
}

def print_connection(conn) :
    print_nid(conn.c_peer.nid)

def ldlm_mode2str(mode) :
        return ldlm_modes.__getitem__(mode)

def res2str(res) :
    return "[0x%x:0x%x:0x%x]" % (res.lr_name.name[0], res.lr_name.name[1],
            res.lr_name.name[2])

def policy_data2str(lr_type, data) :
    if lr_type == ldlm_types.LDLM_IBITS :
        return "%s" % dbits2str(data.l_inodebits.bits, MDS_INODELOCK)
    elif lr_type == ldlm_types.LDLM_EXTENT :
        return "[%d-%d]" % (data.l_extent.start, data.l_extent.end)

    return "%s" % data

def print_ldlm_request(prefix, req) :
    res = req.lock_desc.l_resource
    try:
        print("%s %s %s %s %s" %
                (prefix, ldlm_types.__getitem__(res.lr_type), res2str(res),
                ldlm_mode2str(req.lock_desc.l_req_mode),
                policy_data2str(res.lr_type, req.lock_desc.l_policy_data)))
    except:
        print("err")

def lock_client(lock) :
    if lock.l_export != 0 :
        conn = lock.l_export.exp_imp_reverse.imp_connection
        remote = ("%s@%s" % (conn.c_remote_uuid.uuid, nid2str(conn.c_peer.nid)))
    elif lock.l_conn_export != 0 :
        remote = lock.l_conn_export.exp_obd.obd_name
    else :
        remote = "local lock"
    return remote

def print_ldlm_lock(ldlm_lock, prefix) :
    pid = ""
    remote = lock_client(ldlm_lock)
    if remote == "local lock" :
        pid = ldlm_lock.l_pid

    print("%s 0x%x/0x%x lrc %u/%d,%d %s %s %s" % (prefix,
                            ldlm_lock.l_handle.h_cookie,
                            ldlm_lock.l_remote_handle.cookie,
                            ldlm_lock.l_refc.counter, ldlm_lock.l_readers,
                            ldlm_lock.l_writers, remote,
                            res2str(ldlm_lock.l_resource), pid))
    print(prefix, "flags:", dbits2str(ldlm_lock.l_flags, LDLM_flags))
    if ldlm_lock.l_req_mode == ldlm_lock.l_granted_mode :
        timeout = ""
        if ldlm_lock.l_callback_timeout != 0 :
            jiffies = readSymbol("jiffies")
            timeout = "will timeout in " + j_delay(jiffies,
                ldlm_lock.l_callback_timeout)
        print(prefix, "granted", ldlm_mode2str(ldlm_lock.l_granted_mode),
                timeout)
        if ldlm_lock.l_flags & LDLM_flags.LDLM_FL_WAITED :
            print(prefix, "BL AST sent",
                    get_seconds() - ldlm_lock.l_last_activity, "sec ago")
    else :
        print("%s req_mode: %s enqueued %us ago" % (prefix,
              ldlm_mode2str(ldlm_lock.l_req_mode),
              get_seconds() - ldlm_lock.l_last_activity))
    if ldlm_lock.l_resource.lr_type == ldlm_types.LDLM_EXTENT :
        print("%s [%d-%d] requested [%d-%d]" % (prefix,
            ldlm_lock.l_policy_data.l_extent.start,
            ldlm_lock.l_policy_data.l_extent.end,
            ldlm_lock.l_req_extent.start, ldlm_lock.l_req_extent.end))
    elif ldlm_lock.l_resource.lr_type == ldlm_types.LDLM_IBITS :
        print("%s %s" % (prefix,
            dbits2str(ldlm_lock.l_policy_data.l_inodebits.bits,
                MDS_INODELOCK)))
    else :
        print("%s %s" % (prefix, ldlm_lock.l_policy_data))

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
        try:
            recent = "recent lock " + ldlm_mode2str(res.lr_most_restr)
        except:
            recent = ""
        print("res %x %s %s refc %d %s" %
              (res, ldlm_types.__getitem__(res.lr_type), res2str(res),
                  res.lr_refcount.counter, recent))
        granted = readSUListFromHead(res.lr_granted,
                "l_res_link", "struct ldlm_lock")
        for lock in granted :
            if args.active :
                if lock.l_readers != 0 or lock.l_writers != 0:
                    print_ldlm_lock(lock, "    ")
            else :
                print("    ", lock)
                print_ldlm_lock(lock, "    ")

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

def lock_compatible(lock1, lock2) :
    if lck_compat_array[lock1.l_req_mode] & lock2.l_granted_mode == 0 :
        if lock1.l_resource.lr_type == ldlm_types.LDLM_IBITS :
            bits = lock1.l_policy_data.l_inodebits.bits
            if bits & lock2.l_policy_data.l_inodebits.bits != 0 :
                return False
            else :
                print("TODO: conflict found")
                return False
    return True

def find_conflicting_lock(lock) :
    granted = readSUListFromHead(lock.l_resource.lr_granted,
                "l_res_link", "struct ldlm_lock")
    for gr in granted :
        if lock_compatible(lock, gr) == False :
            return gr

    waiting = readSUListFromHead(lock.l_resource.lr_waiting,
                "l_res_link", "struct ldlm_lock")
    for w in waiting :
        if lock_compatible(lock, w) == False :
            return w
    return None

def show_tgt(pid) :
    print(pid)
    addr = search_for_reg("RDI", pid, "tgt_request_handle")
    if addr != 0:
        req = readSU("struct ptlrpc_request", addr)
        show_ptlrpc_request(req)
    addr = search_for_reg("RBX", pid, "schedule_timeout")
    if addr == 0 :
        addr = search_for_reg("RBX", pid, "__schedule")
    if addr == 0 :
        addr = search_for_reg("RBX", pid, "schedule")
    lock = readSU("struct ldlm_lock", addr)
    print(lock)
    print_ldlm_lock(lock, "")
    return lock

def show_completition_waiting_locks() :
    res = dict()
    (funcpids, functasks, alltaskaddrs) = get_threads_subroutines_slow()
    waiting_pids = funcsMatch(funcpids, "ldlm_completion_ast")
    for pid in waiting_pids :
        lock = show_tgt(pid)
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

def show_BL_AST_locks() :
    ptlrpc_all_services = readSymbol("ptlrpc_all_services")
    services = readSUListFromHead(ptlrpc_all_services,
                "srv_list", "struct ptlrpc_service")
    waiting_locks_list = readSymbol("waiting_locks_list")
    waiting = readSUListFromHead(waiting_locks_list,
                "l_pending_chain", "struct ldlm_lock")
    for lock in waiting :
        print(lock)
        print_ldlm_lock(lock, "    ")
        remote = lock_client(lock)
        pattern = re.compile(remote)
        show_processing(pattern)
        for srv in services :
            show_waiting(srv, pattern)

if ( __name__ == '__main__'):
    import argparse

    parser =  argparse.ArgumentParser()
    parser.add_argument("-l","--lock", dest="lock", default = 0)
    parser.add_argument("-n","--ns", dest="ns", default = 0)
    parser.add_argument("-g","--grep", dest="g", default = 0)
    parser.add_argument("-w","--compwait", dest="compl_waiting",
                        action='store_true')
    parser.add_argument("-b","--blocking", dest="blocking",
                        action='store_true')
    parser.add_argument("-a","--active", dest="active",
                        action='store_true')
    parser.add_argument("-p","--pid", dest="pid", default = 0)
    parser.add_argument("-f","--flags", dest="flags", default = 0)
    args = parser.parse_args()

    if args.lock != 0 :
        l = readSU("struct ldlm_lock", int(args.lock, 16))
        print_ldlm_lock(l, "")
    elif args.ns != 0 :
        ns = readSU("struct ldlm_namespace", int(args.ns, 16))
        show_ns_locks(ns)
    elif args.compl_waiting != 0 :
        show_completition_waiting_locks()
    elif args.blocking != 0 :
        show_BL_AST_locks()
    elif args.pid != 0 :
        show_tgt(int(args.pid))
    elif args.g != 0 :
        show_namespaces(args.g)
    elif args.flags != 0 :
        print("flags:", dbits2str(int(args.flags, 0), LDLM_flags))
    else :
        show_namespaces(r'.*')

