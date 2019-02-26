# cl_io functions

from __future__ import print_function

from pykdump.API import *
from LinuxDump.BTstack import *

import fregsapi

cl_page_state_c = '''
enum cl_page_state {
        CPS_CACHED,
        CPS_OWNED,
        CPS_PAGEOUT,
        CPS_PAGEIN,
        CPS_FREEING,
        CPS_NR
};
'''
cl_page_state = CEnum(cl_page_state_c)

obd_brw_flags_c = '''
#define OBD_BRW_READ            0x01
#define OBD_BRW_WRITE           0x02
#define OBD_BRW_SYNC            0x08
#define OBD_BRW_CHECK           0x10
#define OBD_BRW_FROM_GRANT      0x20
#define OBD_BRW_GRANTED         0x40
#define OBD_BRW_NOCACHE         0x80
#define OBD_BRW_NOQUOTA        0x100
#define OBD_BRW_SRVLOCK        0x200
#define OBD_BRW_ASYNC          0x400
#define OBD_BRW_MEMALLOC       0x800
#define OBD_BRW_OVER_USRQUOTA 0x1000
#define OBD_BRW_OVER_GRPQUOTA 0x2000
#define OBD_BRW_SOFT_SYNC     0x4000
#define OBD_BRW_OVER_PRJQUOTA 0x8000
'''
obd_brw_flags = CDefine(obd_brw_flags_c)

cl_page_type_c = '''
enum cl_page_type {
        CPT_CACHEABLE = 1,
        CPT_TRANSIENT
};
'''
cl_page_type = CEnum(cl_page_type_c)

vvp_page_ops = readSymbol("vvp_page_ops")
vvp_transient_page_ops = readSymbol("vvp_transient_page_ops")
#lov_comp_page_ops = readSymbol("lov_comp_page_ops")
lovsub_page_ops = readSymbol("lovsub_page_ops")
osc_page_ops = readSymbol("osc_page_ops")
try:
    lov_raid0_page_ops = readSymbol("lov_raid0_page_ops")
except:
    lov_raid0_page_ops = 0

def vvp_env_io(env) :
    vvp_session_key = readSymbol("vvp_session_key")
    v = env.le_ses.lc_value[vvp_session_key.lct_index]
    return readSU("struct vvp_session", v).cs_ios

def osc_env_io(env) :
    session_key = readSymbol("osc_session_key")
    v = env.le_ses.lc_value[session_key.lct_index]
    return readSU("struct osc_session", v).os_io

def ll_env_info(env) :
    ll_thread_key = readSymbol("ll_thread_key")
    v = env.le_ctx.lc_value[ll_thread_key.lct_index]
    return readSU("struct ll_thread_info", v)

def page_list_sanity_check(obj, queue) :
    pages = readSUListFromHead(queue.pl_pages, "cp_batch", "struct cl_page")
    for p in pages :
        print_cl_page(p, "")
        vvp_page = readSU("struct vvp_page", (int)(p) + 80)
        print("vm: %x %x idx: %d" % (p.cp_vmpage, vvp_page.vpg_page,
            vvp_page.vpg_cl.cpl_index))

def print_osc_page(osc_page, prefix) :
    oap = osc_page.ops_oap
    print(prefix, # osc_page,
          "idx:", osc_page.ops_cl.cpl_index,
          "cmd:", dbits2str(oap.oap_cmd, obd_brw_flags),
          "off:", oap.oap_obj_off, oap.oap_brw_page.pg)
    if oap.oap_request != 0 :
       show_ptlrpc_request(oap.oap_request)
    else :
        print(prefix, oap.oap_request)

def print_cl_page(cl, prefix):
    print(prefix, cl, "state: ", cl_page_state.__getitem__(cl.cp_state),
          "type:",  cl_page_type.__getitem__(cl.cp_type),
          cl.cp_vmpage)

    for layer in readSUListFromHead(cl.cp_layers, "cpl_linkage",
            "struct cl_page_slice") :
        if layer.cpl_ops == vvp_page_ops :
            ccc_page = readSU("struct ccc_page", layer)
            print(prefix + "  ", "ccc", ccc_page)
        elif layer.cpl_ops == lovsub_page_ops :
            print(prefix + "  ", "lovsub", layer)
        elif layer.cpl_ops == osc_page_ops :
            osc_page = readSU("struct osc_page", layer)
            print(prefix + "  ", "osc", osc_page)
            print_osc_page(osc_page, prefix + "\t")
        elif layer.cpl_ops == lov_raid0_page_ops :
            lov_page = readSU("struct lov_page", layer)
            print(prefix + "  ", "lov", lov_page)
        else :
            print("unknown layer", layer, layer.cpl_ops)

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

def print_waiting_pages() :
    (funcpids, functasks, alltaskaddrs) = get_threads_subroutines_slow()
    waiting_pids = funcsMatch(funcpids, "__wait_on_bit_lock")
    for pid in waiting_pids :
        print(pid)
        addr = search_for_reg("RSI", pid, "cl_lock_state_wait")
        cl_lock = readSU("struct cl_lock", addr)
        print_cl_lock(cl_lock, "")

if ( __name__ == '__main__'):
    import argparse

    parser =  argparse.ArgumentParser()
    parser.add_argument("-e","--env", dest="env", default = 0)
    parser.add_argument("-s","--osc", dest="osc", default = 0)
    parser.add_argument("-p","--page", dest="cl_page", default = 0)
    args = parser.parse_args()
    if args.env != 0 :
        env = readSU("struct lu_env", int(args.env, 16))
        vio = vvp_env_io(env)
        print(vio)
        print(osc_env_io(env))
#        print(ll_env_info(env))
#        queue = vio.u.write.vui_queue
#        print(queue)
#        page_list_sanity_check(0, queue)
    elif args.osc != 0 :
        osc_page = readSU("struct osc_page", int(args.osc, 16))
        print_osc_page(osc_page, "")
    elif args.cl_page != 0 :
        cl_page = readSU("struct cl_page", int(args.cl_page, 16))
        print_cl_page(cl_page, "")
    else :
        print_waiting_pages()

