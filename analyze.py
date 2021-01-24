from pykdump.API import *
from LinuxDump.BTstack import *
import LinuxDump.fregsapi as fregsapi
import LinuxDump.KernLocks as kernlocks
import LinuxDump.fs as fs
import crashlib.util as crutil
import ktime as ktime
import obd as obd
import ptlrpc as ptlrpc
import ldlm_lock as ldlm

try:
    import mdt as mdt
except:
    pass

try:
    import cl_io as cl_io
    import cl_lock as cl_lock
    cli_modules = True
except:
    cli_modules = False

def cli_get_dentry(stack) :
    addr = ptlrpc.search_stack_for_reg("RDI", stack, "notify_change")
    if addr != 0 :
        dentry = readSU("struct dentry", addr)
        return dentry

    addr = ptlrpc.search_stack_for_reg("RSI", stack, "ll_getattr")
    if addr != 0 :
        dentry = readSU("struct dentry", addr)
        return dentry

    return None

def cli_get_inode(stack) :
    addr = ptlrpc.search_stack_for_reg("RDX", stack, "ll_file_io_generic")
    if addr != 0 :
        f = readSU("struct file", addr)
        return f.f_inode

    addr = ptlrpc.search_stack_for_reg("RDI", stack, "ll_lookup_it")
    if addr != 0 :
        inode = readSU("struct inode", addr)
        return inode

    addr = ptlrpc.search_stack_for_reg("RDI", stack, "ll_close_inode_openhandle")
    if addr != 0 :
        inode = readSU("struct inode", addr)
        return inode

    addr = ptlrpc.search_stack_for_reg("RDX", stack, "cl_glimpse_lock")
    if addr != 0 :
        inode = readSU("struct inode", addr)
        return inode

    addr = ptlrpc.search_stack_for_reg("RDI", stack, "ll_new_node")
    if addr != 0 :
        inode = readSU("struct inode", addr)
        return inode

    addr = ptlrpc.search_stack_for_reg("RDI", stack, "ll_layout_conf")
    if addr != 0 :
        inode = readSU("struct inode", addr)
        return inode

    addr = ptlrpc.search_stack_for_reg("RDI", stack, "ll_layout_intent")
    if addr != 0 :
        inode = readSU("struct inode", addr)
        return inode

    return None

def cli_get_request(stack, prefix) :
    addr = ptlrpc.search_stack_for_reg("RSI", stack, "ptlrpc_set_wait")
    if addr != 0 :
        print()
        rqset = readSU("struct ptlrpc_request_set", addr)
        ptlrpc.show_ptlrpc_set(rqset)
        return rqset

    addr = ptlrpc.search_stack_for_reg("RSI", stack, "ldlm_cli_enqueue")
    if addr != 0 :
        print()
        addr = readU64(addr)
        if addr != 0 :
            req = readSU("struct ptlrpc_request", addr)
            ptlrpc.show_ptlrpc_request(req)
            return req

    addr = ptlrpc.search_stack_for_reg("RSI", stack, "ldlm_cli_enqueue_fini")
    if addr != 0 :
        print()
        req = readSU("struct ptlrpc_request", addr)
        ptlrpc.show_ptlrpc_request(req)
        return req

    addr = ptlrpc.search_stack_for_reg("RDI", stack, "wait_for_completion")
    if addr != 0 :
        print()
        cbargs_addr = addr - getStructInfo('struct osc_async_cbargs')['opc_sync'].offset
        cbargs = readSU("struct osc_async_cbargs", cbargs_addr)
        print(cbargs)
        res = exec_crash_command("search 0x%x" % cbargs_addr)
        if len(res) == 0 :
            print("no matches!")
            return None
        print(res)
        for s in res.splitlines():
            m = obd.__re_search.match(s)
            if (m) :
                addr = int(m.group(1), 16)
                req = readSU("struct ptlrpc_request", addr - 0x180)
                ptlrpc.show_ptlrpc_request(req)
                return req

    return None

def dentry2path(de) :
    p = fs.get_dentry_name(de)
    while de.d_parent != 0 and de.d_parent != de:
        de = de.d_parent
        p = fs.get_dentry_name(de) + "/" + p
    return p

def show_client_pid(pid, prefix) :
    stack = ptlrpc.get_stacklist(pid)
    if stack == None :
        return

    dentry = cli_get_dentry(stack)
    if dentry :
        print()
        print(prefix, dentry2path(dentry))
        cl_io.print_dentry(dentry)
        cl_io.print_inode(prefix, dentry.d_inode)
    else :
        inode = cli_get_inode(stack)
        print()
        cl_io.print_inode(prefix, inode)

    try :
        addr = ptlrpc.search_stack_for_reg("RDX", stack, "cl_lock_request")
    except:
        addr = 0
    if addr != 0 :
        print()
        cl = readSU("struct cl_lock", addr)
        cl_lock.print_cl_lock(cl, prefix)
    else :
        addr = ptlrpc.search_stack_for_reg("RSI", stack, "lov_lock_enqueue")
        if addr != 0 :
            print()
            lock_slice = readSU("struct cl_lock_slice", addr)
            cl_lock.print_cl_lock(lock_slice.cls_lock, prefix)

    addr = ptlrpc.search_stack_for_reg("RSI", stack, "lmv_revalidate_slaves")
    if addr != 0 :
        print()
        lsm = readSU("struct lmv_stripe_md", addr)
        cl_io.print_lsm("", lsm)

    addr = ptlrpc.search_stack_for_reg("RSI", stack, "__wait_on_bit_lock")
    if addr != 0 :
        print()
        wb = readSU("struct wait_bit_queue", addr)
        page = readSU("struct page", wb.key.flags)
        cl_page = readSU("struct cl_page", page.private)
        cl_io.print_cl_page(cl_page, "")

    addr = ptlrpc.search_stack_for_reg("RSI", stack, "ll_readpage")
    if addr != 0 :
        print()
        page = readSU("struct page", addr)
        cl_page = readSU("struct cl_page", page.private)
        cl_io.print_cl_page(cl_page, "")

    req = cli_get_request(stack, prefix)

    addr = ptlrpc.search_stack_for_reg("RDI", stack, "__mutex_lock_slowpath")
    if addr != 0 :
        print()
        mutex = readSU("struct mutex", addr)
        kernlocks.decode_mutex(mutex)

    addr = ptlrpc.search_stack_for_reg("RDI", stack, "__pv_queued_spin_lock_slowpath")
    if addr != 0 :
        print()
        qspin = readSU("struct qspinlock", addr)
        print(qspin)
        t = crutil.read_qspinlock(qspin)
        print(t)

    addr = ptlrpc.search_stack_for_reg("RSI", stack, "osc_extent_wait")
    if addr != 0 :
        print()
        ext = readSU("struct osc_extent", addr)
        print(ext)

    addr = ptlrpc.search_stack_for_reg("RDI", stack, "obd_get_mod_rpc_slot")
    if addr != 0 :
        print()
        cli_obd = readSU("struct client_obd", addr)
    elif req != None :
        cli_obd = req.rq_import.imp_obd.u.cli

    if cli_obd :
        print("\n%s %s mod slots %d/%d" % (cli_obd, cli_obd.cl_import,
            cli_obd.cl_mod_rpcs_in_flight, cli_obd.cl_max_mod_rpcs_in_flight))
        if cli_obd.cl_mod_rpcs_in_flight == cli_obd.cl_max_mod_rpcs_in_flight :
            ptlrpc.show_import("", cli_obd.cl_import)
            ptlrpc.imp_show_requests(cli_obd.cl_import)

    return req != None

def find_bl_handler(lock) :
    (funcpids, functasks, alltaskaddrs) = get_threads_subroutines_slow()
    pids = funcsMatch(funcpids, "ldlm_handle_bl_callback")
    for pid in pids :
        stack = ptlrpc.get_stacklist(pid)
        addr = ptlrpc.search_stack_for_reg("RDX", stack, "ldlm_handle_bl_callback")
        if addr == 0 :
            addr = ptlrpc.search_stack_for_reg("RDI", stack, "osc_ldlm_blocking_ast")
        if addr != Addr(lock) :
            continue
        print("\n    Pid", pid, "is serving BL callback")
        show_client_pid(pid, "    ")
        break

def parse_import_eviction(imp) :
    ptlrpc.show_import("", imp)
    ptlrpc.imp_show_state_history("", imp)

    cli_waits = False
    print("\n=== BL AST pending locks ===")
    for res in ldlm.get_ns_resources(imp.imp_obd.obd_namespace) :
        granted = readSUListFromHead(res.lr_granted,
                "l_res_link", "struct ldlm_lock")
        for lock in sorted(granted, key = lambda l : l.l_activity) :
            if lock.l_flags & ldlm.LDLM_flags.LDLM_FL_BL_AST != 0:
                print()
                ldlm.print_ldlm_lock(lock, "")
                if lock.l_activity < 100 :
                    continue
                if lock.l_readers != 0 or lock.l_writers != 0 :
                    if show_client_pid(lock.l_pid, "") :
                        cli_waits = True
                else :
                    find_bl_handler(lock)
                if lock.l_resource.lr_type == ldlm.ldlm_types.LDLM_EXTENT :
                    if lock.l_ast_data != 0 :
                        osc_obj = readSU("struct osc_object", lock.l_ast_data)
                        print("osc obj in l_ast_data", osc_obj)

    if not cli_waits :
        ptlrpc.imp_show_requests(imp)
#       ptlrpc.imp_show_history(imp)

def parse_client_eviction(stack) :
    addr = ptlrpc.search_stack_for_reg("RDI", stack, "ptlrpc_import_recovery_state_machine")
    if addr == 0 :
        return 0
    imp = readSU("struct obd_import", addr)
    parse_import_eviction(imp)

def parse_version_mismatch(stack) :
    addr = ptlrpc.search_stack_for_reg("RSI", stack, "ptlrpc_replay_interpret")
    if addr == 0 :
        return 0
    req = readSU("struct ptlrpc_request", addr)
    ptlrpc.show_ptlrpc_request(req)

def show_bl_ast_lock(lock) :
    ldlm.print_ldlm_lock(lock, "")
    cli_pid = 0
    cli_lock = None
    if cli_modules :
        cli_lock = ldlm.find_lock_by_cookie(lock.l_remote_handle.cookie)
    if cli_lock :
        print("client lock:")
        ldlm.print_ldlm_lock(cli_lock, "")
        cli_pid = cli_lock.l_pid

    if cli_lock == None or not cli_lock.l_flags & ldlm.LDLM_flags.LDLM_FL_BL_AST:
        received_bl_ast = False
        svc = ptlrpc.find_service("ldlm_cbd")
        if svc :
            for req in ptlrpc.get_history_reqs(svc) :
                if ptlrpc.get_opc(req) == ptlrpc.opcodes.LDLM_BL_CALLBACK :
                    ldlm_req = readSU("struct ldlm_request", ptlrpc.get_req_buffer(req, 1))
                    if ldlm_req.lock_handle[0].cookie == lock.l_remote_handle.cookie :
                        ptlrpc.show_ptlrpc_request(req)
                        received_bl_ast = True
    else :
        received_bl_ast = True
    if not received_bl_ast :
        svc = ptlrpc.find_service("mdt")
        if svc :
            for req in ptlrpc.get_history_reqs(svc) :
                if ptlrpc.get_opc(req) == ptlrpc.opcodes.LDLM_ENQUEUE :
                    ldlm_req = readSU("struct ldlm_request", ptlrpc.get_req_buffer(req, 1))
                    if ldlm_req.lock_handle[0].cookie == lock.l_remote_handle.cookie :
                        ptlrpc.show_ptlrpc_request(req)
                        if cli_pid == 0 :
                            cli_pid = ptlrpc.get_pid(req)
    mdt.find_print_fid(lock.l_export.exp_obd.obd_lu_dev,
            ldlm.res2fid(lock.l_resource), "    ")

    if cli_pid != 0 :
        print("client PID", cli_pid)
        if cli_modules :
            show_client_pid(cli_pid, "    ")

def parse_srv_eviction(stack) :
    addr = ptlrpc.search_stack_for_reg("R13", stack, "panic")
    if addr == 0 :
        return 0
    l_exp_list_off = getStructInfo('struct ldlm_lock')['l_exp_list'].offset
    lock = readSU("struct ldlm_lock", addr - l_exp_list_off)
    print("evicted lock:")
    show_bl_ast_lock(lock)
    print()

    print("waiting locks:")
    waiting_locks_list = readSymbol("waiting_locks_list")
    waiting = readSUListFromHead(waiting_locks_list,
                "l_pending_chain", "struct ldlm_lock")
    for lock in waiting :
        show_bl_ast_lock(lock)
        print()

def analyze_eviction() :
    btsl = exec_bt("bt")
    for s in btsl:
        fregsapi.search_for_registers(s)
    for bts in btsl :
        pid = bts.pid
        print("current pid:", pid, "time:", ktime.get_seconds(),
                ktime.ktime_get_seconds())
        parsed = False
        for f in bts.frames:
            if f.func == "ptlrpc_import_recovery_state_machine" :
                parse_client_eviction(btsl)
                parsed = True
                break
            elif f.func == "expired_lock_main" :
                parse_srv_eviction(btsl)
                parsed = True
                break
            elif f.func == "ptlrpc_replay_interpret" :
                parse_version_mismatch(btsl)
                parsed = True
                break
        if not parsed :
            print(bts)

if ( __name__ == '__main__'):
    import argparse

    parser =  argparse.ArgumentParser()
    parser.add_argument("-p","--pid", dest="pid", default = 0)
    parser.add_argument("-i","--import", dest="imp", default = 0)
    args = parser.parse_args()

    if args.pid != 0 :
        show_client_pid(int(args.pid), "")
    elif args.imp != 0 :
        imp = readSU("struct obd_import", int(args.imp, 16))
        parse_import_eviction(imp)
    else :
        analyze_eviction()

