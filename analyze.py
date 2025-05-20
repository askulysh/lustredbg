from pykdump.API import *
from LinuxDump.BTstack import *
import LinuxDump.fregsapi as fregsapi
import LinuxDump.fs as fs
import crashlib.util as crutil
import ktime as ktime
import obd as obd
import ptlrpc as ptlrpc
import ldlm_lock as ldlm
import cl_io as cl_io

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

def cli_get_fsync_io(stack) :
    addr = ptlrpc.search_stack_for_reg("RSI", stack, "osc_io_fsync_start")
    if addr != 0 :
        io = readSU("struct cl_io_slice", addr)
        return io
    addr = ptlrpc.search_stack_for_reg("RSI", stack, "osc_io_fsync_end")
    if addr != 0 :
        io = readSU("struct cl_io_slice", addr)
        return io
    return None

def cli_show_io(stack) :
    addr = ptlrpc.search_stack_for_reg("RSI", stack, "vvp_io_read_start")
    if addr != 0 :
        io = readSU("struct cl_io_slice", addr)
        rd = io.cis_io.u.ci_rd.rd
        print("read: [", rd.crw_pos, "-", rd.crw_pos + rd.crw_count - 1, "]")
        return

    addr = ptlrpc.search_stack_for_reg("RSI", stack, "vvp_io_write_start")
    if addr != 0 :
        io = readSU("struct cl_io_slice", addr)
        wr = io.cis_io.u.ci_wr.wr
        print("write: [", wr.crw_pos, "-", wr.crw_pos + wr.crw_count - 1, "]")
        return

    io = cli_get_fsync_io(stack)
    if io :
        fi = io.cis_io.u.ci_fsync
        print("fsync: [", fi.fi_start, "-", fi.fi_end, "]")

def cli_get_file(stack) :
    addr = ptlrpc.search_stack_for_reg("RSI", stack, "ll_file_open")
    if addr == 0 :
        addr = ptlrpc.search_stack_for_reg("RDI", stack, "do_dentry_open")
    if addr == 0 :
        addr = ptlrpc.search_stack_for_reg("RDX", stack, "ll_atomic_open")
    if addr == 0 :
        addr = ptlrpc.search_stack_for_reg("RDI", stack, "vfs_fallocate")
    if addr != 0 :
        file = readSU("struct file", addr)
        return file

    return None

def cli_get_dentry(stack) :
    addr = ptlrpc.search_stack_for_reg("RDI", stack, "notify_change")
    if addr != 0 :
        dentry = readSU("struct dentry", addr)
        return dentry

    addr = ptlrpc.search_stack_for_reg("RSI", stack, "ll_getattr")
    if addr != 0 :
        dentry = readSU("struct dentry", addr)
        return dentry

    addr = ptlrpc.search_stack_for_reg("RSI", stack, "ll_lookup_it")
    if addr != 0 :
        dentry = readSU("struct dentry", addr)
        return dentry

    addr = ptlrpc.search_stack_for_reg("RDI", stack, "ll_inode_revalidate")
    if addr != 0 :
        dentry = readSU("struct dentry", addr)
        return dentry

    return None

    return None

def cli_get_inode(stack) :
    addr = ptlrpc.search_stack_for_reg("RDX", stack, "ll_file_io_generic")
    if addr != 0 :
        f = readSU("struct file", addr)
        try:
            return f.f_inode
        except:
            pass

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

        rq_info = getStructInfo('struct ptlrpc_request')
        try:
            offset = rq_info['rq_set_chain'].offset
        except KeyError:
            cli_rq_info = getStructInfo('struct ptlrpc_cli_req')
            offset = rq_info['rq_cli'].offset + cli_rq_info['cr_set_chain'].offset

        req = readSU("struct ptlrpc_request", int(rqset.set_requests.next) - offset)
        return req

    addr = ptlrpc.search_stack_for_reg("RSI", stack, "ldlm_cli_enqueue")
    if addr != 0 :
        addr = readU64(addr)

    if addr == 0:
        addr = ptlrpc.search_stack_for_reg("RSI", stack, "ldlm_cli_enqueue_fini")
#    if addr == 0:
#        addr = ptlrpc.search_stack_for_reg("R12", stack, "ldlm_cli_enqueue_fini")
    if addr == 0:
        addr = ptlrpc.search_stack_for_reg("RDI", stack, "ptlrpc_get_mod_rpc_slot")
    if addr != 0 :
        print()
        req = readSU("struct ptlrpc_request", addr)
        print(req)
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
        off = getStructInfo('struct ptlrpc_request')['rq_cli'].offset
        off += getStructInfo('struct ptlrpc_cli_req')['cr_async_args'].offset
        off += getStructInfo('struct osc_setattr_args')['sa_cookie'].offset
        for s in res.splitlines():
            m = obd.__re_search.match(s)
            if (m) :
                addr = int(m.group(1), 16)
                req = readSU("struct ptlrpc_request", addr - off)
                print(req)
                ptlrpc.show_ptlrpc_request(req)
                return req

    return None

def page2cl_page(page) :
    return readSU("struct cl_page", page.private)

def cli_get_page(stack) :
    addr = ptlrpc.search_stack_for_reg("RSI", stack, "__wait_on_bit_lock")
    if addr != 0 :
        wb = readSU("struct wait_bit_queue", addr)
        return readSU("struct page", wb.key.flags)

    addr = ptlrpc.search_stack_for_reg("RDI", stack, "wait_on_page_bit")
    if addr != 0 :
        return readSU("struct page", addr)

    addr = ptlrpc.search_stack_for_reg("RSI", stack, "ll_readpage")
    if addr != 0 :
        return readSU("struct page", addr)

    addr = ptlrpc.search_stack_for_reg("RDX", stack, "ll_io_read_page")
    if addr != 0 :
        cl_page = readSU("struct cl_page", addr)
        return cl_page.cp_vmpage

    return None

def dentry2path(de) :
    p = fs.get_dentry_name(de)
    while de.d_parent != 0 and de.d_parent != de:
        de = de.d_parent
        p = fs.get_dentry_name(de) + "/" + p
    return p

def cli_guess_inode(stack) :
    inode = cli_get_inode(stack)
    if inode :
        return inode

    dentry = None
    file = cli_get_file(stack)
    if file :
        dentry = file.f_path.dentry
        inode = file.f_inode

    if inode :
        return inode

    dentry = cli_get_dentry(stack)
    if dentry :
        if int(dentry.d_inode) != 0 :
            inode = dentry.d_inode

    return inode

def show_sa_pid(stack, prefix) :
    addr = ptlrpc.search_stack_for_reg("RDI", stack, "ll_statahead_thread")
    if addr == 0 :
        return False

    sai = readSU("struct ll_statahead_info", addr)
    print(sai)
    lbh = readSU("struct lmv_batch", sai.sai_bh)
    print(lbh)
    if lbh == 0:
        return True

    for sbh in readSUListFromHead(lbh.lbh_sub_batch_list, "sbh_sub_item",
                                  "struct lmvsub_batch") :
        print(sbh)

    return True

def req_has_cookie(req, cookie):

    if ptlrpc.get_opc(req) == ptlrpc.opcodes.LDLM_ENQUEUE :
        ldlm_req = readSU("struct ldlm_request", ptlrpc.get_req_buffer(req, 1))
        return ldlm_req.lock_handle[0].cookie == cookie

    return False

def show_client_pid(pid, cookie, prefix) :
    stack = ptlrpc.get_stacklist(pid)
    if stack == None :
        return False

    if show_sa_pid(stack, prefix) :
        return True

    print()
    inode  = None
    dentry = None
    file = cli_get_file(stack)
    if file :
        it = readSU("struct lookup_intent", file.private_data)
        print(prefix, it)
        dentry = file.f_path.dentry
        inode = file.f_inode

    if dentry == 0xffffffffffffffff :
        dentry = None

    if dentry == None:
        dentry = cli_get_dentry(stack)
    if dentry :
        print(prefix, dentry2path(dentry))
        cl_io.print_dentry(dentry)
        if int(dentry.d_inode) != 0 :
            inode = dentry.d_inode

    if inode == None:
        inode = cli_get_inode(stack)

    if inode :
        cl_io.print_inode(prefix, inode)
        lli = readSU("struct ll_inode_info", inode -
            member_offset('struct ll_inode_info', 'lli_vfs_inode'))

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

    page = cli_get_page(stack)

    if page :
        print()
        cl_page = page2cl_page(page)
        cl_io.print_cl_page(cl_page, "")

    cli_show_io(stack)

    req = cli_get_request(stack, prefix)

    bl_task = ptlrpc.search_for_mutex(stack)
    if not bl_task :
        bl_task = ptlrpc.search_for_rw_semaphore(stack)
    if not bl_task and  inode :
        bl_task = ptlrpc.rw_sem_owner(lli.lli_lsm_sem)
        if bl_task and bl_task.pid == pid :
            bl_task = None

    if inode :
        print("ll_trunc_readers:", lli.lli_trunc_sem.ll_trunc_readers.counter,
              "ll_trunc_waiters:", lli.lli_trunc_sem.ll_trunc_waiters.counter)

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

    cli_obd = None
    addr = ptlrpc.search_stack_for_reg("RDI", stack, "obd_get_mod_rpc_slot")
    if addr != 0 :
        print()
        cli_obd = readSU("struct client_obd", addr)
        print("Waiting for mod slot !!!")
    else :
        addr = ptlrpc.search_stack_for_reg("RAX", stack, "obd_get_request_slot")
        if addr != 0 :
            print()
            obd = readSU("struct obd_device", addr)
            cli_obd = obd.u.cli
            print("Waiting for obd slot !!!")

    if cli_obd == None and req != None :
        cli_obd = req.rq_import.imp_obd.u.cli

    if req :
        if req_has_cookie(req, cookie) :
            return True

    if cli_obd :
        print("\n%s %s rpcs in flight %d/%d" % (cli_obd, cli_obd.cl_import,
            cli_obd.cl_rpcs_in_flight, cli_obd.cl_max_rpcs_in_flight))
        print("\n%s %s mod slots %d/%d" % (cli_obd, cli_obd.cl_import,
            cli_obd.cl_mod_rpcs_in_flight, cli_obd.cl_max_mod_rpcs_in_flight))
        if cli_obd.cl_mod_rpcs_in_flight == cli_obd.cl_max_mod_rpcs_in_flight or cli_obd.cl_rpcs_in_flight == cli_obd.cl_max_rpcs_in_flight :
            ptlrpc.show_import("", cli_obd.cl_import)
            ptlrpc.imp_show_unreplied_requests(cli_obd.cl_import)

    if bl_task  :
        print("\nPid ", bl_task.pid)
        return show_client_pid(bl_task.pid, 0, prefix)
    elif inode :
        find_inode_handler(inode.i_ino)

    return cli_obd != None

def show_bl_pid(pid, prefix) :
    stack = ptlrpc.get_stacklist(pid)
    if stack == None :
        return
    addr = ptlrpc.search_stack_for_reg("RDI", stack, "ldlm_bl_thread_main")
    if addr != 0 :
        bltd = readSU("struct ldlm_bl_thread_data", addr)
        print("bl pool:", bltd.bltd_blp,
              "total locks:", bltd.bltd_blp.blp_total_locks,
              "blwis:", bltd.bltd_blp.blp_total_blwis);

    addr = ptlrpc.search_stack_for_reg("RDI", stack,
                                       "ldlm_cancel_lock_for_export")
    if addr !=0 :
        exp = readSU("struct obd_export", addr)
        addr = ptlrpc.search_stack_for_reg("RSI", stack,
                                       "ldlm_cancel_lock_for_export")
        lock = readSU("struct ldlm_lock", addr)

        ptlrpc.show_export_hdr(prefix, exp)
        ldlm.print_ldlm_lock(lock, prefix)

    addr = ptlrpc.search_stack_for_reg("RSI", stack, "osc_extent_wait")
    if addr != 0 :
        print()
        ext = readSU("struct osc_extent", addr)
        print(ext)
        cl_io.print_osc_extent(prefix, ext)

def show_cb_pid(pid, prefix) :
    stack = ptlrpc.get_stacklist(pid)
    if stack == None :
        return
    addr = ptlrpc.search_stack_for_reg("RDI", stack,
                                       "ldlm_callback_handler")
    if addr == 0:
        return
    req = readSU("struct ptlrpc_request", addr)
    ptlrpc.show_ptlrpc_request(req)

def find_bl_handler(lock) :
    (funcpids, functasks, alltaskaddrs) = get_threads_subroutines_slow()
    pids = funcsMatch(funcpids, "ldlm_bl_thread_main")
    for pid in pids :
        stack = ptlrpc.get_stacklist(pid)
        addr = ptlrpc.search_stack_for_reg("RDX", stack, "ldlm_handle_bl_callback")
        if addr == 0 :
            addr = ptlrpc.search_stack_for_reg("RDI", stack, "osc_ldlm_blocking_ast")
        if addr != Addr(lock) :
            addr = ptlrpc.search_stack_for_reg("RDI", stack,
                                               "ldlm_cli_cancel_list_local")
            head = readSU("struct list_head", addr)
            cancels = readSUListFromHead(head, "l_bl_ast", "struct ldlm_lock")
            for l in cancels :
                if l == lock:
                    print("\n    Pid", pid, "has the lock in canceling list")
            continue

        print("\n    Pid", pid, "is serving BL callback")
        show_bl_pid(pid, "    ")
        break

def find_inode_handler(ino) :
    (funcpids, functasks, alltaskaddrs) = get_threads_subroutines_slow()
    pids = funcsMatch(funcpids, "do_syscall_64")
    for pid in pids :
        stack = ptlrpc.get_stacklist(pid)
        i = cli_guess_inode(stack)
#        print(pid, i)
        if i and i.i_ino == ino :
            print(pid)

def parse_blast_lock(lock) :
    cli_waits = False
    ldlm.print_ldlm_lock(lock, "")
    if ktime.get_seconds() - lock.l_activity < 100 :
        return False
    if lock.l_granted_mode == ldlm.ldlm_modes.LCK_MINMODE or lock.l_readers != 0 or lock.l_writers != 0 :
        if show_client_pid(lock.l_pid, lock.l_handle.h_cookie, "") :
            cli_waits = True
        else :
            find_bl_handler(lock)
        if lock.l_resource.lr_type == ldlm.ldlm_types.LDLM_EXTENT :
            if lock.l_ast_data != 0 :
                osc_obj = readSU("struct osc_object", lock.l_ast_data)
                print("osc obj in l_ast_data", osc_obj)
    return cli_waits

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
                if parse_blast_lock(lock) :
                        cli_waits = True
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
            show_client_pid(cli_pid, 0, "    ")

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
    parser.add_argument("-B","--bl_pid", dest="bl_pid", default = 0)
    parser.add_argument("-C","--cb_pid", dest="cb_pid", default = 0)
    parser.add_argument("-i","--import", dest="imp", default = 0)
    parser.add_argument("-I","--inode", dest="inode", default = 0)
    parser.add_argument("-l","--lock", dest="lock", default = 0)
    parser.add_argument("-c","--cookie", dest="cookie", default = 0)
    args = parser.parse_args()

    if args.pid != 0 :
        show_client_pid(int(args.pid), 0, "")
    elif args.bl_pid != 0 :
        show_bl_pid(int(args.bl_pid), "")
    elif args.cb_pid != 0 :
        show_cb_pid(int(args.cb_pid), "")
    elif args.inode != 0 :
        find_inode_handler(int(args.inode, 16))
    elif args.imp != 0 :
        imp = readSU("struct obd_import", int(args.imp, 16))
        parse_import_eviction(imp)
    elif args.lock != 0 :
        lock = readSU("struct ldlm_lock", int(args.lock, 16))
        parse_blast_lock(lock)
    elif args.cookie != 0 :
        lock = ldlm.find_lock_by_cookie(int(args.cookie, 16))
        if lock :
            parse_blast_lock(lock)
    else :
        analyze_eviction()

