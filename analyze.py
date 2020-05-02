from pykdump.API import *
from LinuxDump.BTstack import *
import LinuxDump.fregsapi as fregsapi
import LinuxDump.KernLocks as kernlocks
import ktime as ktime
import obd as obd
import ptlrpc as ptlrpc
import ldlm_lock as ldlm
import mdt as mdt
try:
    import cl_io as cl_io
    import cl_lock as cl_lock
    cli_modules = True
except:
    cli_modules = False

def show_client_pid(pid, prefix) :
    stack = ptlrpc.get_stacklist(pid)
    if stack == None :
        return

    addr = ptlrpc.search_stack_for_reg("RDX", stack, "ll_file_io_generic")
    if addr != 0 :
        print()
        f = readSU("struct file", addr)
        cl_io.print_inode(prefix, f.f_inode)

    addr = ptlrpc.search_stack_for_reg("RDI", stack, "notify_change")
    if addr != 0 :
        print()
        dentry = readSU("struct dentry", addr)
        cl_io.print_dentry(dentry)
        cl_io.print_inode(prefix, dentry.d_inode)

    addr = ptlrpc.search_stack_for_reg("RDI", stack, "ll_lookup_it")
    if addr != 0 :
        print()
        inode = readSU("struct inode", addr)
        cl_io.print_inode(prefix, inode)

    addr = ptlrpc.search_stack_for_reg("RSI", stack, "ll_getattr")
    if addr != 0 :
        print()
        dentry = readSU("struct dentry", addr)
        cl_io.print_dentry(dentry)
        cl_io.print_inode(prefix, dentry.d_inode)

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

    addr = ptlrpc.search_stack_for_reg("RSI", stack, "ptlrpc_set_wait")
    if addr != 0 :
        print()
        rqset = readSU("struct ptlrpc_request_set", addr)
        ptlrpc.show_ptlrpc_set(rqset)
    else :
        addr = ptlrpc.search_stack_for_reg("RSI", stack, "ldlm_cli_enqueue")
        if addr != 0 :
            print()
            addr = readU64(addr)
            if addr != 0 :
                req = readSU("struct ptlrpc_request", addr)
                ptlrpc.show_ptlrpc_request(req)

    addr = ptlrpc.search_stack_for_reg("RDI", stack, "__mutex_lock_slowpath")
    if addr != 0 :
        print()
        mutex = readSU("struct mutex", addr)
        kernlocks.decode_mutex(mutex)


def parse_import_eviction(imp) :
    ptlrpc.show_import("", imp)
    ptlrpc.imp_show_state_history("", imp)

    print("\n=== BL AST pending locks ===")
    for res in ldlm.get_ns_resources(imp.imp_obd.obd_namespace) :
        granted = readSUListFromHead(res.lr_granted,
                "l_res_link", "struct ldlm_lock")
        for lock in granted :
            if lock.l_flags & ldlm.LDLM_flags.LDLM_FL_BL_AST != 0:
                ldlm.print_ldlm_lock(lock, "")
                show_client_pid(lock.l_pid, "")

    ptlrpc.imp_show_requests(imp)
    ptlrpc.imp_show_history(imp)

def parse_client_eviction(stack) :
    addr = ptlrpc.search_stack_for_reg("RDI", stack, "ptlrpc_import_recovery_state_machine")
    if addr == 0 :
        return 0
    imp = readSU("struct obd_import", addr)
    parse_import_eviction(imp)

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
    lock = readSU("struct ldlm_lock", addr)
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

