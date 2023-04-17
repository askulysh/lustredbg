# cl_io functions

from __future__ import print_function

from pykdump.API import *
from LinuxDump.BTstack import *
from LinuxDump.trees import *
from LinuxDump.KernLocks import *
from LinuxDump.fs.dcache import *
import LinuxDump.fregsapi
import obd as obd
from ptlrpc import *
import lustrelib as ll

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
mdc_lu_obj_ops = readSymbol("mdc_lu_obj_ops")

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
    try :
        index = osc_page.ops_cl.cpl_page.cp_osc_index
    except:
        index = osc_page.ops_cl.cpl_index
    oap = osc_page.ops_oap
    print(prefix, # osc_page,
          "idx:", index,
          "cmd:", dbits2str(oap.oap_cmd, obd_brw_flags),
          "flg:", dbits2str(oap.oap_brw_page.flag, obd_brw_flags),
          "off:", oap.oap_obj_off, oap.oap_brw_page.pg)
    if oap.oap_request != 0 :
       show_ptlrpc_request(oap.oap_request)
    else :
        print(prefix, oap.oap_request)

def print_page_slice(layer, prefix) :
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

def print_cl_page(cl, prefix):
    try :
        page_state = cl_page_state.__getitem__(cl.cp_state)
        page_type = cl_page_type.__getitem__(cl.cp_type)
    except :
        page_type ="unknown"
        page_state ="unknown"
    print(prefix, cl, "state: ", page_state, "type:",  page_type, cl.cp_vmpage)
    try:
        for i in range(cl.cp_layer_count) :
            # struct_size("struct cl_page")
            a = Addr(cl) + struct_size("struct cl_page") + cl.cp_layer_offset[i]
            layer = readSU("struct cl_page_slice", a)
            print_page_slice(layer, prefix)
    except:
        for layer in readSUListFromHead(cl.cp_layers, "cpl_linkage",
                "struct cl_page_slice") :
            print_page_slice(layer, prefix)


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
    return lu2osc_dev(obj.oo_cl.co_lu.lo_dev).osc_exp;

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

def print_layout_raid0(prefix, ext, r0) :
    print(prefix, ext, "raid0", r0, r0.lo_nr)
    for i in range(r0.lo_nr) :
        print(prefix + "    ", r0.lo_sub[i])
        print_lu_obj_header(prefix + "    ", r0.lo_sub[i].lso_header.coh_lu)

def lu_ext2str(ext) :
    if ext.e_end == 0xffffffffffffffff :
        return "%u - EOF" % ext.e_start
    else :
        return "%u - %u" % (ext.e_start, ext.e_end)

def print_lov_layout_entry(prefix, le) :
    if le.lle_type == lov_pattern.LOV_PATTERN_RAID0 :
        print_layout_raid0(prefix, lu_ext2str(le.lle_extent), le.lle_raid0)
    elif le.lle_type == lov_pattern.LOV_PATTERN_MDT :
        print(prefix, lu_ext2str(le.lle_extent), le.lle_dom)
        print_lu_obj_header(prefix, le.lle_dom.lo_dom.lso_header.coh_lu)
    else :
        print(prefix, lu_ext2str(le.lle_extent), le)

def print_lov_obj(prefix, lov) :
    print(prefix, "lov", lov)
    try:
        print(prefix, "mirrors", lov.u.composite.lo_mirror_count, "flags",
                lov.u.composite.lo_flags)
        for i in range(lov.u.composite.lo_mirror_count) :
            lre = lov.u.composite.lo_mirrors[i]
            print(prefix, "mirror[", i,"] id:", lre.lre_mirror_id,  " valid:",
                    lre.lre_valid)
            for j in range(lre.lre_start, lre.lre_end + 1) :
                print_lov_layout_entry(prefix + "    ",
                        lov.u.composite.lo_entries[j])
    except:
        for i in range(lov.u.composite.lo_entry_count) :
            print_lov_layout_entry(prefix + "    ", lov.u.composite.lo_entries[i])

def print_osc_obj(prefix, osc) :
    print(prefix, osc, "npages", osc.oo_npages, osc_cli(osc),
          "nr_writes", osc.oo_nr_writes.counter, "nr_ios",
          osc.oo_nr_ios.counter)
    show_import(prefix, osc_cli(osc).cl_import)

def print_lu_obj(prefix, lu_obj) :
    if lu_obj.lo_ops == lov_lu_obj_ops :
        lov = readSU("struct lov_object", lu_obj)
        print_lov_obj(prefix + "    ", lov)
    elif lu_obj.lo_ops == osc_lu_obj_ops or lu_obj.lo_ops == mdc_lu_obj_ops :
        osc = readSU("struct osc_object", lu_obj)
        print_osc_obj(prefix + "    ", osc)
    else :
        print(prefix, lu_obj)

def print_lu_obj_header(prefix, loh) :
    print(prefix, obd.fid2str(loh.loh_fid))
    for lu_obj in readSUListFromHead(loh.loh_layers,
                                    "lo_linkage", "struct lu_object") :
        print_lu_obj(prefix, lu_obj)

def print_vvp_object(prefix, vvp) :
    print(vvp, "inode", vvp.vob_inode)
    print_lu_obj_header("", vvp.vob_header.coh_lu)

def osc2vvp(osc) :
    lovsub = readSU("struct lovsub_object", Addr(osc.oo_cl.co_lu.lo_header))
    return readSU("struct vvp_object", lovsub.lso_header.coh_parent)

def print_lsm(prefix, lsm) :
        print(prefix, lsm)
        print(prefix, "stripe cnt", lsm.lsm_md_stripe_count,
              "master MDT", lsm.lsm_md_master_mdt_index,
              "hash type", lsm.lsm_md_hash_type);
        for i in range(lsm.lsm_md_stripe_count) :
            oi = lsm.lsm_md_oinfo[i]
            print(prefix, "  stripe[%d] %s MDS %d %s" %
                    (i, obd.fid2str(oi.lmo_fid), oi.lmo_mds, oi.lmo_root))

def print_inode(prefix, inode) :
    lli = readSU("struct ll_inode_info", inode -
            member_offset('struct ll_inode_info', 'lli_vfs_inode'))
    try :
        inode_lock = inode.i_mutex
    except :
        inode_lock = inode.i_rwsem
    print(inode, inode_lock, lli, obd.fid2str(lli.lli_fid), lli.lli_clob)
    if S_ISDIR(inode.i_mode) and lli.lli_lsm_md != 0 :
        print_lsm(prefix + '   ', lli.lli_lsm_md)

    if lli.lli_clob :
        vvp_object = readSU("struct vvp_object", lli.lli_clob.co_lu.lo_header)
        print_vvp_object(prefix, vvp_object)

def get_vvp_obj_from_hash(hs) :
    off = member_offset('struct lu_object_header', 'loh_hash')
    for hn in ll.cfs_hash_get_nodes(hs) :
        vvp = readSU("struct vvp_object", hn - off)
        print_vvp_object("", vvp)

def print_osc_extent(prefix, ext) :
    print(prefix, ext, "state", ext.oe_state, "npages", ext.oe_nr_pages,
          ext.oe_dlmlock)
    off = member_offset('struct osc_page', 'ops_oap')
    for oap in readSUListFromHead(ext.oe_pages, "oap_pending_item",
                                  "struct osc_async_page") :
        osc_page = readSU("struct osc_page", oap - off)
        print_osc_page(osc_page, "")

from crash import mem2long

def ffs(x):
    """Returns the index, counting from 1, of the
    least significant set bit in `x`.
    """
    return (x&-x).bit_length()

RADIX_TREE_MAP_SIZE = None
RADIX_TREE_HEIGHT_MASK = None

_rnode = "struct radix_tree_node"
try:
    ti = getStructInfo(_rnode)["slots"].ti
    RADIX_TREE_MAP_SIZE = ti.dims[0]
    RADIX_TREE_MAP_MASK = RADIX_TREE_MAP_SIZE - 1
    RADIX_TREE_MAP_SHIFT = ffs(RADIX_TREE_MAP_SIZE) - 1
    RADIX_TREE_INDIRECT_PTR = 1
    height_to_maxindex = readSymbol("height_to_maxindex")
    # Are we on a kernel with 'radix_tree_node.path'?
    if (member_size(_rnode, "path") != -1):
            # Yes, we are
            RADIX_TREE_MAX_PATH = len(height_to_maxindex)-1
            RADIX_TREE_HEIGHT_SHIFT = RADIX_TREE_MAX_PATH + 1
            RADIX_TREE_HEIGHT_MASK = (1 << RADIX_TREE_HEIGHT_SHIFT) - 1
except:
    pass

def radix_tree_is_indirect_ptr(addr):
    return (long(addr) & RADIX_TREE_INDIRECT_PTR)

def indirect_to_ptr(ptr):
    return (long(ptr) & ~RADIX_TREE_INDIRECT_PTR)

def walk_page_tree2(ptree):
    first_rnode = readSU(_rnode, indirect_to_ptr(ptree.rnode))
    if (not first_rnode):
        return []
    if not radix_tree_is_indirect_ptr(ptree.rnode) :
        return [ptree.rnode]

    _offset = member_offset(_rnode, "slots")
    _size = RADIX_TREE_MAP_SIZE * pointersize

    _addrs = set()
    def walk_radix_node(rnode):
        arr = mem2long(readmem(rnode+_offset, _size),
                       array=RADIX_TREE_MAP_SIZE)
        #for i, s in enumerate(rnode.slots):
        for i, s in enumerate(arr):
            if (not s):
                continue
            if not radix_tree_is_indirect_ptr(s) :
                yield s
            else:
                for s1 in walk_radix_node(indirect_to_ptr(s)):
                    yield s1
    return walk_radix_node(long(first_rnode))

if ( __name__ == '__main__'):
    import argparse

    parser =  argparse.ArgumentParser()
    parser.add_argument("-e","--env", dest="env", default = 0)
    parser.add_argument("-p","--page", dest="page", default = 0)
    parser.add_argument("-c","--cl_page", dest="cl_page", default = 0)
    parser.add_argument("-s","--osc_page", dest="osc", default = 0)
    parser.add_argument("-E","--extent", dest="ext", default = 0)
    parser.add_argument("-V","--vvp_object", dest="vvp_object", default = 0)
    parser.add_argument("-S","--osc_object", dest="osc_object", default = 0)
    parser.add_argument("-l","--ldlm_lock", dest="ldlm_lock", default = 0)
    parser.add_argument("-f","--file", dest="file", default = 0)
    parser.add_argument("-i","--inode", dest="inode", default = 0)
    parser.add_argument("-d","--dentry", dest="dentry", default = 0)
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
    elif args.page != 0 :
        page = readSU("struct page", int(args.page, 16))
        cl_page = readSU("struct cl_page", page.private)
        print_cl_page(cl_page, "")
    elif args.cl_page != 0 :
        cl_page = readSU("struct cl_page", int(args.cl_page, 16))
        print_cl_page(cl_page, "")
    elif args.file != 0 :
        f = readSU("struct file", int(args.file, 16))
        print_dentry(f.f_path.dentry)
        print_inode("", f.f_inode)
    elif args.inode != 0 :
        inode = readSU("struct inode", int(args.inode, 16))
        print_inode("", inode)
    elif args.dentry != 0 :
        dentry = readSU("struct dentry", int(args.dentry, 16))
        print_dentry(dentry)
        print_inode("", dentry.d_inode)
    elif args.vvp_object != 0 :
        vvp_object = readSU("struct vvp_object", int(args.vvp_object, 16))
        print_vvp_object("", vvp_object)
    elif args.osc_object != 0 :
        osc_object = readSU("struct osc_object", int(args.osc_object, 16))
        print_osc_obj("", osc_object)
        for p in walk_page_tree2(osc_object.oo_tree) :
            osc_page = readSU("struct osc_page", p)
            print_osc_page(osc_page, "    ")
    elif args.ext != 0 :
        ext = readSU("struct osc_extent", int(args.ext, 16))
        print_osc_extent("", ext)
    elif args.ldlm_lock != 0 :
        lock = readSU("struct ldlm_lock", int(args.ldlm_lock, 16))
        if lock.l_ast_data != 0:
            osc_obj = readSU("struct osc_object", lock.l_ast_data)
            print_vvp_object("", osc2vvp(osc_obj))
    elif args.hash != 0 :
        hs = readSU("struct cfs_hash", int(args.hash, 16))
        get_vvp_obj_from_hash(hs)
    elif args.fromslab != 0 :
        get_osc_objects_fromslab()
    elif args.extentfromslab != 0 :
        get_osc_extents_fromslab()
    elif args.waitpages != 0 :
        print_waiting_pages()

