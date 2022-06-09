# mdt functions

from __future__ import print_function

from pykdump.API import *
import obd as obd
import ptlrpc as ptlrpc
import ldlm_lock as ldlm
import osd as osd

if sym2addr("mdt_lu_obj_ops") :
    mdt_lu_obj_ops = readSymbol("mdt_lu_obj_ops")
else :
    mdt_lu_obj_ops = 0
if sym2addr("mdd_lu_obj_ops") :
    mdd_lu_obj_ops = readSymbol("mdd_lu_obj_ops")
else :
    mdd_lu_obj_ops = 0
if sym2addr("lod_lu_obj_ops") :
    lod_lu_obj_ops = readSymbol("lod_lu_obj_ops")
else :
    lod_lu_obj_ops = 0
if sym2addr("osp_lu_obj_ops") :
    osp_lu_obj_ops = readSymbol("osp_lu_obj_ops")
else :
    osp_lu_obj_ops = 0
if sym2addr("osd_lu_obj_ops") :
    osd_lu_obj_ops = readSymbol("osd_lu_obj_ops")
else :
    osd_lu_obj_ops = 0

mod_flags_c = '''
#define	DEAD_OBJ    1
#define	ORPHAN_OBJ  2
#define	VOLATILE_OBJ 16
'''
mod_flags = CDefine(mod_flags_c)

def print_link_ea(prefix, leh) :
    if leh.leh_magic == 0x11EAF1DF :
        addr = leh + 1
        for i in range(0,leh.leh_reccount) :
            lee = readSU("struct link_ea_entry", addr)
            reclen = (lee.lee_reclen[0] << 8) + lee.lee_reclen[1]
            name  = readmem(lee.lee_name,  reclen - 16 - 2)
            print(prefix, lee, name, obd.fid_be2str(lee.lee_parent_fid))
            addr = addr + reclen 
    else :
        print("leh magic error !", leh.leh_magic)

def print_osp_object(osp_obj, prefix) :
    print(prefix, "osp", osp_obj)
    prefix += "\t"
    oxe_name_exists = member_size("struct osp_xattr_entry", "oxe_name")
    for oxe in readSUListFromHead(osp_obj.opo_xattr_list, "oxe_list",
            "struct osp_xattr_entry") :
        if oxe_name_exists == -1:
            name = readmem(oxe.oxe_buf, oxe.oxe_namelen)
        else :
            name = readmem(oxe.oxe_name, oxe.oxe_namelen)
        print(prefix, name, oxe)
        if name == b'trusted.link' :
            ea_header = readSU("struct link_ea_header", oxe.oxe_value)
            print_link_ea(prefix, ea_header)

def print_lod_object(lod, prefix) :
    if obd.is_dir(lod.ldo_obj.do_lu.lo_header.loh_attr) :
        slave = lod.ldo_dir_slave_stripe & 4
        striped = lod.ldo_dir_striped & 2
        print(prefix, "striped dir", striped, "slave", slave,
              "stripe count", lod.ldo_dir_stripe_count)
        for i in range(lod.ldo_dir_stripe_count) :
            print_full_tree_mdt_obj(lod.ldo_stripe[i].do_lu, prefix + "    ")
    else :
        print(prefix, "comp count", lod.ldo_comp_cnt)
        for i in range(lod.ldo_comp_cnt) :
            comp = lod.ldo_comp_entries[i]
            print(prefix, comp, "stripe cnt", comp.llc_stripe_count)
            for j in range(comp.llc_stripe_count) :
                osp_obj = readSU("struct osp_object", comp.llc_stripe[j] -
                        member_offset('struct osp_object', 'opo_obj'))
                print_osp_object(osp_obj, prefix + "\t")

def print_generic_mdt_obj(layer, prefix) :
        if layer.lo_ops == mdt_lu_obj_ops :
            print(prefix, "mdt", layer)
        elif layer.lo_ops == mdd_lu_obj_ops :
            mdd_obj = readSU("struct mdd_object", layer)
            print(prefix, "mdd", mdd_obj,
                  dbits2str(mdd_obj.mod_flags, mod_flags))
        elif layer.lo_ops == lod_lu_obj_ops :
            lod_obj = readSU("struct lod_object", layer)
            print(prefix, "lod", lod_obj)
            try :
                print_lod_object(lod_obj, prefix + "\t")
            except :
                pass
        elif layer.lo_ops == osd_lu_obj_ops :
            osd_obj = readSU("struct osd_object", layer)
            print(prefix, "osd", osd_obj)
            osd.print_osd_object(osd_obj, prefix + "\t")
        elif layer.lo_ops == osp_lu_obj_ops :
            osp_obj = readSU("struct osp_object", layer - 0x50)
            print_osp_object(osp_obj, prefix)
        else :
            print(prefix, "unknown", layer)

def print_full_tree_mdt_obj(layer, prefix) :
    if layer.lo_ops == mdt_obj_ops :
        mdt = layer
        print(prefix, "mdt", layer)
    elif layer.lo_ops == mdd_lu_obj_ops :
        mdd_obj = readSU("struct mdd_object", layer)
        mdt = readSU("struct mdt_object",
                Addr(mdd_obj.mod_obj.mo_lu.lo_header))
    elif layer.lo_ops == lod_lu_obj_ops :
        lod_obj = readSU("struct lod_object", layer)
        mdt = readSU("struct mdt_object",
                Addr(lod_obj.ldo_obj.do_lu.lo_header))
    elif layer.lo_ops == osd_lu_obj_ops :
        osd_obj = readSU("struct osd_object", layer)
        mdt = readSU("struct mdt_object",
                Addr(osd_obj.oo_dt.do_lu.lo_header))
    elif layer.lo_ops == osp_lu_obj_ops :
        osp_obj = readSU("struct osp_object", layer - 0x50)
        mdt = readSU("struct mdt_object",
                Addr(osp_obj.opo_obj.do_lu.lo_header))
    else :
        print(prefix, "unknown", layer)
        mdt = None
    if mdt:
        print_mdt_obj(mdt, prefix)

def print_mdt_obj(mdt, prefix):
    obd.print_loh(mdt.mot_header, prefix)
    for layer in readSUListFromHead(mdt.mot_header.loh_layers, "lo_linkage",
            "struct lu_object") :
        print_generic_mdt_obj(layer, prefix + "    ")

def find_print_fid(lu_dev, fid, prefix) :
    lu_obj = obd.lu_object_find(lu_dev, fid)
    if lu_obj :
        mdt_obj = readSU("struct mdt_object", Addr(lu_obj))
        print_mdt_obj(mdt_obj, prefix)

def parse_mti(mti, opc, prefix):
    fid_prefix = prefix + "    "
    print("mdt", mti.mti_mdt)
    lu_dev = mti.mti_mdt.mdt_lu_dev
    print("mti_tmp_fid1", mti.mti_tmp_fid1, obd.fid2str(mti.mti_tmp_fid1))
    find_print_fid(lu_dev, mti.mti_tmp_fid1, fid_prefix)
    print("mti_tmp_fid2", mti.mti_tmp_fid2, obd.fid2str(mti.mti_tmp_fid2))
    try :
        find_print_fid(lu_dev, mti.mti_tmp_fid2, fid_prefix)
    except:
        print()

    if opc == 0 or opc == ptlrpc.opcodes.MDS_REINT :
        print("rr_fid1", mti.mti_rr.rr_fid1, obd.fid2str( mti.mti_rr.rr_fid1))
        find_print_fid(lu_dev, mti.mti_rr.rr_fid1, fid_prefix)
        print("rr_fid2", mti.mti_rr.rr_fid2, obd.fid2str( mti.mti_rr.rr_fid2))
        try :
            find_print_fid(lu_dev, mti.mti_rr.rr_fid2, fid_prefix)
        except:
            print()
        if mti.mti_rr.rr_opcode == ptlrpc.mds_reint.REINT_RENAME :
            print("rename %s/%s %s -> %s/%s %s" % (
                  obd.fid2str(mti.mti_rr.rr_fid1), mti.mti_rr.rr_name.ln_name,
                  obd.fid2str(mti.mti_tmp_fid1),
                  obd.fid2str(mti.mti_rr.rr_fid2), mti.mti_rr.rr_tgt_name.ln_name,
                  obd.fid2str(mti.mti_tmp_fid2)))
        elif mti.mti_rr.rr_opcode == ptlrpc.mds_reint.REINT_MIGRATE :
            print("migrate %s/%s -> %s" % (obd.fid2str(mti.mti_rr.rr_fid1),
                mti.mti_rr.rr_name.ln_name, obd.fid2str(mti.mti_rr.rr_fid2)))
        else :
            print(mti.mti_rr)
    for i in range(6) :
        print(i, ":")
        ldlm.show_mlh(mti.mti_lh[i], prefix)

if ( __name__ == '__main__'):
    import argparse

    parser =  argparse.ArgumentParser()
    parser.add_argument("-t","--mdt", dest="mdt", default = 0)
    parser.add_argument("-d","--mdd", dest="mdd", default = 0)
    parser.add_argument("-s","--osd", dest="osd", default = 0)
    parser.add_argument("-i","--mti", dest="mti", default = 0)
    args = parser.parse_args()
    if args.mdt != 0 :
        mdt_obj = readSU("struct mdt_object", int(args.mdt, 16))
        print_mdt_obj(mdt_obj, "")
    elif args.mdd != 0 :
        mdd_obj = readSU("struct mdd_object", int(args.mdd, 16))
        mdt_obj = readSU("struct mdt_object", mdd_obj.mod_obj.mo_lu.lo_header)
        print_mdt_obj(mdt_obj, "")
    elif args.osd != 0 :
        osd_obj = readSU("struct osd_object", int(args.osd, 16))
        mdt_obj = readSU("struct mdt_object", osd_obj.oo_dt.do_lu.lo_header)
        print_mdt_obj(mdt_obj, "")
    elif args.mti != 0 :
        mti = readSU("struct mdt_thread_info", int(args.mti, 16))
        parse_mti(mti, 0, "")

