from pykdump.API import *
from LinuxDump.BTstack import *
import ptlrpc as ptlrpc
import ldlm_lock as ldlm
import cl_io as cl_io
import cl_lock as cl_lock

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

    try :
        addr = ptlrpc.search_stack_for_reg("RDX", stack, "cl_lock_request")
    except:
        addr = 0
    if addr != 0 :
        print()
        cl = readSU("struct cl_lock", addr)
        cl_lock.print_cl_lock(cl, prefix)

def parse_client_eviction(stack) :
    addr = ptlrpc.search_stack_for_reg("RDI", stack, "ptlrpc_import_recovery_state_machine")
    if addr == 0 :
        return 0

    imp = readSU("struct obd_import", addr)
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

if ( __name__ == '__main__'):
    import argparse

    parser =  argparse.ArgumentParser()
    parser.add_argument("-l","--lock", dest="lock", default = 0)
    args = parser.parse_args()

    btsl = exec_bt("bt")
    for bts in btsl :
        pid = bts.pid
        print("current pid:", pid)
        parsed = False
        for f in bts.frames:
            if f.func == "ptlrpc_import_recovery_state_machine" :
                parse_client_eviction(btsl)
                parsed = True
                break
        if not parsed :
            print(bts)
