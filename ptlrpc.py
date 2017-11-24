# ptlrpc functions

from __future__ import print_function

from pykdump.API import *
from ktime import *
from lnet import *

max_req = 10


obd_md_flags_c = '''
#define OBD_MD_FLID        0x00000001
#define OBD_MD_FLATIME     0x00000002
#define OBD_MD_FLMTIME     0x00000004
#define OBD_MD_FLCTIME     0x00000008
#define OBD_MD_FLSIZE      0x00000010
#define OBD_MD_FLBLOCKS    0x00000020
#define OBD_MD_FLBLKSZ     0x00000040
#define OBD_MD_FLMODE      0x00000080
#define OBD_MD_FLTYPE      0x00000100
#define OBD_MD_FLUID       0x00000200
#define OBD_MD_FLGID       0x00000400
#define OBD_MD_FLFLAGS     0x00000800
#define OBD_MD_FLNLINK     0x00002000
#define OBD_MD_FLGENER     0x00004000
/*#define OBD_MD_FLINLINE    (0x00008000ULL)  inline data. used until 1.6.5 */
#define OBD_MD_FLRDEV      0x00010000
#define OBD_MD_FLEASIZE    0x00020000
#define OBD_MD_LINKNAME    0x00040000
#define OBD_MD_FLHANDLE    0x00080000
#define OBD_MD_FLCKSUM     0x00100000
#define OBD_MD_FLQOS       0x00200000
/*#define OBD_MD_FLOSCOPQ    (0x00400000ULL) osc opaque data, never used */
#define OBD_MD_FLCOOKIE    0x00800000
#define OBD_MD_FLGROUP     0x01000000
#define OBD_MD_FLFID       0x02000000
#define OBD_MD_FLEPOCH     0x04000000
#define OBD_MD_FLGRANT     (0x08000000ULL) /* ost preallocation space grant */
#define OBD_MD_FLDIREA     (0x10000000ULL) /* dir's extended attribute data */
#define OBD_MD_FLUSRQUOTA  (0x20000000ULL) /* over quota flags sent from ost */
#define OBD_MD_FLGRPQUOTA  (0x40000000ULL) /* over quota flags sent from ost */
#define OBD_MD_FLMODEASIZE (0x80000000ULL) /* EA size will be changed */

#define OBD_MD_MDS         (0x0000000100000000ULL) /* where an inode lives on */
#define OBD_MD_REINT       (0x0000000200000000ULL) /* reintegrate oa */
#define OBD_MD_MEA         (0x0000000400000000ULL) /* CMD split EA  */
#define OBD_MD_TSTATE      (0x0000000800000000ULL) /* transient state field */

#define OBD_MD_FLXATTR       (0x0000001000000000ULL) /* xattr */
#define OBD_MD_FLXATTRLS     (0x0000002000000000ULL) /* xattr list */
#define OBD_MD_FLXATTRRM     (0x0000004000000000ULL) /* xattr remove */
#define OBD_MD_FLACL         (0x0000008000000000ULL) /* ACL */
#define OBD_MD_FLRMTPERM     (0x0000010000000000ULL) /* remote permission */
#define OBD_MD_FLMDSCAPA     (0x0000020000000000ULL) /* MDS capability */
#define OBD_MD_FLOSSCAPA     (0x0000040000000000ULL) /* OSS capability */
#define OBD_MD_FLCKSPLIT     (0x0000080000000000ULL) /* Check split on server */
#define OBD_MD_FLCROSSREF    (0x0000100000000000ULL) /* Cross-ref case */
#define OBD_MD_FLGETATTRLOCK (0x0000200000000000ULL) /* Get IOEpoch attributes
                                                      * under lock; for xattr
                                                      * requests means the
                                                      * client holds the lock */
#define OBD_MD_FLOBJCOUNT    (0x0000400000000000ULL) /* for multiple destroy */

#define OBD_MD_FLRMTLSETFACL (0x0001000000000000ULL) /* lfs lsetfacl case */
#define OBD_MD_FLRMTLGETFACL (0x0002000000000000ULL) /* lfs lgetfacl case */
#define OBD_MD_FLRMTRSETFACL (0x0004000000000000ULL) /* lfs rsetfacl case */
#define OBD_MD_FLRMTRGETFACL (0x0008000000000000ULL) /* lfs rgetfacl case */

#define OBD_MD_FLDATAVERSION (0x0010000000000000ULL) /* iversion sum */
#define OBD_MD_FLRELEASED    (0x0020000000000000ULL) /* file released */
'''
obd_md_flags = CDefine(obd_md_flags_c)

opcodes_c = '''
enum {
        OST_REPLY      =  0,
        OST_GETATTR    =  1,
        OST_SETATTR    =  2,
        OST_READ       =  3,
        OST_WRITE      =  4,
        OST_CREATE     =  5,
        OST_DESTROY    =  6,
        OST_GET_INFO   =  7,
        OST_CONNECT    =  8,
        OST_DISCONNECT =  9,
        OST_PUNCH      = 10,
        OST_OPEN       = 11,
        OST_CLOSE      = 12,
        OST_STATFS     = 13,
        OST_SYNC       = 16,
        OST_SET_INFO   = 17,
        OST_QUOTACHECK = 18,
        OST_QUOTACTL   = 19,
	OST_QUOTA_ADJUST_QUNIT = 20,
	MDS_GETATTR		= 33,
	MDS_GETATTR_NAME	= 34,
	MDS_CLOSE		= 35,
	MDS_REINT		= 36,
	MDS_READPAGE		= 37,
	MDS_CONNECT		= 38,
	MDS_DISCONNECT		= 39,
	MDS_GETSTATUS		= 40,
	MDS_STATFS		= 41,
	MDS_PIN			= 42,
	MDS_UNPIN		= 43,
	MDS_SYNC		= 44,
	MDS_DONE_WRITING	= 45,
	MDS_SET_INFO		= 46,
	MDS_QUOTACHECK		= 47,
	MDS_QUOTACTL		= 48,
	MDS_GETXATTR		= 49,
	MDS_SETXATTR		= 50,
	MDS_WRITEPAGE		= 51,
	MDS_IS_SUBDIR		= 52,
	MDS_GET_INFO		= 53,
	MDS_HSM_STATE_GET	= 54,
	MDS_HSM_STATE_SET	= 55,
	MDS_HSM_ACTION		= 56,
	MDS_HSM_PROGRESS	= 57,
	MDS_HSM_REQUEST		= 58,
	MDS_HSM_CT_REGISTER	= 59,
	MDS_HSM_CT_UNREGISTER	= 60,
	MDS_SWAP_LAYOUTS	= 61,
        LDLM_ENQUEUE     = 101,
        LDLM_CONVERT     = 102,
        LDLM_CANCEL      = 103,
        LDLM_BL_CALLBACK = 104,
        LDLM_CP_CALLBACK = 105,
        LDLM_GL_CALLBACK = 106,
        LDLM_SET_INFO    = 107
};
'''
opcodes = CEnum(opcodes_c)

mds_reint_c = '''
enum {
	REINT_SETATTR  = 1,
	REINT_CREATE   = 2,
	REINT_LINK     = 3,
	REINT_UNLINK   = 4,
	REINT_RENAME   = 5,
	REINT_OPEN     = 6,
	REINT_SETXATTR = 7,
	REINT_RMENTRY  = 8
};
'''
mds_reint = CEnum(mds_reint_c)

it_flags_c = '''
#define IT_OPEN     0x0001
#define IT_CREAT    0x0002
#define IT_READDIR  0x0004
#define IT_GETATTR  0x0008
#define IT_LOOKUP   0x0010
#define IT_UNLINK   0x0020
#define IT_GETXATTR 0x0040
#define IT_EXEC     0x0080
#define IT_PIN      0x0100
'''
it_flags = CDefine(it_flags_c)


reint_fmts = [0 for i in range(9)]
reint_fmts[mds_reint.REINT_SETATTR] = "RQF_MDS_REINT_SETATTR"
reint_fmts[mds_reint.REINT_CREATE] = "RQF_MDS_REINT_CREATE"
reint_fmts[mds_reint.REINT_LINK] = "RQF_MDS_REINT_LINK"
reint_fmts[mds_reint.REINT_UNLINK] = "RQF_MDS_REINT_UNLINK"
reint_fmts[mds_reint.REINT_RENAME] = "RQF_MDS_REINT_RENAME"
reint_fmts[mds_reint.REINT_OPEN] = "RQF_MDS_REINT_OPEN"
reint_fmts[mds_reint.REINT_SETXATTR] = "RQF_MDS_REINT_SETXATTR"
reint_fmts[mds_reint.REINT_RMENTRY] = "RQF_MDS_REINT_UNLINK"

mds_open_flags_c = '''
#define FMODE_READ               00000001
#define FMODE_WRITE              00000002

#define MDS_FMODE_EXEC           00000004
#define MDS_FMODE_EPOCH          01000000
#define MDS_FMODE_TRUNC          02000000
#define MDS_FMODE_SOM            04000000

#define MDS_OPEN_CREATED         00000010
#define MDS_OPEN_CROSS           00000020

#define MDS_OPEN_CREAT           00000100
#define MDS_OPEN_EXCL            00000200
#define MDS_OPEN_TRUNC           00001000
#define MDS_OPEN_APPEND          00002000
#define MDS_OPEN_SYNC            00010000
#define MDS_OPEN_DIRECTORY       00200000

#define MDS_OPEN_BY_FID 	040000000
#define MDS_OPEN_DELAY_CREATE  0100000000
#define MDS_OPEN_OWNEROVERRIDE 0200000000
#define MDS_OPEN_JOIN_FILE     0400000000

#define MDS_OPEN_LOCK         04000000000
#define MDS_OPEN_HAS_EA      010000000000
#define MDS_OPEN_HAS_OBJS    020000000000
'''
mds_open_flags = CDefine(mds_open_flags_c)


lustre_imp_state_c = '''
enum lustre_imp_state {
        LUSTRE_IMP_CLOSED     = 1,
        LUSTRE_IMP_NEW        = 2,
        LUSTRE_IMP_DISCON     = 3,
        LUSTRE_IMP_CONNECTING = 4,
        LUSTRE_IMP_REPLAY     = 5,
        LUSTRE_IMP_REPLAY_LOCKS = 6,
        LUSTRE_IMP_REPLAY_WAIT  = 7,
        LUSTRE_IMP_RECOVER    = 8,
        LUSTRE_IMP_FULL       = 9,
        LUSTRE_IMP_EVICTED    = 10
};
'''
lustre_imp_state = CEnum(lustre_imp_state_c)

def print_req_flags(req) :
    s  = ""
    if req.rq_intr :
        s = s + "|Intrrupted"
    if req.rq_replied :
        s = s + "|Replied"
    if req.rq_err :
        s = s + "|Error"
    if req.rq_net_err :
        s = s + "|NetError"
    if req.rq_timedout :
        s = s + "|Timedout"
    if req.rq_resend :
        s = s + "|Resend"
    if req.rq_restart :
        s = s + "|Restart"
    if req.rq_replay :
        s = s + "|Replay"
    if req.rq_waiting :
        s = s + "|Waiting"
    return s

def phase2str(phase) :
    return {
        -339681792 : 'NEW',
        -339681791 : 'RPC',
        -339681790 : 'BULK',
        -339681789 : 'INTERPRET',
        -339681788 : 'COMPLETE',
        -339681787 : 'UNREG_RPC',
        -339681786 : 'UNREG_BULK',
        -339681785 : 'UNDEFINED',
    } [phase]

def req_sent(req) :
    if req.rq_sent != 0 :
        return ("sent %4ds ago dl in %5ds" %
            (get_seconds() - req.rq_sent, req.rq_deadline - get_seconds()))
    else :
        return "Waiting...                  "

def get_msg_buffer(msg, n) :
    bufcount = msg.lm_bufcount
    offset = (8*4 + (bufcount )*4 + 7) & (~0x7)
    a = int(msg) + offset
    for i in range(0, n) :
        a += ((msg.lm_buflens[i] + 7) & (~7))

    return a

def get_req_buffer(req, n) :
    msg = req.rq_reqmsg
    return get_msg_buffer(msg, n)

def fid2str(fid) :
    return "[0x%x:0x%x:0x%x]" % (fid.f_seq, fid.f_oid, fid.f_ver)

def mtd_reint_show(reint) :
    if reint.rr_opcode == mds_reint.REINT_UNLINK :
        rec = readSU("struct mdt_rec_unlink", int(reint))
        print("%s unlink %s/%s" % (rec, fid2str(rec.ul_fid1),
            fid2str(rec.ul_fid2)))
    elif reint.rr_opcode == mds_reint.REINT_OPEN :
        rec = readSU("struct mdt_rec_create", int(reint))
        print("%s open   %s/%s %s" % (rec, fid2str(rec.cr_fid1),
            fid2str(rec.cr_fid2), dbits2str(rec.cr_flags_l, mds_open_flags)))
    else :
        print("%s %s %s" % (reint, mds_reint.__getitem__(reint.rr_opcode), fid2str(reint.rr_fid1)))

def mdt_body_show(prefix, body) :
    out = prefix
#    out += "valid " + dbits2str(body.valid, obd_md_flags)
    if body.valid & obd_md_flags.OBD_MD_FLID :
        out += fid2str(body.fid1)
    if body.valid & obd_md_flags.OBD_MD_FLSIZE :
        out += " sz:%s" % body.size
    if body.valid & obd_md_flags.OBD_MD_FLMODE :
        out += " mode:%o" % (body.mode & (~(0xf000)))
    if body.valid & obd_md_flags.OBD_MD_FLTYPE :
        out += " type:%x" % (body.mode & 0xf000)
    print(out)

def show_request_loc(req, req_format, location) :
    for i in range(0, req_format.rf_fields[location].nr) :
        req_msg_field = readSU("struct req_msg_field",
                req_format.rf_fields[location].d[i])
        offset = req_msg_field.rmf_offset[req_format.rf_idx][location]
        if location == 0 :
            msg = req.rq_reqmsg
        else :
            msg = req.rq_repmsg

        if location == 0:
            buf = get_msg_buffer(msg, i)
        else:
            buf = get_msg_buffer(msg, i)

        name = req_msg_field.rmf_name
        if name == "ptlrpc_body" :
            name = "ptlrpc_body_v3"
        elif name == "dlm_req":
            name  = "ldlm_request"
        elif name == "dlm_rep":
            name  = "ldlm_reply"
        elif name == "rec_reint":
            name  = "mdt_rec_reint"
        elif name == "capa":
            name  = "lustre_capa"
        elif name == "mdt_body":
            name  = "mdt_body"
        elif name == "name":
            s = msg.lm_buflens[i+1]
            print("  offset %d %s %s" % (offset, name, str(readmem(buf, s))))
            name = 0

        if name :
            try:
               field = readSU("struct " + name, buf)
               print("  offset %d %s %s" % (offset, req_msg_field.rmf_name, field))
            except TypeError :
                name = 0

        if name == 0 :
            print("  offset %d %s %x" % (offset, req_msg_field.rmf_name, buf))

        if name == "mdt_rec_reint":
            mtd_reint_show(field)
        elif name == "mdt_body":
            mdt_body_show("   ", field)
        elif name == "ldlm_intent":
            print("  offset %d %s %s" % (offset,    field, dbits2str(field.opc, it_flags)))

def show_request_fmt(req, fmt) :
    req_format = readSymbol(fmt)
    print("request:")
    show_request_loc(req, req_format, 0)
    print("reply:")
    show_request_loc(req, req_format, 1)

def show_ptlrpc_request_buf(req) :
    body = readSU("struct ptlrpc_body_v3", get_req_buffer(req, 0))
    print("opc %s" % opcodes.__getitem__(body.pb_opc))
    if body.pb_opc == opcodes.LDLM_ENQUEUE :
        reint = readSU("struct mdt_rec_reint", get_req_buffer(req, 3))
        if reint.rr_opcode == mds_reint.REINT_CREATE :
            show_request_fmt(req, "RQF_LDLM_INTENT_CREATE")
        elif reint.rr_opcode == mds_reint.REINT_OPEN :
            show_request_fmt(req, "RQF_LDLM_INTENT_OPEN")
        else:
            print(body)
            print(reint.rr_opcode)
            ldlm_req = readSU("struct ldlm_request", get_req_buffer(req, 1))
            print(ldlm_req)
    elif body.pb_opc == opcodes.MDS_REINT :
        reint = readSU("struct mdt_rec_reint", get_req_buffer(req, 1))
        show_request_fmt(req, reint_fmts[reint.rr_opcode])
    elif body.pb_opc == opcodes.OST_WRITE :
        show_request_fmt(req, "OST_BRW_WRITE")

def show_ptlrpc_request(req) :
    print("%x x%d %s %4d %s %s" %
          (req, req.rq_xid, req_sent(req), req.rq_status,
           phase2str(req.rq_phase), print_req_flags(req)))
    if req.rq_import != 0:
        show_import("  ", req.rq_import)
    show_ptlrpc_request_buf(req)

def show_ptlrpc_set(s) :
    print("set %x new %d remaining %d" % (s,
        s.set_new_count.counter, s.set_remaining.counter))
    i = 0
    head = s.set_requests

    rq_info = getStructInfo('struct ptlrpc_request')
    try:
        offset = rq_info['rq_set_chain'].offset
    except KeyError:
        cli_rq_info = getStructInfo('struct ptlrpc_cli_req')
        offset = rq_info['rq_cli'].offset + cli_rq_info['cr_set_chain'].offset

    while head.next != s.set_requests :
        head = head.next
        req = readSU("struct ptlrpc_request", int(head) - offset)
        show_ptlrpc_request(req)
        i = i + 1
        if i == max_req :
            break

def show_import(prefix, imp) :
    jiffies = readSymbol("jiffies")
    if imp.imp_conn_current != 0 :
        cur_nid = nid2str(imp.imp_conn_current.oic_conn.c_peer.nid)
    else :
        cur_nid = "null"
    print("%simport %x %s inflight %d %s cur conn: %s next ping in %s" %
          (prefix, imp, imp.imp_obd.obd_name, imp.imp_inflight.counter,
           lustre_imp_state.__getitem__(imp.imp_state), cur_nid,
           j_delay(jiffies, imp.imp_next_ping)))
    if imp.imp_state != lustre_imp_state.LUSTRE_IMP_FULL :
        idx = imp.imp_state_hist_idx
        size = 16
        time = 0
        for i in range(0, size) :
            if (imp.imp_state_hist[(idx - i -1) % size].ish_state ==
                    lustre_imp_state.LUSTRE_IMP_FULL) :
                time = imp.imp_state_hist[(idx - i -1) % size].ish_time
                break

        if time != 0 :
            print("%slast FULL was %ss ago" % (prefix, get_seconds() - time))
        else :
            print("%slast FULL was never" % prefix)
        connections = readSUListFromHead(imp.imp_conn_list, "oic_item", "struct obd_import_conn")
        for conn in connections :
            print("%s%s tried %s ago" % (prefix, nid2str(conn.oic_conn.c_peer.nid),
                    j_delay(conn.oic_last_attempt, jiffies)))
        if imp.imp_no_pinger_recover == 1 :
            print("imp_no_pinger_recover == 1 !!!!")

def imp_show_history(imp) :
        replay_list = readSUListFromHead(imp.imp_replay_list, "rq_replay_list", "struct ptlrpc_request")
        for req in replay_list :
            print(req)
            show_ptlrpc_request_buf(req)

def show_ptlrpcd_ctl(ctl) :
    pc_set = ctl.pc_set
    show_ptlrpc_set(ctl.pc_set)

def show_ptlrpcds() :
    try:
        ptlrpcds_num = readSymbol("ptlrpcds_num")
    except TypeError:
        ptlrpcds_num = 1
    ptlrpcds = readSymbol("ptlrpcds")
    for i in range(0, ptlrpcds_num) :
        print("cpt %d" % i)
        ptlrpcd = ptlrpcds[i]
        for t in range(0, ptlrpcd.pd_nthreads) :
            show_ptlrpcd_ctl(ptlrpcd.pd_threads[t])

    print("recovery:");
    try:
        ptlrpcd_rcv = readSymbol("ptlrpcd_rcv")
    except TypeError:
        ptlrpcd_rcv = ptlrpcds[0].pd_thread_rcv
    show_ptlrpcd_ctl(ptlrpcd_rcv)

if ( __name__ == '__main__'):
    import argparse

    parser =  argparse.ArgumentParser()
    parser.add_argument("-r","--request", dest="req", default = 0)
    parser.add_argument("-s","--set", dest="set", default = 0)
    parser.add_argument("-n","--num", dest="n", default = 0)
    parser.add_argument("-i","--import", dest="imp", default = 0)
    args = parser.parse_args()
    if args.n != 0 :
        max_req = n
    if args.req != 0 :
        req = readSU("struct ptlrpc_request", int(args.req, 0))
        show_ptlrpc_request(req)
    elif args.set != 0 :
        s = readSU("struct ptlrpc_request_set", int(args.set, 0))
        show_ptlrpc_set(s)
    elif args.imp != 0 :
        imp = readSU("struct obd_import", int(args.imp, 0))
        imp_show_history(imp)
    else :
        show_ptlrpcds()
