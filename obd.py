# obd functions

from __future__ import print_function

from pykdump.API import *

def fid_flatten32(fid) :
    FID_SEQ_START = 0x200000000
    seq = fid.f_seq - FID_SEQ_START
    ino = ((seq & 0x000fffff) << 12) + ((seq >> 8) & 0xfffff000) + (seq >> (64
        - (40-8)) & 0xffffff00) + (fid.f_oid & 0xff000fff) + ((fid.f_oid &
            0x00fff000) << 8)
    return ino

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
    print(bd_bucket)
    print(bd_offset)
    return (bd_bucket, bd_offset)

def hash_for_each_hd(hs, func) :
    buckets = hs.hs_buckets
    bucket_num = 1 << (hs.hs_cur_bits - hs.hs_bkt_bits)
    for ix in range(0, bucket_num) :
        bd = buckets[ix]
        if bd != 0 :
            if bd.hsb_count == 0 :
                continue
            print(bd, bd.hsb_count)
            a = int(bd.hsb_head)
            for offset in range(0, 1 << hs.hs_bkt_bits) :
                dep = readSU("cfs_hash_head_dep_t", a + 16*offset)
                hlist = dep.hd_head
                if hlist.first != 0 :
                    print(offset)
                    func(hlist)

def walk_hash2(hlist) :
    print(hlist)
    head = hlist.first

    while head != 0 :
        print(head)
        head = head.next

def lu_object_find(dev, fid) :
    hs = dev.ld_site.ls_obj_hash
    print(hs)
#    hash_for_each_hd(hs, walk_hash2)
    (bd_bucket, bd_offset) = (cfs_hash_bd_from_key(hs, hs.hs_buckets,
                              hs.hs_cur_bits, fid))
    try :
        dep = readSU("cfs_hash_head_dep_t", bd_bucket.hsb_head + 16*bd_offset)
    except:
        dep = readSU("cfs_hash_head_dep", bd_bucket.hsb_head + 16*bd_offset)
    print(dep)
    head = dep.hd_head.first
    while head != 0 :
        print(head)
        mdt_object = readSU("struct mdt_object", head - 0x20)
        if mdt_object.mot_header.loh_fid.f_seq == fid.f_seq and mdt_object.mot_header.loh_fid.f_oid == fid.f_oid and mdt_object.mot_header.loh_fid.f_ver == fid.f_ver :
               break
        head = head.next
    if head == 0 :
        print("Can't find fid !")
        return 0
    print(mdt_object)
    return mdt_object.mot_obj

def show_obd(dev) :
    print("0x%x %036s 0x%016x %01d   %01d   %01d   %01d   %01d   "
          "%01d   %01d  %02d/%02d %02d/%02d %d %d" %
          (dev, dev.obd_name, dev.obd_lu_dev, dev.obd_inactive,
           dev.obd_starting, dev.obd_attached, dev.obd_set_up,
           dev.obd_stopping, dev.obd_force, dev.obd_fail,
           dev.u.cli.cl_r_in_flight, dev.u.cli.cl_max_rpcs_in_flight,
           dev.u.cli.cl_w_in_flight, dev.u.cli.cl_max_rpcs_in_flight,
           dev.u.cli.cl_pending_r_pages.counter,
           dev.u.cli.cl_pending_w_pages.counter))

def show_obds() :
    obd_devs = readSymbol("obd_devs")
    print("        obd_device               name \t\t\t   lu_dev   \t  "
          "ina sta att set sto "
          "for fai r_inf w_inf")
    for i in range(0, 8192) :
        if obd_devs[i] != 0 :
            show_obd(obd_devs[i])

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

if ( __name__ == '__main__'):
    import argparse

    parser =  argparse.ArgumentParser()
    parser.add_argument("-d","--device", dest="device",
                        default=0)
    parser.add_argument("-f","--fid", dest="fid",
                        default=0)
    parser.add_argument("-s","--search", dest="search_ptr",
                        default=0)
    args = parser.parse_args()
    if args.fid != 0 :
        lu_dev = readSU("struct lu_device", int(args.device, 0))
        fid = readSU("struct lu_fid", int(args.fid, 0))
        lu_object_find(lu_dev, fid)
    elif args.search_ptr != 0 :
        ptr_search(int(args.search_ptr, 0))
    else :
        show_obds()

