# ldlm_lock functions

from __future__ import print_function

from pykdump.API import *
from LinuxDump.BTstack import *
import LinuxDump.fregsapi as fregsapi
from LinuxDump.fs.dcache import *
from ktime import *
from lnet import *
import ptlrpc as ptlrpc
import obd as obd
try :
    import mdt as mdt
except TypeError :
    pass

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
#define MDS_INODELOCK_DOM    0x000040
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

def res2fid(res) :
    return obd.Fid("0x%x:0x%x:0x%x" % (res.lr_name.name[0], res.lr_name.name[1],
            res.lr_name.name[2]))

def policy_data2str(lr_type, data) :
    if lr_type == ldlm_types.LDLM_IBITS :
        return "%s" % dbits2str(data.l_inodebits.bits, MDS_INODELOCK)
    elif lr_type == ldlm_types.LDLM_EXTENT :
        return "[%d-%d]" % (data.l_extent.start, data.l_extent.end)
    elif lr_type == ldlm_types.LDLM_FLOCK :
        try :
            return "[%d-%d] pid: %d owner: %x" % (data.l_flock.start,
                data.l_flock.end, data.l_flock.pid, data.l_flock.owner)
        except KeyError :
            return "[%d-%d] pid: %d owner: %x" % (data.l_flock.lfw_start,
                data.l_flock.lfw_end, data.l_flock.lfw_pid,
                data.l_flock.lfw_owner)

    return "%s" % data

def print_ldlm_request(prefix, req) :
    res = req.lock_desc.l_resource
    if res.lr_type != 0 :
        print("%s %s %s %s %s" %
                (prefix, ldlm_types.__getitem__(res.lr_type), res2str(res),
                ldlm_mode2str(req.lock_desc.l_req_mode),
                policy_data2str(res.lr_type, req.lock_desc.l_policy_data)))
    n = req.lock_count
    if n == 0 :
        n = 1
    if n > 2 :
        n = 2
    for i in range(n) :
        print("%s 0x%x" % (prefix, req.lock_handle[i].cookie))

def print_ldlm_reply(prefix, rep) :
    res = rep.lock_desc.l_resource
    if res.lr_type != 0 :
        print("%s %s %s %s %s 0x%x %s %x %d" %
                (prefix, ldlm_types.__getitem__(res.lr_type), res2str(res),
                ldlm_mode2str(rep.lock_desc.l_granted_mode),
                policy_data2str(res.lr_type, rep.lock_desc.l_policy_data),
                rep.lock_handle.cookie, dbits2str(rep.lock_flags, LDLM_flags),
                rep.lock_policy_res1, rep.lock_policy_res2))

def lock_client(lock) :
    if lock.l_export != 0 :
        remote = ptlrpc.exp_cl_str(lock.l_export)
    elif lock.l_conn_export != 0 :
        remote = lock.l_conn_export.exp_obd.obd_name
    else :
        remote = "local lock"
    return remote

def get_bl_ast_seconds(lock) :
    try :
         sec = lock.l_blast_sent
    except :
         sec = lock.l_last_activity
    return sec

def get_last_activity_seconds(lock) :
    try :
         sec = lock.l_activity
    except :
         sec = lock.l_last_activity
    return sec

def lock_refc(lock) :
    try :
        refc = lock.l_refc.counter
    except :
        refc = lock.l_handle.h_ref.refs.counter
    return refc

def lock_cb_time(lock) :
    try:
        return lock.l_callback_timeout
    except:
        return lock.l_callback_timestamp

def print_ldlm_lock(ldlm_lock, prefix) :
    print(prefix, ldlm_lock)
    pid = ldlm_lock.l_pid
    remote = lock_client(ldlm_lock)

    print("%s 0x%x/0x%x lrc %u/%d,%d %s %s %s" % (prefix,
                            ldlm_lock.l_handle.h_cookie,
                            ldlm_lock.l_remote_handle.cookie,
                            lock_refc(ldlm_lock), ldlm_lock.l_readers,
                            ldlm_lock.l_writers, remote,
                            res2str(ldlm_lock.l_resource), pid))
    print(prefix, "flags:", dbits2str(ldlm_lock.l_flags, LDLM_flags))
    if ldlm_lock.l_req_mode == ldlm_lock.l_granted_mode :
        timeout = ""
        t = lock_cb_time(ldlm_lock)
        if t != 0 :
            timeout = "will timeout in " + str(t - ktime_get_seconds())

        print(prefix, "granted", ldlm_mode2str(ldlm_lock.l_granted_mode),
                timeout)

        if ldlm_lock.l_flags & LDLM_flags.LDLM_FL_NS_SRV :
            try :
                last_used = ldlm_lock.l_last_used.tv64
            except :
                last_used = 0
            if last_used != 0 :
                sec = (ktime_get() - last_used)/1000000000
                print(prefix, "last used", sec, "sec ago")
        else:
            sec = get_seconds() - ldlm_lock.l_activity
            print(prefix, "enqueued", sec, "sec ago")

        if ldlm_lock.l_flags & LDLM_flags.LDLM_FL_WAITED :
            print(prefix, "BL AST sent",
                    get_seconds() - get_bl_ast_seconds(ldlm_lock), "sec ago")
    else :
        print("%s req_mode: %s enqueued %us ago" % (prefix,
              ldlm_mode2str(ldlm_lock.l_req_mode),
              get_seconds() - get_last_activity_seconds(ldlm_lock)))
    if ldlm_lock.l_resource.lr_type == ldlm_types.LDLM_EXTENT :
        print("%s [%d-%d] requested [%d-%d]" % (prefix,
            ldlm_lock.l_policy_data.l_extent.start,
            ldlm_lock.l_policy_data.l_extent.end,
            ldlm_lock.l_req_extent.start, ldlm_lock.l_req_extent.end))
    else :
        print("%s %s" % (prefix, policy_data2str(ldlm_lock.l_resource.lr_type,
            ldlm_lock.l_policy_data)))

def find_lock_by_cookie(cookie) :
    handle = obd.class_handle2object(cookie)
    if handle :
        return readSU("struct ldlm_lock", Addr(handle))
    return None

def show_mlh(mlh, prefix) :
    cookie = mlh.mlh_pdo_lh.cookie
    if cookie :
        print("pdo %x" % cookie)
        lock = find_lock_by_cookie(cookie)
        if lock :
            print_ldlm_lock(lock, prefix + "\t")

    cookie = mlh.mlh_reg_lh.cookie
    if cookie :
        print("reg %x" % cookie)
        lock = find_lock_by_cookie(cookie)
        if lock :
            print_ldlm_lock(lock, prefix + "\t")

def get_hash_elements(hs) :
    buckets = hs.hs_buckets
    bucket_num = 1 << (hs.hs_cur_bits - hs.hs_bkt_bits)
    for ix in range(0, bucket_num) :
        bd = buckets[ix]
        if bd != 0 :
            a = int(bd.hsb_head)
            for offset in range(0, 1 << hs.hs_bkt_bits) :
                hlist = readSU("struct hlist_head", a + 8*2*offset)
                if hlist != 0 :
                    yield hlist

def show_resource_hdr(res) :
    try:
        recent = "recent lock " + ldlm_mode2str(res.lr_most_restr)
    except:
        recent = ""
    if res.lr_ns_bucket.nsb_namespace.ns_client == 0x2 and res.lr_type == ldlm_types.LDLM_IBITS :
        inode = "%s" % res.lr_lvb_inode
        if res.lr_lvb_inode and S_ISDIR(res.lr_lvb_inode.i_mode) :
            inode += " DIR"
    else :
        inode = ""
    print("res %x %s %s refc %d %s %s" %
            (res, ldlm_types.__getitem__(res.lr_type), res2str(res),
            res.lr_refcount.counter, recent, inode))
    if res.lr_waiting.next != res.lr_waiting.prev and res.lr_granted.next == res.lr_granted.prev :
        print("Error: Empty granted list while locks are waiting !!!")

def show_resource(res) :
    show_resource_hdr(res)
    granted = readSUListFromHead(res.lr_granted,
                "l_res_link", "struct ldlm_lock", maxel=res.lr_refcount.counter)
    for lock in granted :
        if (not args.active) or lock.l_readers != 0 or lock.l_writers != 0:
                print_ldlm_lock(lock, "    ")
#                for l in granted :
#                    if l != lock and lock_compatible(lock, l) == False :
#                        print("not compatible !!! :")
#                        print_ldlm_lock(l, "         ")

    waiting = readSUListFromHead(res.lr_waiting,
                "l_res_link", "struct ldlm_lock", maxel=res.lr_refcount.counter)
    if len(waiting) > 0 :
        print("waiting locks:")
        for lock in waiting :
            print_ldlm_lock(lock, "    ")
            compatible = True
            for ll in granted :
                if not lock_compatible(lock, ll) :
                    compatible = False
                    print("\t\tconflicts with granted :")
                    print_ldlm_lock(ll, "\t\t\t")
                    break
            if not compatible :
                continue
            for l in waiting :
                if l != lock and not lock_compatible(lock, l) :
                    compatible = False
                    print("\t\tconflicts with waiting !!! :")
                    print_ldlm_lock(l, "\t\t\t")
                    break
            if compatible:
                print("\t\t ready to grant !!!")

def get_ns_resources(ns) :
    offset = getStructInfo('struct ldlm_resource')['lr_hash'].offset
    for e in get_hash_elements(ns.ns_rs_hash) :
        for re in readStructNext(e.first, "next") :
            yield readSU("struct ldlm_resource", int(re) - offset)

def show_ns_locks(ns) :
    print("ns %x %s total granted %d" % (ns, ns.ns_obd.obd_name,
        ns.ns_pool.pl_granted.counter))
    for res in get_ns_resources(ns) :
        show_resource(res)

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

def cli_granted_locks() :
    l = readSymbol("ldlm_cli_active_namespace_list")
    nss = readSUListFromHead(l, "ns_list_chain", "struct ldlm_namespace")
    for ns in nss :
       for res in get_ns_resources(ns) :
           yield from readSUListFromHead(res.lr_granted,
                "l_res_link", "struct ldlm_lock")

def lock_compatible(lock1, lock2) :
    if lck_compat_array[lock1.l_req_mode] & lock2.l_req_mode == 0 :
        if lock1.l_resource.lr_type == ldlm_types.LDLM_IBITS :
            bits = lock1.l_policy_data.l_inodebits.bits
            if bits & lock2.l_policy_data.l_inodebits.bits != 0 :
                return False
            else :
                return True
        elif lock1.l_resource.lr_type == ldlm_types.LDLM_EXTENT :
            pol1 = lock1.l_policy_data.l_extent
            pol2 = lock2.l_policy_data.l_extent
            if pol1.end < pol2.start or pol1.start > pol2.end :
                return True
            else :
                return False
        elif lock1.l_resource.lr_type == ldlm_types.LDLM_FLOCK :
            pol1 = lock1.l_policy_data.l_flock
            pol2 = lock2.l_policy_data.l_flock
            if pol1.owner == pol2.owner:
                return True
            if pol2.start < pol1.start :
                t = pol1
                pol1 = pol2
                pol2 = t
            if pol1.end < pol2.start or pol1.start > pol2.end :
                return True
            else :
                return False
        else :
            return False
    return True

def find_conflicting_in_list(lock, lr_list) :
    locks = readSUListFromHead(lr_list, "l_res_link", "struct ldlm_lock")
    for l in locks :
        if l != lock and lock_compatible(lock, l) == False :
            return l

    return None

def find_conflicting_lock(lock) :
    conflict = find_conflicting_in_list(lock, lock.l_resource.lr_granted)
    if conflict :
        return conflict

    conflict = find_conflicting_in_list(lock, lock.l_resource.lr_waiting)
    if conflict :
        return conflict

    return None

def parse_ldlm_cp_ast(stack) :
    if ptlrpc.stack_has_func(stack, "ldlm_completion_ast") :
        addr = ptlrpc.search_stack_for_reg("RBX", stack, "schedule_timeout")
        if addr == 0 :
            addr = ptlrpc.search_stack_for_reg("RBX", stack, "__schedule")
        if addr == 0 :
            addr = ptlrpc.search_stack_for_reg("RBX", stack, "schedule")
        if addr != 0 :
            lock = readSU("struct ldlm_lock", addr)
            print_ldlm_lock(lock, "")
            return lock
    return None

def show_tgt(pid) :
    req = ptlrpc.show_pid(pid, None)
    if req == 0:
        return 0
    env = req.rq_srv.sr_svc_thread.t_env
    key = readSymbol("mdt_thread_key")
    if key.lct_tags == 16 or key.lct_tags == 256 :
        val = env.le_ses.lc_value[key.lct_index]
    else :
        val = env.le_ctx.lc_value[key.lct_index]
    if val != 0 :
        mti = readSU("struct mdt_thread_info", val)
        print(mti)
        mdt.parse_mti(mti, ptlrpc.get_opc(req), "")

    return parse_ldlm_cp_ast(ptlrpc.get_stacklist(pid))

def show_completition_waiting_locks() :
    res = dict()
    (funcpids, functasks, alltaskaddrs) = _get_threads_subroutines()
    waiting_pids = funcpids["ldlm_completion_ast"]
    for pid in ptlrpc.sort_pids_by_start_time(waiting_pids) :
        lock = show_tgt(pid)
        conflict = find_conflicting_lock(lock)
        try :
            count = res[conflict][0]
            max_wait = res[conflict][1]
        except :
            count = 0
            max_wait = 0
        count = count + 1
        cur_wait = get_seconds() - get_last_activity_seconds(lock)
        if max_wait < cur_wait :
            max_wait = cur_wait
        res[conflict] = [count, max_wait]
    print("--------------")
    for l in res :
        print("%d threads are waiting (max %ss) for" % (res[l][0], res[l][1]))
        print_ldlm_lock(l, "")

def req_has_cancel(req, handle) :
    body = readSU("struct ptlrpc_body_v3", ptlrpc.get_req_buffer(req, 0))
    if body.pb_opc != ptlrpc.opcodes.LDLM_ENQUEUE and body.pb_opc != ptlrpc.opcodes.LDLM_CANCEL :
           return False
    ldlm_req = readSU("struct ldlm_request", ptlrpc.get_req_buffer(req, 1))
    n = ldlm_req.lock_count
    if n == 0 :
        n = 1
    for i in range(n) :
        if ldlm_req.lock_handle[i].cookie == handle :
            return True
    return False

def exp_find_cancel(exp, handle) :
    rq_info = getStructInfo('struct ptlrpc_request')
    srv_rq_info = getStructInfo('struct ptlrpc_srv_req')
    offset = rq_info['rq_srv'].offset + srv_rq_info['sr_exp_list'].offset

    entry = exp.exp_hp_rpcs
    while entry.prev != exp.exp_hp_rpcs :
        entry = entry.prev
        req = readSU("struct ptlrpc_request", int(entry) - offset)
        if req_has_cancel(req, handle) :
            return req
    entry = exp.exp_reg_rpcs
    while entry.prev != exp.exp_reg_rpcs :
        entry = entry.prev
        req = readSU("struct ptlrpc_request", int(entry) - offset)
        if req_has_cancel(req, handle) :
            return req
    return None

def show_BL_AST_locks() :
    ptlrpc_all_services = readSymbol("ptlrpc_all_services")
    services = readSUListFromHead(ptlrpc_all_services,
                "srv_list", "struct ptlrpc_service")
    waiting_locks_list = readSymbol("waiting_locks_list")
    waiting = readSUListFromHead(waiting_locks_list,
                "l_pending_chain", "struct ldlm_lock")
    bad = set()
    for lock in waiting :
        print_ldlm_lock(lock, "")
        cancel = exp_find_cancel(lock.l_export, lock.l_handle.h_cookie)
        if cancel :
            print("Cancel has arrived")
            ptlrpc.show_ptlrpc_request(cancel)
        else :
            if get_seconds() - get_bl_ast_seconds(lock) > 50 :
                bad.add(lock.l_export)
        print()

    if len(bad) == 0 :
        return

    print(len(bad), "bad clients:")
    print(*sorted([nid2str(e.exp_connection.c_peer.nid) for e in bad]))
    print()

    for exp in bad :
        ptlrpc.show_export("    ", exp)
        remote = ptlrpc.exp_cl_str(exp)
        pattern = re.compile(remote)
        for srv in services :
            ptlrpc.show_waiting(srv, pattern)
        print()

def analyze_deadlock(lock) :
    res = lock.l_resource
    print("starting lock", lock)
    print()

    show_resource(lock.l_resource)

    if lock.l_req_mode == lock.l_granted_mode :
        conflict = find_conflicting_in_list(lock, lock.l_resource.lr_waiting)
    else :
        conflict = find_conflicting_in_list(lock, lock.l_resource.lr_granted)

    while conflict :
        print("\nconflicting lock", conflict)
        if conflict.l_req_mode == conflict.l_granted_mode :
            print_ldlm_lock(conflict, "")

        print()
        if conflict.l_export :
            lock = 0
        else :
            lock = show_tgt(conflict.l_pid)

        if lock == 0 :
            if conflict.l_req_mode != conflict.l_granted_mode :
                print_ldlm_lock(conflict, "")
            print("\nexport", conflict.l_export, ":")
            if conflict.l_export != 0 :
                ptlrpc.show_export("", conflict.l_export)
            return

        print("lock", lock);
        conflict = find_conflicting_lock(lock)

    if not conflict :
        print("\nError: no conflict")
        show_resource(lock.l_resource)

def show_ns_info(ns_list) :
    namespaces = readSUListFromHead(ns_list, "ns_list_chain", "struct ldlm_namespace")
    for ns in namespaces :
        try :
            name = ns.ns_name
        except:
            name = ns.ns_rs_hash.hs_name
        print(ns, name, "lock count", obd.stats_couter_sum(ns.ns_stats, 0))

def list_namespaces() :
    print("SRV namespaces:")
    show_ns_info(readSymbol("ldlm_srv_namespace_list"))
    print("CLI namespaces:")
    show_ns_info(readSymbol("ldlm_cli_active_namespace_list"))

if ( __name__ == '__main__'):
    import argparse

    parser =  argparse.ArgumentParser()
    parser.add_argument("-l","--lock", dest="lock", default = 0)
    parser.add_argument("-c","--cookie", dest="cookie", default = 0)
    parser.add_argument("-r","--res", dest="res", default = 0)
    parser.add_argument("-R","--show-res", dest="show_res",
                        action='store_true')
    parser.add_argument("-n","--ns", dest="ns", default = 0)
    parser.add_argument("-g","--grep", dest="g", default = 0)
    parser.add_argument("-w","--compwait", dest="compl_waiting",
                        action='store_true')
    parser.add_argument("-b","--blocking", dest="blocking",
                        action='store_true')
    parser.add_argument("-a","--active", dest="active",
                        action='store_true')
    parser.add_argument("-N","--show-namespaces", dest="show_namespaces",
                        action='store_true')
    parser.add_argument("-p","--pid", dest="pid", default = 0)
    parser.add_argument("-G","--granted", dest="granted_pid", default = 0)
    parser.add_argument("-f","--flags", dest="flags", default = 0)
    parser.add_argument("-d","--dealock", dest="dead", default = 0)
    args = parser.parse_args()

    if args.lock != 0 :
        l = readSU("struct ldlm_lock", int(args.lock, 16))
        if args.show_res :
            show_resource(l.l_resource)
        else:
            print_ldlm_lock(l, "")
    elif args.cookie != 0 :
        lock = find_lock_by_cookie(int(args.cookie, 16))
        if lock :
            print_ldlm_lock(lock, "")
    elif args.res != 0 :
        res = readSU("struct ldlm_resource", int(args.res, 16))
        show_resource(res)
    elif args.show_namespaces :
        list_namespaces()
    elif args.ns != 0 :
        ns = readSU("struct ldlm_namespace", int(args.ns, 16))
        if args.show_res :
            print("ns %x %s total granted %d" % (ns, ns.ns_obd.obd_name,
                ns.ns_pool.pl_granted.counter))
            res_sorted = sorted(get_ns_resources(ns),
                    key = lambda res : res.lr_refcount.counter,  reverse=True)
            for res in res_sorted :
                show_resource_hdr(res)
        else:
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
    elif args.dead != 0 :
        l = readSU("struct ldlm_lock", int(args.dead, 16))
        analyze_deadlock(l)
    elif args.granted_pid != 0 :
        for lock in sorted(filter(lambda l : l.l_pid == int(args.granted_pid),
                                    cli_granted_locks()),
                            key = lambda l : l.l_activity) :
            print_ldlm_lock(lock, "")
    else :
        show_namespaces(r'.*')

