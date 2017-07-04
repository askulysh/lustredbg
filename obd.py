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
    dep = readSU("cfs_hash_head_dep_t", bd_bucket.hsb_head + 16*bd_offset)
    print(dep)
    hlist_head = dep.hd_head
    mdt_object = readSU("struct mdt_object", hlist_head.first - 0x20)
    print(mdt_object)

if ( __name__ == '__main__'):
    import argparse

    parser =  argparse.ArgumentParser()
    parser.add_argument("-d","--device", dest="device",
                        default=0)
    parser.add_argument("-f","--fid", dest="fid",
                        default=0)
    args = parser.parse_args()
    if args.fid != 0 :
        lu_dev = readSU("struct lu_device", int(args.device, 0))
        fid = readSU("struct lu_fid", int(args.fid, 0))
        lu_object_find(lu_dev, fid)

