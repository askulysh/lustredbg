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

def lod_parse_striping(prefix, addr) :
    lmm = readSU("struct lov_mds_md_v1", addr)
    print(lmm, hex(lmm.lmm_magic))
    comp = readSU("struct lov_comp_md_v1", addr)
    print(comp, comp.lcm_entry_count)
    for i in range(comp.lcm_entry_count) :
        lod_comp = readSU("struct lod_layout_component",
                          comp.lcm_entries[i])
        print(lod_comp)
        lmm = readSU("struct lov_mds_md_v1",
                     addr+comp.lcm_entries[i].lcme_offset)
        print(lmm, hex(lmm.lmm_magic))
        for j in range(lmm.lmm_stripe_count) :
            print(lmm.lmm_objects[j])

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
            osp_obj = readSU("struct osp_object", layer -
                             member_offset('struct osp_object', 'opo_obj'))
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
        osp_obj = readSU("struct osp_object", layer -
                         member_offset('struct osp_object', 'opo_obj'))

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

def obd2mdt(dev) :
    """Given an MDT's struct obd_device, return its struct mdt_device.
    dev.obd_lu_dev points at the embedded mdt_lu_dev member."""
    return readSU("struct mdt_device",
                  dev.obd_lu_dev - member_offset("struct mdt_device",
                                                 "mdt_lu_dev"))

def get_tdtd(dev) :
    """Given an MDT's struct obd_device, return its
    struct target_distribute_txn_data (mdt_lut.lut_tdtd)."""
    mdt = obd2mdt(dev)
    return readSU("struct target_distribute_txn_data", mdt.mdt_lut.lut_tdtd)

def show_lut(dev) :
    """Dump an MDT's struct lu_target reply-data bookkeeping
    (lut_reply_header) and the export generation hash
    (lut_obd.obd_gen_hash), the two inputs consulted by
    update_recovery_update_ses() when it tries to attach dtrq_xid
    to an update-log replay (see update_recovery.c:1051)."""
    mdt = obd2mdt(dev)
    lut = mdt.mdt_lut
    lrh = lut.lut_reply_header
    print("lut_reply_header: magic 0x%x header_size %d reply_size %d" %
          (lrh.lrh_magic, lrh.lrh_header_size, lrh.lrh_reply_size))
    ghash = lut.lut_obd.obd_gen_hash
    print("obd_gen_hash %s count %d" % (ghash, ghash.hs_count.counter
          if hasattr(ghash, "hs_count") else -1))

def show_gen_hash(dev) :
    """Walk obd_gen_hash and print each export's lcd_generation (the key
    update_recovery_update_ses() looks up via lrd_client_gen when trying
    to attach dtrq_xid to a replayed update). A generation present in the
    on-disk reply-data record but absent here (e.g. because the client
    was re-registered under a new generation after an eviction/failover)
    would explain a lookup miss and a permanently xid=0 dtrq."""
    exp_off = member_offset("struct obd_export", "exp_gen_hash")
    def show_exp(hnode) :
        exp = readSU("struct obd_export", Addr(hnode) - exp_off)
        gen = exp.u.eu_target_data.ted_lcd.lcd_generation
        print("  export %s uuid %s generation %d conn_cnt %d failed %d" %
              (exp, exp.exp_client_uuid.uuid, gen, exp.exp_conn_cnt,
               exp.exp_failed))
    obd.hash_for_each_hd(dev.obd_gen_hash, show_exp)

def print_dtrq(dtrq, prefix) :
    print("%s%s transno %d batchid %d xid %d local_update_executed %d" %
          (prefix, dtrq, dtrq.dtrq_master_transno, dtrq.dtrq_batchid,
           dtrq.dtrq_xid, dtrq.dtrq_local_update_executed))
    for dtrqs in readSUListFromHead(dtrq.dtrq_sub_list, "dtrqs_list",
            "struct distribute_txn_replay_req_sub") :
        print("%s    sub mdt_index %d %s" %
              (prefix, dtrqs.dtrqs_mdt_index, dtrqs))

def print_dtrq_list(head, prefix, name) :
    print("%s%s:" % (prefix, name))
    for dtrq in readSUListFromHead(head, "dtrq_list",
            "struct distribute_txn_replay_req") :
        print_dtrq(dtrq, prefix + "  ")

def show_tdtd(dev) :
    """Dump target_distribute_txn_data for an MDT (batchid bookkeeping and
    the two update-replay lists: tdtd_replay_list (pending) and
    tdtd_replay_finish_list (already applied via update-log replay, which
    is consulted by is_req_replayed_by_update() to drop duplicate client
    request replays)."""
    tdtd = get_tdtd(dev)
    print("%s tdtd_batchid %d tdtd_committed_batchid %d" %
          (tdtd, tdtd.tdtd_batchid, tdtd.tdtd_committed_batchid))
    print_dtrq_list(tdtd.tdtd_replay_list, "  ", "tdtd_replay_list (pending)")
    print_dtrq_list(tdtd.tdtd_replay_finish_list, "  ",
                    "tdtd_replay_finish_list (applied)")

def find_dtrq(dev, transno) :
    """Search both tdtd replay lists for a dtrq matching dtrq_master_transno,
    e.g. to check whether a given client replay transno was already
    recorded as applied via the update-log replay path."""
    tdtd = get_tdtd(dev)
    for name, head in (("tdtd_replay_list", tdtd.tdtd_replay_list),
                       ("tdtd_replay_finish_list",
                        tdtd.tdtd_replay_finish_list)) :
        for dtrq in readSUListFromHead(head, "dtrq_list",
                "struct distribute_txn_replay_req") :
            if dtrq.dtrq_master_transno == transno :
                print("found in %s:" % name)
                print_dtrq(dtrq, "  ")
                return dtrq
    print("transno %d not found in tdtd_replay_list or "
          "tdtd_replay_finish_list" % transno)
    return None

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
    parser.add_argument("-l","--lov", dest="lov", default = 0)
    parser.add_argument("-T","--tdtd", dest="tdtd", default = 0,
                        help="struct obd_device address of an MDT; "
                             "dump target_distribute_txn_data replay lists")
    parser.add_argument("-x","--transno", dest="transno", default = 0,
                        help="with -T, look up a single dtrq by "
                             "dtrq_master_transno in either replay list")
    parser.add_argument("-L","--lut", dest="lut", default = 0,
                        help="struct obd_device address of an MDT; dump "
                             "lut_reply_header and obd_gen_hash")
    parser.add_argument("-G","--gen-hash", dest="genhash", default = 0,
                        help="struct obd_device address of an MDT; dump "
                             "obd_gen_hash entries (export generations)")
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
    elif args.lov != 0 :
        lod_parse_striping("", int(args.lov, 16))
    elif args.tdtd != 0 :
        dev = readSU("struct obd_device", int(args.tdtd, 16))
        if args.transno != 0 :
            find_dtrq(dev, int(args.transno))
        else :
            show_tdtd(dev)
    elif args.lut != 0 :
        dev = readSU("struct obd_device", int(args.lut, 16))
        show_lut(dev)
    elif args.genhash != 0 :
        dev = readSU("struct obd_device", int(args.genhash, 16))
        show_gen_hash(dev)

