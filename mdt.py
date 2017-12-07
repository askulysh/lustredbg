# mdt functions

from __future__ import print_function

from pykdump.API import *
from obd import *

mdd_lu_obj_ops = readSymbol("mdd_lu_obj_ops")
lod_lu_obj_ops = readSymbol("lod_lu_obj_ops")
osd_lu_obj_ops = readSymbol("osd_lu_obj_ops")
mdt_obj_ops = readSymbol("mdt_obj_ops")

def fid2str(fid) :
    return "[0x%x:0x%x:0x%x]" % (fid.f_seq, fid.f_oid, fid.f_ver)

def print_osd_object(osd_obj, prefix) :
    inode = readSU("struct inode", osd_obj.oo_inode)
    print(prefix, inode)

def print_mdt_obj(mdt, prefix):
    moh = mdt.mot_header
    print(prefix, "%s %s flags: %x attr 0%o" % (mdt, fid2str(moh.loh_fid),
           moh.loh_flags, moh.loh_attr))

    for layer in readSUListFromHead(mdt.mot_header.loh_layers, "lo_linkage",
            "struct lu_object") :
        if layer.lo_ops == mdt_obj_ops :
            print(prefix, "mdt", layer)
        elif layer.lo_ops == mdd_lu_obj_ops :
            mdd_obj = readSU("struct mdd_object", layer)
            print(prefix, "mdd", mdd_obj)
        elif layer.lo_ops == lod_lu_obj_ops :
            lod_obj = readSU("struct lod_object", layer)
            print(prefix, "lod", lod_obj)
        elif layer.lo_ops == osd_lu_obj_ops :
            osd_obj = readSU("struct osd_object", layer)
            print(prefix, "osd", osd_obj)
            print_osd_object(osd_obj, prefix + "\t")

def find_print_fid(lu_dev, fid, prefix) :
    mdt_obj = lu_object_find(lu_dev, fid)
    if mdt_obj :
        print(mdt_obj)
        print_mdt_obj(mdt_obj, prefix)

def parse_mti(mti, prefix):
    fid_prefix = prefix + "    "
    print("mdt", mti.mti_mdt)
    lu_dev = mti.mti_mdt.mdt_lu_dev
    print("mti_tmp_fid1", mti.mti_tmp_fid1)
    find_print_fid(lu_dev, mti.mti_tmp_fid1, fid_prefix)
    print("mti_tmp_fid2", mti.mti_tmp_fid2)
    find_print_fid(lu_dev, mti.mti_tmp_fid2, fid_prefix)
    print("rr_fid1", mti.mti_rr.rr_fid1)
    find_print_fid(lu_dev, mti.mti_rr.rr_fid1, fid_prefix)
    print("rr_fid2", mti.mti_rr.rr_fid2)
    find_print_fid(lu_dev, mti.mti_rr.rr_fid2, fid_prefix)

if ( __name__ == '__main__'):
    import argparse

    parser =  argparse.ArgumentParser()
    parser.add_argument("-t","--mdt", dest="mdt", default = 0)
    parser.add_argument("-s","--osd", dest="osd", default = 0)
    parser.add_argument("-i","--mti", dest="mti", default = 0)
    args = parser.parse_args()
    if args.mdt != 0 :
        mdt_obj = readSU("struct mdt_object", int(args.mdt, 0))
        print_mdt_obj(mdt_obj, "")
    elif args.osd != 0 :
        osd_obj = readSU("struct osd_object", int(args.osd, 0))
        print_osd_object(osd_obj, "")
    elif args.mti != 0 :
        mti = readSU("struct mdt_thread_info", int(args.mti, 16))
        parse_mti(mti, "")

