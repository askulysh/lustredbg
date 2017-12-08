# mdt functions

from __future__ import print_function

from pykdump.API import *
from obd import *

mdd_lu_obj_ops = readSymbol("mdd_lu_obj_ops")
lod_lu_obj_ops = readSymbol("lod_lu_obj_ops")
osd_lu_obj_ops = readSymbol("osd_lu_obj_ops")
osp_lu_obj_ops = readSymbol("osp_lu_obj_ops")
mdt_obj_ops = readSymbol("mdt_obj_ops")

lu_object_header_attr_c = '''
enum lu_object_header_attr {
        LOHA_EXISTS   = 1,
        LOHA_REMOTE   = 2
};
'''
lu_object_header_attr = CEnum(lu_object_header_attr_c)

def attr2str(attr) :
    ret = lu_object_header_attr.__getitem__(attr & 3)
    if attr & 0xf000 == 0x4000 :
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

def fid2str(fid) :
    return "[0x%x:0x%x:0x%x]" % (fid.f_seq, fid.f_oid, fid.f_ver)

def print_osd_object(osd_obj, prefix) :
    inode = readSU("struct inode", osd_obj.oo_inode)
    print(prefix, inode)

def print_mdt_obj(mdt, prefix):
    moh = mdt.mot_header
    print(prefix, "%s %s flags: %x attr 0%o %s" % (mdt, fid2str(moh.loh_fid),
           moh.loh_flags, moh.loh_attr, attr2str(moh.loh_attr)))

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
        elif layer.lo_ops == osp_lu_obj_ops :
            osp_obj = readSU("struct osp_object", layer - 0x50)
            print(prefix, "osp", osp_obj)
        else :
            print(prefix, "unknown", layer)

def find_print_fid(lu_dev, fid, prefix) :
    mdt_obj = lu_object_find(lu_dev, fid)
    if mdt_obj :
        print_mdt_obj(mdt_obj, prefix)

def parse_mti(mti, prefix):
    fid_prefix = prefix + "    "
    print("mdt", mti.mti_mdt)
    lu_dev = mti.mti_mdt.mdt_lu_dev
    print("mti_tmp_fid1", mti.mti_tmp_fid1, fid2str(mti.mti_tmp_fid1))
    find_print_fid(lu_dev, mti.mti_tmp_fid1, fid_prefix)
    print("mti_tmp_fid2", mti.mti_tmp_fid2, fid2str(mti.mti_tmp_fid2))
    find_print_fid(lu_dev, mti.mti_tmp_fid2, fid_prefix)
    print("rr_fid1", mti.mti_rr.rr_fid1, fid2str( mti.mti_rr.rr_fid1))
    find_print_fid(lu_dev, mti.mti_rr.rr_fid1, fid_prefix)
    print("rr_fid2", mti.mti_rr.rr_fid2, fid2str( mti.mti_rr.rr_fid2))
    find_print_fid(lu_dev, mti.mti_rr.rr_fid2, fid_prefix)

if ( __name__ == '__main__'):
    import argparse

    parser =  argparse.ArgumentParser()
    parser.add_argument("-t","--mdt", dest="mdt", default = 0)
    parser.add_argument("-s","--osd", dest="osd", default = 0)
    parser.add_argument("-i","--mti", dest="mti", default = 0)
    args = parser.parse_args()
    if args.mdt != 0 :
        mdt_obj = readSU("struct mdt_object", int(args.mdt, 16))
        print_mdt_obj(mdt_obj, "")
    elif args.osd != 0 :
        osd_obj = readSU("struct osd_object", int(args.osd, 16))
        print_osd_object(osd_obj, "")
    elif args.mti != 0 :
        mti = readSU("struct mdt_thread_info", int(args.mti, 16))
        parse_mti(mti, "")

