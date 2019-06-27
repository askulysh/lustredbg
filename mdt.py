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
#define LOHA_EXISTS             1
#define LOHA_REMOTE             2
#define LOHA_HAS_AGENT_ENTRY    4
'''
lu_object_header_attr = CDefine(lu_object_header_attr_c)


mod_flags_c = '''
#define	DEAD_OBJ    1
#define	ORPHAN_OBJ  2
#define	VOLATILE_OBJ 16
'''
mod_flags = CDefine(mod_flags_c)

def attr2str(attr) :
    ret = dbits2str(attr & 7, lu_object_header_attr)
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
    print(prefix, inode, "ino", osd_obj.oo_inode.i_ino,
            "nlink", osd_obj.oo_inode.i_nlink)

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
            print(prefix, "mdd", mdd_obj,
                  dbits2str(mdd_obj.mod_flags, mod_flags))
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
    if mti.mti_rr.rr_opcode == mds_reint.REINT_RENAME :
        print("rename %s/%s -> %s/%s" % (
              fid2str(mti.mti_rr.rr_fid1), mti.mti_rr.rr_name.ln_name,
              fid2str(mti.mti_rr.rr_fid2), mti.mti_rr.rr_tgt_name.ln_name))
    elif mti.mti_rr.rr_opcode == mds_reint.REINT_MIGRATE :
        print("migrate %s/%s -> %s" % (fid2str(mti.mti_rr.rr_fid1),
            mti.mti_rr.rr_name.ln_name, fid2str(mti.mti_rr.rr_fid2)))

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
        mdt_obj = readSU("struct mdt_object", osd_obj.oo_dt.do_lu.lo_header)
        print_mdt_obj(mdt_obj, "")
    elif args.mti != 0 :
        mti = readSU("struct mdt_thread_info", int(args.mti, 16))
        parse_mti(mti, "")

