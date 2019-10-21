# cl_io functions

from __future__ import print_function

from pykdump.API import *
from LinuxDump.BTstack import *
from LinuxDump.trees import *
import lustrelib as ll

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
try:
    lovsub_page_ops = readSymbol("lovsub_page_ops")
except:
    lovsub_page_ops = 0
osc_page_ops = readSymbol("osc_page_ops")
try:
    lov_raid0_page_ops = readSymbol("lov_raid0_page_ops")
except:
    lov_raid0_page_ops = 0
try:
    lov_comp_page_ops = readSymbol("lov_comp_page_ops")
except:
    lov_comp_page_ops = 0

lov_lu_obj_ops = readSymbol("lov_lu_obj_ops")
osc_lu_obj_ops = readSymbol("osc_lu_obj_ops")

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
          "flg:", dbits2str(oap.oap_brw_page.flag, obd_brw_flags),
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
            try:
                ccc_page = readSU("struct ccc_page", layer)
                print(prefix + "  ", "ccc", ccc_page)
            except:
                vvp_page = readSU("struct vvp_page", layer)
                print(prefix + "  ", "vvp", vvp_page)
        elif layer.cpl_ops == lovsub_page_ops :
            print(prefix + "  ", "lovsub", layer)
        elif layer.cpl_ops == osc_page_ops :
            osc_page = readSU("struct osc_page", layer)
            print(prefix + "  ", "osc", osc_page)
            print_osc_page(osc_page, prefix + "\t")
        elif layer.cpl_ops == lov_raid0_page_ops or layer.cpl_ops == lov_comp_page_ops :
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

def lu2osc_dev(d) :
    return readSU("struct osc_device", d)

def osc_export(obj) :
    return lu2osc_dev(obj.oo_cl.co_lu.lo_dev).od_exp;

def osc_cli(obj) :
    return osc_export(obj).exp_obd.u.cli;

def get_osc_objects_fromslab():
    from LinuxDump.Slab import get_slab_addrs
    try:
        (alloc, free) = get_slab_addrs("osc_object_kmem")
    except crash.error as val:
        print (val)
        return
    npages = 0
    for o in alloc:
        obj = readSU("struct osc_object", o)
        if obj.oo_npages != 0 :
            print_osc_obj("", obj)
            npages += obj.oo_npages
    print("total", npages, "pages")

def get_osc_extents_fromslab():
    from LinuxDump.Slab import get_slab_addrs
    try:
        (alloc, free) = get_slab_addrs("osc_extent_kmem")
    except crash.error as val:
        print (val)
        return
    npages = 0
    for e in alloc:
        ext = readSU("struct osc_extent", e)
        if ext.oe_nr_pages > 0 and ext.oe_nr_pages < 1000000 :
            print_osc_obj("", ext.oe_obj)
            npages += ext.oe_nr_pages
    print("total", npages, "pages")


lov_pattern_c = '''
#define LOV_PATTERN_NONE	0x000
#define LOV_PATTERN_RAID0	0x001
#define LOV_PATTERN_RAID1	0x002
#define LOV_PATTERN_MDT		0x100
#define LOV_PATTERN_CMOBD	0x200
'''
lov_pattern = CDefine(lov_pattern_c)

def print_layout_raid0(prefix, r0) :
    print(prefix, "raid0", r0)
    for i in range(r0.lo_nr) :
        print(prefix + "    ", r0.lo_sub[i])
        print_lu_obj_header(r0.lo_sub[i].lso_header.coh_lu)

def print_lov_layout_entry(prefix, le) :
    if le.lle_type == lov_pattern.LOV_PATTERN_RAID0 :
        print_layout_raid0(prefix, le.lle_raid0)
    elif le.lle_type == lov_pattern.LOV_PATTERN_MDT :
        print(prefix, le.lle_dom)
    else :
        print(prefix, le)

def print_lov_obj(prefix, lov) :
    print(prefix, "lov", lov)
    for i in range(lov.u.composite.lo_entry_count) :
        print_lov_layout_entry(prefix + "    ", lov.u.composite.lo_entries[i])

def print_osc_obj(prefix, osc) :
    print(prefix, "osc", osc, "npages", osc.oo_npages, osc_cli(osc),
          "nr_writes", osc.oo_nr_writes.counter, "nr_ios",
          osc.oo_nr_ios.counter)

def print_lu_obj(lu_obj) :
    if lu_obj.lo_ops == lov_lu_obj_ops :
        lov = readSU("struct lov_object", lu_obj)
        print_lov_obj("    ", lov)
    elif lu_obj.lo_ops == osc_lu_obj_ops :
        osc = readSU("struct osc_object", lu_obj)
        print_osc_obj("    ", osc)
    else :
        print(lu_obj)

def print_lu_obj_header(loh) :
    print(fid2str(loh.loh_fid))
    for lu_obj in readSUListFromHead(loh.loh_layers,
                                    "lo_linkage", "struct lu_object") :
        print_lu_obj(lu_obj)

def print_vvp_object(prefix, vvp) :
    print(vvp, "inode", vvp.vob_inode)
    print_lu_obj_header(vvp.vob_header.coh_lu)

def print_inode(prefix, inode) :
    lli = readSU("struct ll_inode_info", inode -
            member_offset('struct ll_inode_info', 'lli_vfs_inode'))
    print(inode, lli, lli.lli_clob.co_lu.lo_header)
    vvp_object = readSU("struct vvp_object", lli.lli_clob.co_lu.lo_header)
    print_vvp_object(prefix, vvp_object)

def get_vvp_obj_from_hash(hs) :
    off = member_offset('struct lu_object_header', 'loh_hash')
    for hn in ll.cfs_hash_get_nodes(hs) :
        vvp = readSU("struct vvp_object", hn - off)
        print_vvp_object(vvp)

if ( __name__ == '__main__'):
    import argparse

    parser =  argparse.ArgumentParser()
    parser.add_argument("-e","--env", dest="env", default = 0)
    parser.add_argument("-s","--osc_page", dest="osc", default = 0)
    parser.add_argument("-V","--vvp_object", dest="vvp_object", default = 0)
    parser.add_argument("-S","--osc_object", dest="osc_object", default = 0)
    parser.add_argument("-f","--file", dest="file", default = 0)
    parser.add_argument("-i","--inode", dest="inode", default = 0)
    parser.add_argument("-p","--page", dest="cl_page", default = 0)
    parser.add_argument("-H","--hash", dest="hash", default = 0)
    parser.add_argument("-w","--waitpages", dest="waitpages",
                        action='store_true')
    parser.add_argument("-a","--fromslab", dest="fromslab",
                        action='store_true')
    parser.add_argument("-x","--extfromslab", dest="extentfromslab",
                        action='store_true')
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
    elif args.file != 0 :
        f = readSU("struct file", int(args.file, 16))
        print_inode("", f.f_inode)
    elif args.inode != 0 :
        inode = readSU("struct inode", int(args.inode, 16))
        print_inode("", inode)
    elif args.vvp_object != 0 :
        vvp_object = readSU("struct vvp_object", int(args.vvp_object, 16))
        print_vvp_object("", vvp_object)
    elif args.osc_object != 0 :
        osc_object = readSU("struct osc_object", int(args.osc_object, 16))
        print_osc_obj("", osc_object)
        if osc_object.oo_npages == 1 :
            osc_page = readSU("struct osc_page", osc_object.oo_tree.rnode)
            print_osc_page(osc_page, "    ")
        else :
            for p in walk_page_tree(osc_object.oo_tree) :
                osc_page = readSU("struct osc_page", p)
                print_osc_page(osc_page, "    ")
    elif args.hash != 0 :
        hs = readSU("struct cfs_hash", int(args.hash, 16))
        get_vvp_obj_from_hash(hs)
    elif args.fromslab != 0 :
        get_osc_objects_fromslab()
    elif args.extentfromslab != 0 :
        get_osc_extents_fromslab()
    elif args.waitpages != 0 :
        print_waiting_pages()

