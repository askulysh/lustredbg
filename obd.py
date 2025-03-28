# obd functions

from __future__ import print_function

from pykdump.API import *
import lustrelib as ll
import ptlrpc as ptlrpc

lu_object_header_attr_c = '''
#define LOHA_EXISTS             1
#define LOHA_REMOTE             2
#define LOHA_HAS_AGENT_ENTRY    4
'''
lu_object_header_attr = CDefine(lu_object_header_attr_c)

class Fid:
    def __init__(self, desc):
        a = desc.split(':')
        self.f_seq = int(a[0], 16)
        self.f_oid = int(a[1], 16)
        self.f_ver = int(a[2], 16)

def fid_flatten32(fid) :
    FID_SEQ_START = 0x200000000
    seq = fid.f_seq - FID_SEQ_START
    ino = ((seq & 0x000fffff) << 12) + ((seq >> 8) & 0xfffff000) + (seq >> (64
        - (40-8)) & 0xffffff00) + (fid.f_oid & 0xff000fff) + ((fid.f_oid &
            0x00fff000) << 8)
    return ino

def fid2str(fid) :
    if fid == 0 :
        return "[0x0:0x0:0x0]"
    else :
        return "[0x%x:0x%x:0x%x]" % (fid.f_seq, fid.f_oid, fid.f_ver)

def is_dir(attr) :
    return attr & 0xf000 == 0x4000

def attr2str(attr) :
    ret = dbits2str(attr & 7, lu_object_header_attr)
    if is_dir(attr) :
        ret = ret +"|S_IFDIR"
    elif attr & 0xf000 == 0x2000 :
        ret = ret +"|S_IFCHR"
    elif attr & 0xf000 == 0x6000 :
        ret = ret +"|S_IFBLK"
    elif attr & 0xf000 == 0x8000 :
        ret = ret +"|S_IFREG"
    elif attr & 0xf000 == 0x1000 :
        ret = ret +"|S_IFIFO"
    elif attr & 0xf000 == 0xa000 :
        ret = ret +"|S_IFLKN"
    return ret

def print_loh(loh, prefix):
    print(prefix, "%s %s flags: %x attr 0%o %s" % (loh, fid2str(loh.loh_fid),
                                                   loh.loh_flags, loh.loh_attr,
                                                   attr2str(loh.loh_attr)))

def fid_be2str(f) :
    seq = (f[0]<<56)|(f[1]<<48)|(f[2]<<40)|(f[3]<<32)|(f[4]<<24)|(f[5]<<16)|(f[6]<<8)|f[7]
    oid = (f[8]<<24)|(f[9]<<16)|(f[10]<<8)|f[11]
    ver = (f[12]<<24)|(f[13]<<16)|(f[14]<<8)|f[15]
    return "[0x%x:0x%x:0x%x]" % (seq, oid, ver)

def hash_long(val, bits) :
    CFS_GOLDEN_RATIO_PRIME_64 = 0x9e37fffffffc0001
    h = val & 0xffffffffffffffff
    h *= CFS_GOLDEN_RATIO_PRIME_64
    h = h & 0xffffffffffffffff
    return (h >> (64 - bits))

def CFS_HASH_NBKT(hs) :
    return 1 << (hs.hs_cur_bits - hs.hs_bkt_bits)

def lu_obj_hop_hash(hs, fid, mask) :
    h = fid_flatten32(fid)
    h = h & 0xffffffffffffffff
    h += (h >> 4) + (h << 12) 
    h = h & 0xffffffff
    h = hash_long(h, hs.hs_bkt_bits)
    h = h & 0xffffffffffffffff
    h -= hash_long(hs & 0xffffffffffffffff, (fid.f_oid % 11) + 3)
    h = h & 0xffffffffffffffff
    h <<= hs.hs_cur_bits - hs.hs_bkt_bits;
    h |= (fid.f_seq + fid.f_oid) & (CFS_HASH_NBKT(hs) - 1)

    return h & mask

def cfs_hash_bd_from_key(hs, bkts, bits, key) :
    index = lu_obj_hop_hash(hs, key, (1 << bits) - 1)
    bd_bucket = bkts[index & ((1 << (bits - hs.hs_bkt_bits)) - 1)]
    bd_offset = index >> (bits - hs.hs_bkt_bits)
    return (bd_bucket, bd_offset)

def hash_for_each_hd(hs, func) :
    buckets = hs.hs_buckets
    bucket_num = 1 << (hs.hs_cur_bits - hs.hs_bkt_bits)
    hhead_size = 8
    for ix in range(0, bucket_num) :
        bd = buckets[ix]
        if bd != 0 :
            if bd.hsb_count == 0 :
                continue
            print(bd, "count", bd.hsb_count)
            a = int(bd.hsb_head)
            for offset in range(0, 1 << hs.hs_bkt_bits) :
                hlist = readSU("struct hlist_head", a + hhead_size*offset)
                if hlist.first != 0 :
                    print("off", offset, hlist)
                    head = hlist.first

                    while head != 0 :
                        func(head)
                        head = head.next

def hash_for_each_hd2(hs, func) :
    for hn in ll.cfs_hash_get_nodes(hs) :
        func(hn)

def loh_cmp_fid(loh, fid) :
    return loh.loh_fid.f_seq == fid.f_seq and loh.loh_fid.f_oid == fid.f_oid and loh.loh_fid.f_ver == fid.f_ver

def cfs_hash_32(val, bits) :
    GOLDEN_RATIO_32 = 0x61C88647
    return (val * GOLDEN_RATIO_32) >> (32 - bits)

def cfs_hash_64(val, bits) :
    GOLDEN_RATIO_64 = 0x61C8864680B583EB
    return val * GOLDEN_RATIO_64 >> (64 - bits)

def lu_fid_hash(fid, seed) :
    seed = cfs_hash_32(seed ^ fid.f_oid, 32)
    seed ^= cfs_hash_64(fid.f_seq, 32)
    return seed

def lu_bkt_hash(s, fid) :
    return lu_fid_hash(fid, s.ls_bkt_seed) & (s.ls_bkt_cnt - 1)

def rht_bucket(tbl, i) :
    return tbl.buckets[i]
    #    return readSU("struct rhash_head", tbl.buckets+i*8)

def get_rhashtable_nodes(ht) :
    off = member_offset('struct lu_object_header', 'loh_hash')
    for i in range(ht.tbl.size) :
        pos = readSU('struct rhash_head', ht.tbl.buckets[i])
        while pos != 0 and pos&1 == 0 :
            yield pos
            pos = pos.next

def get_rhashtable_objs(ht) :
    off = member_offset('struct lu_object_header', 'loh_hash')
    for n in get_rhashtable_nodes(ht) :
        yield readSU("struct lu_object_header", n - off)

def rhashtable_lookup(ht, key) :
    for loh in get_rhashtable_objs(ht) :
        if loh_cmp_fid(loh, key) :
            return loh
    return None

def lu_object_find_rh(dev, fid) :
    s  = dev.ld_site
    hs = s.ls_obj_hash
#    bkt = s.ls_bkts[lu_bkt_hash(s, fid)]
    return rhashtable_lookup(hs, fid)

def lu_object_find_cfs_hash(dev, fid) :
    hs = dev.ld_site.ls_obj_hash
    (bd_bucket, bd_offset) = (cfs_hash_bd_from_key(hs, hs.hs_buckets,
                              hs.hs_cur_bits, fid))
    try :
        dep = readSU("cfs_hash_head_dep_t", bd_bucket.hsb_head + 16*bd_offset)
    except:
        dep = readSU("struct cfs_hash_head_dep", bd_bucket.hsb_head + 16*bd_offset)
    head = dep.hd_head.first
    off = member_offset('struct lu_object_header', 'loh_hash')
    while head != 0 :
        loh = readSU("struct lu_object_header", head - off)
        if loh_cmp_fid(loh, fid) :
               break
        head = head.next
    if head == 0 :
        print("Can't find fid !")
        return 0
    return loh

def lu_object_find(dev, fid) :
    if symbol_exists("obj_hash_params"):
        return lu_object_find_rh(dev, fid)
    else :
        return lu_object_find_cfs_hash(dev, fid)

def lu_object_find_by_objid(dev, objid) :
    hs = dev.ld_site.ls_obj_hash
    if symbol_exists("obj_hash_params"):
        gen = get_rhashtable_nodes(hs)
    else :
        gen = ll.cfs_hash_get_nodes(hs)
    off = member_offset('struct lu_object_header', 'loh_hash')
    for hn in gen :
        loh = readSU("struct lu_object_header", hn - off)
        if loh.loh_fid.f_oid == objid :
            print_loh(loh, "")
            return loh
    return None

def fld_lookup(fld, seq) :
    fld_cache_entries = readSUListFromHead(fld.lsf_cache.fci_entries_head,
                "fce_list", "struct fld_cache_entry")
    for flde in fld_cache_entries :
        print("0x%x-0x%x %d" % (flde.fce_range.lsr_start,
                flde.fce_range.lsr_end, flde.fce_range.lsr_flags))

def show_obd(dev) :
    print("0x%x %036s 0x%016x %01d   %01d   %01d   %01d   %01d   "
          "%01d   %01d   %01d  %03d/%03d %03d/%03d %d %d %d" %
          (dev, dev.obd_name, dev.obd_lu_dev, dev.obd_inactive,
           dev.obd_starting, dev.obd_attached, dev.obd_set_up,
           dev.obd_stopping, dev.obd_force, dev.obd_fail, dev.obd_recovering,
           dev.u.cli.cl_r_in_flight, dev.u.cli.cl_max_rpcs_in_flight,
           dev.u.cli.cl_w_in_flight, dev.u.cli.cl_max_rpcs_in_flight,
           dev.u.cli.cl_pending_r_pages.counter,
           dev.u.cli.cl_pending_w_pages.counter,
           dev.obd_num_exports))

def xarray_entry(xarray, index):
    node = xarray.xa_head
    if (not (long(node) & 2)):
        if index:
            return 0
        else:
            return node
    node = readSU("struct xa_node", node & ~3)
    if ((index >> node.shift) > 63):
        #raise IndexError('index bigger than xarray')
        return 0
    while (node):
        offset = (index >> node.shift) & 63
        node = node.slots[offset]
        if (not node or not (long(node) & 2)):
                return node
        node = readSU("struct xa_node", node & ~3)

def all_obds() :
    obd_devs = readSymbol("obd_devs")
    for i in range(0, 8192) :
        try :
            e = xarray_entry(obd_devs, i)
            if e :
                yield readSU("struct obd_device", e)
        except :
            if obd_devs[i] != 0 :
                yield obd_devs[i]

def show_obds() :
    print("        obd_device               name \t\t\t   lu_dev   \t  "
          "ina sta att set sto "
          "for fai rec r_inf w_inf")
    for d in all_obds() :
        show_obd(d)

def show_imports() :
    for obd in all_obds() :
        if obd and obd.obd_lu_dev and obd.u.cli.cl_import :
            ptlrpc.show_import("", obd.u.cli.cl_import)

__re_search = re.compile(r'^([a-f0-9]+):')
__re_kmem = re.compile(r'^([a-f0-9]+)\s([a-z_0-9-]+)')
def ptr_search(ptr) :
    res = exec_crash_command("search 0x%x" % ptr)
    if len(res) == 0 :
        print("no matches!")
        return

    for s in res.splitlines():
        m = __re_search.match(s)
        if (m) :
            addr = int(m.group(1), 16)
            print("addr: 0x%x" % addr)
            res2 = exec_crash_command("kmem 0x%x" % addr)
            lines = res2.splitlines()
            m2 = __re_kmem.match(lines[1])
            if (m2) :
                print(m2.group(2), lines[5])
            else :
                print(res2)
        else :
            print(s)

HANDLE_HASH_SIZE = 1 << 16
HANDLE_HASH_MASK = HANDLE_HASH_SIZE - 1

def class_handle2object(cookie) :
    handle_hash = readSymbol("handle_hash")
    bucket = handle_hash + (cookie & HANDLE_HASH_MASK);
    entries = readSUListFromHead(bucket.head, "h_link", "struct portals_handle")
    for e in entries :
        if cookie == e.h_cookie :
            return e

    return 0

def lprocfs_stats_counter_get(stats, cpuid, index) :
    cntr = stats.ls_percpu[cpuid].lp_cntr[index]
    if stats.ls_flags & 0x0002 != 0 :
        c = Addr(cntr) + index * 8
        cntr = readSU("struct lprocfs_counter", c)

    return cntr

def stats_couter_sum(stats, idx) :
    sum = 0
    for i in range(0, stats.ls_biggest_alloc_num) :
        if stats.ls_percpu[i] == 0 :
            continue
        cntr = lprocfs_stats_counter_get(stats, i, idx)
        try :
            sum = sum + cntr.lc_array_sum
            if stats.ls_flags & 0x0002 != 0 :
                sum = sum + readS64(Addr(cntr)+5*8)
        except:
            sum = sum + cntr.lc_sum

    return sum

def obd_memory_sum() :
    return stats_couter_sum(readSymbol("obd_memory"), 0)

if ( __name__ == '__main__'):
    import argparse

    parser =  argparse.ArgumentParser()
    parser.add_argument("-d","--device", dest="device",
                        default=0)
    parser.add_argument("-f","--fid", dest="fid",
                        default=0)
    parser.add_argument("-F","--fid_str", dest="fid_str",
                        default="")
    parser.add_argument("-s","--search", dest="search_ptr",
                        default=0)
    parser.add_argument("-l","--fld_lookup", dest="seq",
                        default=0)
    parser.add_argument("-H","--hash", dest="hash", default=0)
    parser.add_argument("-c","--cookie", dest="cookie", default=0)
    parser.add_argument("-o","--objid", dest="objid", default=0)
    parser.add_argument("-p","--lprocfs_stats", dest="lprocfs_stats", default=0)
    parser.add_argument("-m","--mem", dest="meminfo", action='store_true')
    parser.add_argument("-i","--show_imports", dest="show_imports", action='store_true')
    args = parser.parse_args()

    if args.device != 0 :
        lu_dev = readSU("struct lu_device", int(args.device, 16))

    if args.fid != 0 :
        fid = readSU("struct lu_fid", int(args.fid, 16))
        mdt_obj = lu_object_find(lu_dev, fid)
        print(mdt_obj)
    elif args.fid_str != "" :
        fid = Fid(args.fid_str)
        if args.device != 0 :
            loh = lu_object_find(lu_dev, fid)
            print(loh)
        else :
            for obd in all_obds() :
                if obd.obd_lu_dev == 0 or obd.obd_lu_dev.ld_site == 0 :
                    continue
                loh = lu_object_find(obd.obd_lu_dev, fid)
                print(obd.obd_name, obd, loh)
    elif args.objid != 0 :
        objid = int(args.objid, 16)
        if args.device != 0 :
            lu_object_find_by_objid(lu_dev, objid)
        else :
            for obd in all_obds() :
                if obd.obd_lu_dev == 0 or obd.obd_lu_dev.ld_site == 0 :
                    continue
                loh = lu_object_find_by_objid(obd.obd_lu_dev, objid)
                if loh :
                    print(obd.obd_name, obd, loh)
    elif args.seq != 0 :
        fld_lookup(lu_dev.ld_site.ld_seq_site.ss_server_fld, int(args.seq, 16))
    elif args.search_ptr != 0 :
        ptr_search(int(args.search_ptr, 16))
    elif args.hash != 0 :
        hs = readSU("struct cfs_hash", int(args.hash, 16))
        hash_for_each_hd2(hs, print)
    elif args.cookie != 0 :
        print(class_handle2object(int(args.cookie, 16)))
    elif args.lprocfs_stats :
        stats = readSU("struct lprocfs_stats", int(args.lprocfs_stats, 16))
        print("Sum:",stats_couter_sum(stats, 0))
    elif args.meminfo :
        try :
            libcfs_kmem = readSymbol("libcfs_kmem")
        except:
            libcfs_kmem = readSymbol("libcfs_kmemory")
        print("libcfs_kmemory %uk obd_max_alloc %uk obd_memory %uk" %
                (libcfs_kmem.counter/1024,
                 readSymbol("obd_max_alloc")/1024, obd_memory_sum()/1024))
    elif args.show_imports :
        show_imports()
    else :
        show_obds()

