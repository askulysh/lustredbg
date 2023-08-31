# ptlrpc functions

from __future__ import print_function
from functools import lru_cache

from pykdump.API import *
from ktime import *
from lnet import *
import ldlm_lock as ldlm
import osd as osd
from LinuxDump.BTstack import (_get_threads_subroutines, exec_bt)
import LinuxDump.fregsapi as fregsapi
import LinuxDump.KernLocks as kernlocks
from LinuxDump import Tasks
import re
import lustrelib as ll

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

pb_flags_c = '''
#define MSG_RESENT		0x0002 /* was previously sent, no reply seen */
#define MSG_REPLAY		0x0004 /* was processed, got reply, recovery */
#define MSG_AT_SUPPORT	0x0008 obsolete since 1.5, AT always enabled */
#define MSG_DELAY_REPLAY	0x0010 obsolete since 2.0 */
#define MSG_VERSION_REPLAY	0x0020 obsolete since 1.8.2, VBR always on */
#define MSG_REQ_REPLAY_DONE	0x0040 /* request replay over, locks next */
#define MSG_LOCK_REPLAY_DONE	0x0080 /* lock replay over, client done */
'''
pb_flags = CDefine(pb_flags_c)

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
        OST_LADVISE    = 21,
        OST_FALLOCATE  = 22,
        OST_SEEK       = 23,
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
        LDLM_SET_INFO    = 107,

	MGS_CONNECT	= 250,
	MGS_DISCONNECT	= 251,
	MGS_EXCEPTION	= 252,
	MGS_TARGET_REG	= 253,
	MGS_TARGET_DEL	= 254,
	MGS_SET_INFO	= 255,
	MGS_CONFIG_READ	= 256,

	OBD_PING	 = 400,

        LLOG_ORIGIN_HANDLE_CREATE       = 501,
        LLOG_ORIGIN_HANDLE_NEXT_BLOCK   = 502,
        LLOG_ORIGIN_HANDLE_READ_HEADER  = 503,
        LLOG_ORIGIN_HANDLE_WRITE_REC    = 504,
        LLOG_ORIGIN_HANDLE_CLOSE        = 505,
        LLOG_ORIGIN_CONNECT             = 506,
	LLOG_CATINFO			= 507,
        LLOG_ORIGIN_HANDLE_PREV_BLOCK   = 508,
        LLOG_ORIGIN_HANDLE_DESTROY      = 509,

	QUOTA_DQACQ	= 601,
	QUOTA_DQREL	= 602,

    SEQ_QUERY   = 700,

	FLD_QUERY	= 900,
	FLD_READ	= 901,

	OUT_UPDATE	 = 1000
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
	REINT_RMENTRY  = 8,
	REINT_MIGRATE  = 9
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
#define IT_TRUNC    0x0040
#define IT_GETXATTR 0x0080
#define IT_EXEC     0x0100
#define IT_PIN      0x0200
#define IT_LAYOUT   0x0400
#define IT_QUOTA_DQACQ 0x0800
#define IT_QUOTA_CONN  0x1000
#define IT_SETXATTR 0x2000
#define IT_GLIMPSE  0x4000
#define IT_BRW	    0x8000
'''
it_flags = CDefine(it_flags_c)

mdt_it_code_c = '''
enum {
        MDT_IT_OPEN,
        MDT_IT_OCREAT,
        MDT_IT_CREATE,
        MDT_IT_GETATTR,
        MDT_IT_READDIR,
        MDT_IT_LOOKUP,
        MDT_IT_UNLINK,
        MDT_IT_TRUNC,
        MDT_IT_GETXATTR,
        MDT_IT_LAYOUT,
        MDT_IT_QUOTA,
        MDT_IT_GLIMPSE,
        MDT_IT_BRW,
        MDT_IT_NR
};
'''
mdt_it_code = CEnum(mdt_it_code_c)

def mdt_intent_code(itcode) :
    rc = -1
    if itcode == it_flags.IT_OPEN:
        rc = mdt_it_code.MDT_IT_OPEN
    elif itcode == it_flags.IT_OPEN|it_flags.IT_CREAT:
        rc = mdt_it_code.MDT_IT_OCREAT
    elif itcode == it_flags.IT_CREAT:
        rc = mdt_it_code.MDT_IT_CREATE
    elif itcode == it_flags.IT_READDIR:
        rc = mdt_it_code.MDT_IT_READDIR
    elif itcode == it_flags.IT_GETATTR:
        rc = mdt_it_code.MDT_IT_GETATTR
    elif itcode == it_flags.IT_LOOKUP:
        rc = mdt_it_code.MDT_IT_LOOKUP
    elif itcode == it_flags.IT_UNLINK:
        rc = mdt_it_code.MDT_IT_UNLINK
    elif itcode == it_flags.IT_TRUNC:
        rc = mdt_it_code.MDT_IT_TRUNC
    elif itcode == it_flags.IT_GETXATTR:
        rc = mdt_it_code.MDT_IT_GETXATTR
    elif itcode == it_flags.IT_LAYOUT:
        rc = mdt_it_code.MDT_IT_LAYOUT
    elif itcode == it_flags.IT_QUOTA_DQACQ:
        rc = mdt_it_code.MDT_IT_QUOTA
    elif itcode == it_flags.IT_QUOTA_CONN:
        rc = mdt_it_code.MDT_IT_QUOTA
    elif itcode == it_flags.IT_GLIMPSE:
        rc = mdt_it_code.MDT_IT_GLIMPSE
    elif itcode == it_flags.IT_BRW:
        rc = mdt_it_code.MDT_IT_BRW
    return rc;

intent_fmts = [0 for i in range(mdt_it_code.MDT_IT_NR)]
intent_fmts[mdt_it_code.MDT_IT_OPEN] = "RQF_LDLM_INTENT_OPEN"
intent_fmts[mdt_it_code.MDT_IT_OCREAT] = "RQF_LDLM_INTENT_OPEN"
intent_fmts[mdt_it_code.MDT_IT_CREATE] = "RQF_LDLM_INTENT_CREATE"
intent_fmts[mdt_it_code.MDT_IT_GETATTR] = "RQF_LDLM_INTENT_GETATTR"
intent_fmts[mdt_it_code.MDT_IT_LOOKUP] = "RQF_LDLM_INTENT_GETATTR"
intent_fmts[mdt_it_code.MDT_IT_UNLINK] = "RQF_LDLM_INTENT_UNLINK"
intent_fmts[mdt_it_code.MDT_IT_GETXATTR] = "RQF_LDLM_INTENT_GETXATTR"
intent_fmts[mdt_it_code.MDT_IT_LAYOUT] = "RQF_LDLM_INTENT_LAYOUT"
intent_fmts[mdt_it_code.MDT_IT_GLIMPSE] = "RQF_LDLM_INTENT"
intent_fmts[mdt_it_code.MDT_IT_BRW] = "RQF_LDLM_INTENT"

reint_fmts = [0 for i in range(10)]
reint_fmts[mds_reint.REINT_SETATTR] = "RQF_MDS_REINT_SETATTR"
reint_fmts[mds_reint.REINT_CREATE] = "RQF_MDS_REINT_CREATE_ACL"
reint_fmts[mds_reint.REINT_LINK] = "RQF_MDS_REINT_LINK"
reint_fmts[mds_reint.REINT_UNLINK] = "RQF_MDS_REINT_UNLINK"
reint_fmts[mds_reint.REINT_RENAME] = "RQF_MDS_REINT_RENAME"
reint_fmts[mds_reint.REINT_OPEN] = "RQF_MDS_REINT_OPEN"
reint_fmts[mds_reint.REINT_SETXATTR] = "RQF_MDS_REINT_SETXATTR"
reint_fmts[mds_reint.REINT_RMENTRY] = "RQF_MDS_REINT_UNLINK"
reint_fmts[mds_reint.REINT_MIGRATE] = "RQF_MDS_REINT_MIGRATE"

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
        LUSTRE_IMP_EVICTED    = 10,
        LUSTRE_IMP_IDLE       = 11
};
'''
lustre_imp_state = CEnum(lustre_imp_state_c)

update_type_c = '''
enum update_type {
	OUT_START		= 0,
	OUT_CREATE		= 1,
	OUT_DESTROY		= 2,
	OUT_REF_ADD		= 3,
	OUT_REF_DEL		= 4,
	OUT_ATTR_SET		= 5,
	OUT_ATTR_GET		= 6,
	OUT_XATTR_SET		= 7,
	OUT_XATTR_GET		= 8,
	OUT_INDEX_LOOKUP	= 9,
	OUT_INDEX_INSERT	= 10,
	OUT_INDEX_DELETE	= 11,
	OUT_WRITE		= 12,
	OUT_XATTR_DEL		= 13,
	OUT_PUNCH		= 14,
	OUT_READ		= 15,
	OUT_NOOP		= 16,
	OUT_XATTR_LIST		= 17,
	OUT_LAST                = 18
};
'''
update_type = CEnum(update_type_c)

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
    if msg == 0 :
        return None
    bufcount = msg.lm_bufcount
    offset = (8*4 + (bufcount )*4 + 7) & (~0x7)
    a = int(msg) + offset
    for i in range(0, n) :
        a += ((msg.lm_buflens[i] + 7) & (~7))

    return a

def get_req_msg(req) :
    try :
        msg = req.rq_reqmsg
    except:
        msg = req.rq_pill.rc_reqmsg
    return msg

def get_req_buffer(req, n) :
    return get_msg_buffer(get_req_msg(req), n)

def get_rep_buffer(req, n) :
    return get_msg_buffer(get_rep_msg(req), n)

def get_rep_msg(req) :
    try :
        msg = req.rq_repmsg
    except:
        msg = req.rq_pill.rc_repmsg
    return msg

def fid2str(fid) :
    return "[0x%x:0x%x:0x%x]" % (fid.f_seq, fid.f_oid, fid.f_ver)

def mtd_reint_show(reint) :
    if reint.rr_opcode == mds_reint.REINT_UNLINK :
        rec = readSU("struct mdt_rec_unlink", int(reint))
        print("%s unlink %s/name" % (rec, fid2str(rec.ul_fid1)))
    elif reint.rr_opcode == mds_reint.REINT_RENAME :
        rec = readSU("struct mdt_rec_rename", int(reint))
        print("%s rename %s/name -> %s/symtgt" % (rec, fid2str(rec.rn_fid1),
            fid2str(rec.rn_fid2)))
    elif reint.rr_opcode == mds_reint.REINT_OPEN :
        rec = readSU("struct mdt_rec_create", int(reint))
        print("%s open   %s/%s %s" % (rec, fid2str(rec.cr_fid1),
            fid2str(rec.cr_fid2), dbits2str(rec.cr_flags_l, mds_open_flags)))
    elif reint.rr_opcode == mds_reint.REINT_CREATE :
        rec = readSU("struct mdt_rec_create", int(reint))
        print("%s create   %s/%s %s" % (rec, fid2str(rec.cr_fid1),
            fid2str(rec.cr_fid2), dbits2str(rec.cr_flags_l, mds_open_flags)))
    elif reint.rr_opcode == mds_reint.REINT_MIGRATE :
        rec = readSU("struct mdt_rec_rename", int(reint))
        print("%s migrate %s/name -> %s" % (rec, fid2str(rec.rn_fid1),
            fid2str(rec.rn_fid2)))
    else :
        if reint.rr_opcode != 0 :
            print("%s %s %s" % (reint, mds_reint.__getitem__(reint.rr_opcode), fid2str(reint.rr_fid1)))

def mdt_body_show(prefix, body) :
    out = ""
    try:
#    out += "valid " + dbits2str(body.valid, obd_md_flags)
        if body.valid & obd_md_flags.OBD_MD_FLID :
            out += fid2str(body.fid1)
        if body.valid & obd_md_flags.OBD_MD_FLSIZE :
            out += " sz:%s" % body.size
        if body.valid & obd_md_flags.OBD_MD_FLMODE :
            out += " mode:%o" % (body.mode & (~(0xf000)))
        if body.valid & obd_md_flags.OBD_MD_FLTYPE :
            out += " type:%x" % (body.mode & 0xf000)
    except:
        if body.mbo_valid & obd_md_flags.OBD_MD_FLID :
            out += fid2str(body.mbo_fid1)
        if body.mbo_valid & obd_md_flags.OBD_MD_FLSIZE :
            out += " sz:%s" % body.mbo_size
        if body.mbo_valid & obd_md_flags.OBD_MD_FLMODE :
            out += " mode:%o" % (body.mbo_mode & (~(0xf000)))
        if body.mbo_valid & obd_md_flags.OBD_MD_FLTYPE :
            out += " type:%x" % (body.mbo_mode & 0xf000)

    if len(out) > 1 :
        print(prefix, out)

def ost_body_show(prefix, body) :
    print("%s %s" % (prefix, fid2str(body.oa.o_oi.oi_fid)))

def print_update(fmt, ou) :
    print(fmt, ou, update_type.__getitem__(ou.ou_type), fid2str(ou.ou_fid))

def print_update_req(fmt, our) :
    print(fmt, our)
    ou = readSU("struct object_update", our.ourq_updates)
    print_update(fmt, ou)
#    for i in range(0, our.ourq_count) :

def show_request_loc(req, req_format, location) :
    for i in range(0, req_format.rf_fields[location].nr) :
        req_msg_field = readSU("struct req_msg_field",
                req_format.rf_fields[location].d[i])
        offset = req_msg_field.rmf_offset[req_format.rf_idx][location]
        if location == 0 :
            msg = get_req_msg(req)
        else :
            msg = get_rep_msg(req)
            if msg == 0 :
                print("no reply buffer");
                return

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
        elif name == "name" or name == "symtgt":
            s = msg.lm_buflens[i+1]
            if s > 0 :
                if s > 256 :
                    l = 256
                else :
                    l = s
                ss = ""
                mem = readmem(buf, l)
                for i in range(0,l) :
                    if mem[i] != 0:
                        ss = ss +chr(mem[i])
                    else :
                        break
            else:
                ss = ""
            print("  offset %d %s size %d \"%s\"" % (offset, name, s, ss))
            name = 0

        if name :
            try:
               field = readSU("struct " + name, buf)
               if req_msg_field.rmf_flags & 4 : # array
                   array  = "x %d" % (msg.lm_buflens[i] / req_msg_field.rmf_size)
               else :
                   array = ""
               print("  offset %d %s %s %s" % (offset, req_msg_field.rmf_name, field, array))
            except TypeError :
                name = 0

        if name == 0 :
            print("  offset %d %s size %d %x" %
                  (offset, req_msg_field.rmf_name, msg.lm_buflens[i+1], buf))

        if name == "mdt_rec_reint":
            mtd_reint_show(field)
        elif name == "mdt_body":
            mdt_body_show("   ", field)
        elif name == "ost_body":
            ost_body_show("   ", field)
        elif name == "niobuf_remote":
            print("   ", field.rnb_offset, field.rnb_offset + field.rnb_len)
        elif name == "ldlm_intent":
            print("  offset %d %s %s" % (offset,    field, dbits2str(field.opc, it_flags)))
        elif name == "ldlm_request":
            ldlm.print_ldlm_request("   ", field)
        elif name == "ldlm_reply":
            ldlm.print_ldlm_reply("   ", field)
        elif name == "out_update_header" and field.ouh_inline_length > 0 :
            our = readSU("struct object_update_request",
                    field.ouh_inline_data)
            print_update_req("   ", our)

def show_request_fmt(req, fmt) :
    req_format = readSymbol(fmt)
    print("request:")
    show_request_loc(req, req_format, 0)
    print("reply:")
    show_request_loc(req, req_format, 1)

def get_req_body(req) :
    return readSU("struct ptlrpc_body_v3", get_req_buffer(req, 0))

def get_opc(req) :
    return get_req_body(req).pb_opc

def get_pid(req) :
    return get_req_body(req).pb_status

def show_ptlrpc_request_buf(req) :
    if req.rq_pill.rc_fmt == sym2addr("worker_format") :
        print("osc worker request")
        return

    b = get_req_buffer(req, 0)
    if not b :
        return
    body = readSU("struct ptlrpc_body_v3", b)
    print("opc %s transno %d tag %d conn %d %s pid/status %d job %s" %
          (opcodes.__getitem__(body.pb_opc), body.pb_transno, body.pb_tag,
           body.pb_conn_cnt, dbits2str(body.pb_flags, pb_flags),
           body.pb_status, body.pb_jobid))
    if body.pb_opc == opcodes.LDLM_ENQUEUE :
        ldlm_req = readSU("struct ldlm_request", get_req_buffer(req, 1))
        if ldlm_req.lock_desc.l_resource.lr_type == ldlm.ldlm_types.LDLM_IBITS and ldlm_req.lock_flags & ldlm.LDLM_flags.LDLM_FL_HAS_INTENT :
            intent = readSU("struct ldlm_intent", get_req_buffer(req, 2))
            it = mdt_intent_code(intent.opc)
            if it != -1 :
                show_request_fmt(req, intent_fmts[it])
            else :
                try :
                    show_request_fmt(req, "RQF_LDLM_INTENT")
                except:
                    print(body)
                    print(ldlm_req)
                    print(intent)
        else:
            show_request_fmt(req, "RQF_LDLM_ENQUEUE")
    elif body.pb_opc == opcodes.LDLM_CONVERT :
        show_request_fmt(req, "RQF_LDLM_CONVERT")
    elif body.pb_opc == opcodes.LDLM_CANCEL :
        show_request_fmt(req, "RQF_LDLM_CANCEL")
    elif body.pb_opc == opcodes.LDLM_BL_CALLBACK :
        show_request_fmt(req, "RQF_LDLM_BL_CALLBACK")
    elif body.pb_opc == opcodes.LDLM_CP_CALLBACK :
        show_request_fmt(req, "RQF_LDLM_CP_CALLBACK")
    elif body.pb_opc == opcodes.MDS_REINT :
        reint = readSU("struct mdt_rec_reint", get_req_buffer(req, 1))
        show_request_fmt(req, reint_fmts[reint.rr_opcode])
    elif body.pb_opc == opcodes.MDS_CONNECT :
        show_request_fmt(req, "RQF_MDS_CONNECT")
    elif body.pb_opc == opcodes.OST_CONNECT :
        show_request_fmt(req, "RQF_OST_CONNECT")
    elif body.pb_opc == opcodes.MDS_GETATTR :
        show_request_fmt(req, "RQF_MDS_GETATTR")
    elif body.pb_opc == opcodes.MDS_GETXATTR :
        show_request_fmt(req, "RQF_MDS_GETXATTR")
    elif body.pb_opc == opcodes.MDS_CLOSE :
        show_request_fmt(req, "RQF_MDS_CLOSE")
    elif body.pb_opc == opcodes.MDS_HSM_PROGRESS :
        show_request_fmt(req, "RQF_MDS_HSM_PROGRESS")
    elif body.pb_opc == opcodes.OST_SETATTR :
        show_request_fmt(req, "RQF_OST_SETATTR")
    elif body.pb_opc == opcodes.OST_READ :
        show_request_fmt(req, "RQF_OST_BRW_READ")
    elif body.pb_opc == opcodes.OST_WRITE :
        show_request_fmt(req, "RQF_OST_BRW_WRITE")
    elif body.pb_opc == opcodes.OST_CREATE :
        show_request_fmt(req, "RQF_OST_CREATE")
    elif body.pb_opc == opcodes.OST_DESTROY :
        show_request_fmt(req, "RQF_OST_DESTROY")
    elif body.pb_opc == opcodes.OST_PUNCH :
        show_request_fmt(req, "RQF_OST_PUNCH")
    elif body.pb_opc == opcodes.OST_LADVISE :
        show_request_fmt(req, "RQF_OST_LADVISE")
    elif body.pb_opc == opcodes.OST_FALLOCATE :
        show_request_fmt(req, "RQF_OST_FALLOCATE")
    elif body.pb_opc == opcodes.OST_SEEK :
        show_request_fmt(req, "RQF_OST_SEEK")
    elif body.pb_opc == opcodes.FLD_QUERY :
        show_request_fmt(req, "RQF_FLD_QUERY")
    elif body.pb_opc == opcodes.FLD_READ :
        show_request_fmt(req, "RQF_FLD_READ")
    elif body.pb_opc == opcodes.OUT_UPDATE :
        show_request_fmt(req, "RQF_OUT_UPDATE")

def exp_cl_str(exp) :
    if not exp :
        return ""
    if exp.exp_imp_reverse != 0 :
        conn = exp.exp_imp_reverse.imp_connection
    else :
        conn = exp.exp_connection
    return "%s@%s" % (exp.exp_client_uuid.uuid, nid2str(conn.c_peer.nid))

def req_client(req) :
    if req.rq_export != 0:
        return exp_cl_str(req.rq_export)
    return "@%s" % nid2str(req.rq_peer.nid)

def show_ptlrpc_request_header(req) :
    print("req@%x x%d %s %4d %s %s hp:%d" %
          (req, req.rq_xid, req_sent(req), req.rq_status,
           phase2str(req.rq_phase), print_req_flags(req), req.rq_hp))

def show_ptlrpc_request(req) :
    show_ptlrpc_request_header(req)
    if req.rq_import != 0:
        show_import("  ", req.rq_import)
    else :
        print(req_client(req))
        print("arrived",
              get_seconds() - req.rq_srv.sr_arrival_time.tv_sec, "sec ago")

    show_ptlrpc_request_buf(req)

    if req.rq_status == -75 :
        print()
        print("versions:", get_req_body(req).pb_pre_versions)

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

def imp_show_state_history(prefix, imp):
    idx = imp.imp_state_hist_idx
    size = 16
    for i in range(0, size) :
        j = (idx - i - 1) % size
        if imp.imp_state_hist[j].ish_state == 0 :
            break
        print("%s%s\t%d\t%d ago" % (prefix,
            lustre_imp_state.__getitem__(imp.imp_state_hist[j].ish_state),
            imp.imp_state_hist[j].ish_time,
            get_seconds() - imp.imp_state_hist[j].ish_time))

def show_import(prefix, imp) :
    if imp.imp_connection != 0 :
        cur_nid = nid2str(imp.imp_connection.c_peer.nid)
    else :
        cur_nid = "null"
    cli_obd = imp.imp_obd.u.cli
    print("%simport %x %s inflight %d mod slots %d/%d %s cur conn: %s last reply %ds next ping in %s" %
          (prefix, imp, imp.imp_obd.obd_name, imp.imp_inflight.counter,
           cli_obd.cl_mod_rpcs_in_flight, cli_obd.cl_max_mod_rpcs_in_flight,
           lustre_imp_state.__getitem__(imp.imp_state), cur_nid,
           get_seconds() - imp.imp_last_reply_time,
           imp.imp_next_ping - ktime_get_seconds()))
    if imp.imp_state != lustre_imp_state.LUSTRE_IMP_FULL :
        idx = imp.imp_state_hist_idx
        size = 16
        time_connected = 0
        time_disconnected = 0
        for i in range(0, size) :
            j = (idx - i - 1) % size
            state = imp.imp_state_hist[j].ish_state
            if state == lustre_imp_state.LUSTRE_IMP_DISCON :
                time_disconnected = imp.imp_state_hist[j].ish_time
            if state == lustre_imp_state.LUSTRE_IMP_FULL :
                time_connected = imp.imp_state_hist[j].ish_time
                break

        if time_connected != 0 :
            print("%slast FULL was %ds ago disconnected %ds" %
                    (prefix, get_seconds() - time_connected,
                        get_seconds() - time_disconnected))
        elif imp.imp_state == lustre_imp_state.LUSTRE_IMP_EVICTED :
            j = (idx + 1) % size
            print("%slast success connect was > %ds ago" %
                    (prefix, get_seconds() - imp.imp_state_hist[j].ish_time))
        else :
            print("%slast success connect was %ds ago" %
                    (prefix, ktime_get_seconds() - imp.imp_last_success_conn))
        connections = readSUListFromHead(imp.imp_conn_list, "oic_item", "struct obd_import_conn")
        for conn in connections :
            print("%s%s tried %s ago" % (prefix, nid2str(conn.oic_conn.c_peer.nid),
                    ktime_get_seconds() - conn.oic_last_attempt))
        if imp.imp_no_pinger_recover == 1 :
            print("imp_no_pinger_recover == 1 !!!!")

def show_requests_from_list_reverse(head, offset):
    entry = head
    while entry.prev != head :
        entry = entry.prev
        req = readSU("struct ptlrpc_request", int(entry) - offset)
        if req.rq_srv_req == 1 and req.rq_srv.sr_svc_thread != 0 :
            pid = req.rq_srv.sr_svc_thread.t_pid
            show_pid(pid, None)
        else:
            show_ptlrpc_request(req)
        print()

def show_requests_from_list(l) :
    for req in l :
        show_ptlrpc_request_header(req)
        show_ptlrpc_request_buf(req)

def imp_show_sending_requests(imp) :
    print("\n=== sending ===")
    l = readSUListFromHead(imp.imp_sending_list, "rq_list", "struct ptlrpc_request")
    show_requests_from_list(l)

def imp_show_unreplied_requests(imp) :
    print("\n=== unreplied ===")
    head = imp.imp_unreplied_list
    rq_info = getStructInfo('struct ptlrpc_request')
    cli_rq_info = getStructInfo('struct ptlrpc_cli_req')
    offset = rq_info['rq_cli'].offset + cli_rq_info['cr_unreplied_list'].offset

    entry = imp.imp_unreplied_list
    while entry.prev != imp.imp_unreplied_list :
        entry = entry.prev
        req = readSU("struct ptlrpc_request", int(entry) - offset)
        # RPC state
        if req.rq_phase == -339681791 :
            show_ptlrpc_request(req)

def imp_show_requests(imp) :
    imp_show_sending_requests(imp)

    print("\n=== delayed ===")
    l = readSUListFromHead(imp.imp_delayed_list, "rq_list", "struct ptlrpc_request")
    show_requests_from_list(l)

    imp_show_unreplied_requests(imp)

def imp_show_history(imp) :
    print("replay list:")
    replay_list = readSUListFromHead(imp.imp_replay_list, "rq_replay_list", "struct ptlrpc_request")
    show_requests_from_list(replay_list)

def show_export_hdr(prefix, exp) :
    print(exp.exp_obd, exp.exp_obd.obd_name)
    print("%s %u.%u.%u.%u" % (exp_cl_str(exp),
        (exp.exp_connect_data.ocd_version >> 24) & 255,
        (exp.exp_connect_data.ocd_version >> 16) & 255,
        (exp.exp_connect_data.ocd_version >> 8) & 255,
        (exp.exp_connect_data.ocd_version >> 24) & 255))
    print("conn_cnt", exp.exp_conn_cnt,
            "last_committed", exp.exp_last_committed,
            "last_xid", exp.exp_last_xid)
    print("requests:")
    print("total %d last req %d sec ago" % (exp.exp_rpc_count.counter,
        get_seconds() - exp.exp_last_request_time))
    try:
       print("used slots %t" % exp.exp_used_slots)
    except:
        print("")

def list_empty(head) :
    return head.prev == head

def show_export(prefix, exp) :
    show_export_hdr(prefix, exp)
    reply_list = readSUListFromHead(exp.u.eu_target_data.ted_reply_list,
            "trd_list", "struct tg_reply_data")
    for trd in reply_list :
        print("tag: ", trd.trd_tag, "xid:", trd.trd_reply.lrd_xid,
              "transno", trd.trd_reply.lrd_transno,
              "gen", trd.trd_reply.lrd_client_gen, fid2str(trd.trd_object),
              trd.trd_pre_versions)

    rq_info = getStructInfo('struct ptlrpc_request')
    srv_rq_info = getStructInfo('struct ptlrpc_srv_req')
    offset = rq_info['rq_srv'].offset + srv_rq_info['sr_exp_list'].offset

    if not list_empty(exp.exp_hp_rpcs) :
        print("HP requests:")
        show_requests_from_list_reverse(exp.exp_hp_rpcs, offset)
    if not list_empty(exp.exp_reg_rpcs) :
        print("Regular requests:")
        show_requests_from_list_reverse(exp.exp_reg_rpcs, offset)

#    print("\nlocks:")
#    for hn in ll.cfs_hash_get_nodes(exp.exp_lock_hash) :
#        lock_addr = Addr(hn) -  member_offset('struct ldlm_lock', 'l_exp_hash')
#        lock = readSU("struct ldlm_lock", lock_addr)
#        print_ldlm_lock(lock, "")

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

def search_stack_for_reg(r, stacklist, func) :
    try :
        for s in stacklist:
            for f in s.frames:
                if f.func == func :
                    return f.reg[r][0]
    except KeyError :
        return 0
    return 0

def stack_has_func(stacklist, func) :
    for s in stacklist:
        for f in s.frames:
            if f.func == func :
                return True
    return False

@memoize_cond(CU_LIVE)
def get_stacklist(pid) :
    #     with DisasmFlavor('att'):
    try:
        stacklist = exec_bt("bt %d" % pid, MEMOIZE=False)
        for s in stacklist:
            fregsapi.search_for_registers(s)

    except:
        print("Unable to get stack trace")
        return None
    return stacklist

def search_for_reg(r, pid, func) :
    stacklist = get_stacklist(pid)
    if stacklist:
        return search_stack_for_reg(r, stacklist, func)
    return None

def search_for_rw_semaphore(stack) :
    addr = search_stack_for_reg("RDI", stack, "call_rwsem_down_write_failed")
    if addr == 0:
        addr = search_stack_for_reg("RDI", stack, "rwsem_down_write_slowpath")
    if addr == 0:
        addr = search_stack_for_reg("RDI", stack, "rwsem_down_read_slowpath")
    if addr == 0:
        addr = search_stack_for_reg("RDI", stack, "down_read")
    if addr == 0:
        return None
    print()
    sem = readSU("struct rw_semaphore", addr)
    if sys_info.kernel == "4.18.0" :
        owner = sem.rh_kabi_hidden_39.owner & (~0xf)
    else:
        owner = sem.owner & (~1)
    print(sem, "counter: %lx owner: %x" % (sem.count.counter, owner))

    return readSU("struct task_struct", owner)

def search_for_mutex(stack) :
    addr = search_stack_for_reg("RDI", stack, "__mutex_lock_slowpath")
    if addr == 0:
        addr = search_stack_for_reg("RDI", stack, "__mutex_lock")
    if addr == 0:
        return None
    print()
    mut = readSU("struct mutex", addr)
    if sys_info.kernel == "4.18.0" :
        owner = readU64(addr) & (~0xf)
        print(mut, "counter: owner: %x %x" % (mut.owner.counter, owner))
    try:
        owner = mut.owner
        kernlocks.decode_mutex(mut)
    except:
        pass

    return readSU("struct task_struct", owner)

def get_lu_env(stack) :
    addr = search_stack_for_reg("RDI", stack, "osd_trans_stop")
    if addr == 0 :
        addr = search_stack_for_reg("RDI", stack, "ofd_commitrw")
    if addr == 0 :
        addr = search_stack_for_reg("RDI", stack, "ofd_commitrw_write")
    if addr == 0 :
        return None
    return readSU("struct lu_env", addr)

def show_io_time(lu_env) :
    oti = osd.osd_oti_get(lu_env)
    iobuf = oti.oti_iobuf
    print(iobuf, "dr_numreqs", iobuf.dr_numreqs.counter)
    if iobuf.dr_numreqs.counter != 0 :
        print("waiting for ", ktime_diff(iobuf.dr_start_time))

def task_time_diff(task, t) :
    d = task.se.cfs_rq.rq.clock-task.sched_info.last_arrival
    return d/1000000000

def show_range_lock(rl) :
    try :
        print(rl, '[',rl.rl_start, '-', rl.rl_end,']')
    except:
        print(rl, '[',rl.rl_node.in_extent.start, '-', rl.rl_node.in_extent.end,']')

def show_pid(pid, pattern) :
    stack = get_stacklist(pid)
    if not stack:
        return None

    req = get_request(stack)
    if not req :
        return None

    if pattern == None or pattern.match(req_client(req)) :
        print("PID", pid)
        if sys_info.kernel == "3.10.0" :
            addr = search_stack_for_reg("RBP", stack, "tgt_request_handle")
            if addr != 0 :
                print(readS64(addr - 0x30))
                print(readS64(addr - 0x38))
        if sys_info.kernel == "4.18.0" :
            work_start = search_stack_for_reg("R12", stack, "tgt_request_handle")
            print(work_start, get_seconds() - work_start / 1000000000)
        show_ptlrpc_request(req)
        thread = req.rq_srv.sr_svc_thread
        jiffies = readSymbol("jiffies")
        try:
            touched = thread.t_watchdog.lcw_last_touched
            print("watchdog touched", j_delay(touched, jiffies), "ago")
        except KeyError:
            touched = thread.t_touched
            print("watchdog touched", ktime_diff(touched), "ago")
        try :
            print("last arrival", task_time_diff(thread.t_task,
                    thread.t_task.sched_info.last_arrival), "sec ago")
            print("exec start", task_time_diff(thread.t_task,
                    thread.t_task.se.exec_start), "sec ago")
            T_table = TaskTable()
            task = Task(thread.t_task, T_table.getByPid(pid))
            print(task)
            print(task.Ran_ago)
        except:
            pass

        lu_env = get_lu_env(stack)

        if lu_env and stack_has_func(stack, "osd_trans_stop") :
            print()
            show_io_time(lu_env)

        addr = search_stack_for_reg("RSI", stack, "range_lock")
        if addr != 0 :
            print()
            rlock = readSU("struct range_lock", addr)
            print("waiting on range lock:")
            show_range_lock(rlock)

        if lu_env and stack_has_func(stack, "ofd_commitrw") :
            print()
            ofd_key = readSymbol("ofd_thread_key")
            ofd_info = readSU("struct ofd_thread_info",
                                      lu_env.le_ctx.lc_value[ofd_key.lct_index])
            try :
                if ofd_info.fti_range_locked :
                    print("owns range_lock :")
                    show_range_lock(ofd_info.fti_write_range)
            except:
                pass


        addr = search_stack_for_reg("RSI", stack, "__wait_on_bit_lock")
        if addr != 0 :
            print()
            wb = readSU("struct wait_bit_queue", addr)
            page = readSU("struct page", wb.key.flags)
            print(page, "idx:", page.index)

        addr = search_stack_for_reg("RDI", stack, "bit_wait_io")
        if addr != 0 :
            print()
            wbk = readSU("struct wait_bit_key", addr)
            print("addr: %x" % wbk.flags, "bit:", wbk.bit_nr, "timeout:", wbk.timeout)
            try :
                bh = readSU("struct buffer_head", wbk.flags)
                page = readSU("struct page", bh.b_page)
                print(bh, page, "idx:", page.index)
            except:
                pass

        addr = search_stack_for_reg("RSI", stack, "jbd2_journal_get_write_access")
        if addr != 0 :
            print()
            bh = readSU("struct buffer_head", addr)
            page = readSU("struct page", bh.b_page)
            if sys_info.kernel == "3.10.0" :
                start_lock = search_stack_for_reg("R14", stack, "out_of_line_wait_on_bit_lock")
            elif sys_info.kernel == "4.18.0" :
                addr = search_stack_for_reg("RDI", stack, "bit_wait_io")
                start_lock = 0
                if addr != 0 :
                    print("%x %x" % (addr, addr - 0x30))
                    try :
                        start_lock = readU64(addr - 0x30)
                    except:
                        pass
                print(start_lock)
            print("journal do_get_write_access", bh, page, "idx:", page.index,
                    "started", j_delay(start_lock, jiffies), "ago")

        search_for_rw_semaphore(stack)
        search_for_mutex(stack)

        osd.search_for_bio(stack)
        osd.search_for_transaction(stack)

        ldlm.parse_ldlm_cp_ast(stack)

        addr = search_stack_for_reg("RDX", stack, "mdt_object_local_lock")
        if addr != 0 :
            print()
            ldlm.show_mlh(readSU("struct mdt_lock_handle", addr), "")

        addr = search_stack_for_reg("RSI", stack, "osp_precreate_reserve")
        if addr != 0 :
            print()
            osp = readSU("struct osp_device", addr)
            imp = osp.opd_obd.u.cli.cl_import
            print("waiting in osp_precreate_reserve", osp)
            show_import("   ", imp)
    else :
        return None

    return req

def get_request(stack) :
    addr = search_stack_for_reg("RDI", stack, "tgt_request_handle")
    if addr == 0 :
        addr = search_stack_for_reg("RDI", stack, "ldlm_request_cancel")
    if addr == 0 :
        return None
    return readSU("struct ptlrpc_request", addr)

def get_work_arrived_time(pid) :
    req = get_request(get_stacklist(pid))
    if not req :
        return 0

    return req.rq_srv.sr_arrival_time.tv_sec

def get_work_exec_time(pid) :
    req = get_request(get_stacklist(pid))
    if not req :
        return get_seconds()
    try :
        thread = req.rq_srv.sr_svc_thread
        return thread.t_task.se.exec_start
    except:
        return 0

def get_work_start_time_3_10(pid) :
    rbp = search_for_reg("RBP", pid, "tgt_request_handle")
    if rbp == 0 :
        rbp = search_for_reg("RBP", pid, "ldlm_cancel_handler")
    if rbp == 0 :
        return 0
    return readU64(rbp-0x38)

def get_work_start_time_4_18(pid) :
    return search_for_reg("R12", pid, "tgt_request_handle")

def sort_pids_by_start_time(pids) :
    if sys_info.kernel == "3.10.0" :
        la = lambda pid : get_work_start_time_3_10(pid)
    else :
        la = lambda pid : get_work_start_time_4_18(pid)

    return sorted(pids, key=la)

def get_request_pids() :
    (funcpids, functasks, alltaskaddrs) = _get_threads_subroutines()
    return funcpids["ptlrpc_server_handle_request"]

def show_processing(pattern) :
    waiting_pids = get_request_pids()
    if pattern :
        pids=sort_pids_by_start_time(waiting_pids)
    else :
        pids=sorted(waiting_pids, key=get_work_exec_time)
        req = get_request(get_stacklist(pids[0]))
        task = False
        try :
            if req :
                task = req.rq_srv.sr_svc_thread.t_task
        except:
            pass
        if task and task_time_diff(task, task.se.exec_start) > 20 :
            print("Sorting by exec time")
        else :
            pids=sort_pids_by_start_time(waiting_pids)
    for pid in pids :
        if show_pid(pid, pattern) :
            print()

def show_cli_waiting() :
    (funcpids, functasks, alltaskaddrs) = _get_threads_subroutines()
    waiting_pids = funcpids["ptlrpc_set_wait"]
    for pid in waiting_pids :
        print("PID", pid)
        rqset = readSU("struct ptlrpc_request_set",
                search_for_reg("RSI", pid, "ptlrpc_set_wait"))
        show_ptlrpc_set(rqset)

def show_policy(policy, pattern) :
    if (policy == 0) :
        return
    print(policy, policy.pol_desc.pd_name, policy.pol_req_queued)
    fifo_head = readSU("struct nrs_fifo_head", policy.pol_private)
#    print(fifo_head)
    rq_info = getStructInfo('struct ptlrpc_request')
    srv_rq_info = getStructInfo('struct ptlrpc_srv_req')
    nrs_rq_info = getStructInfo('struct ptlrpc_nrs_request')
    offset = rq_info['rq_srv'].offset + srv_rq_info['sr_nrq'].offset + nrs_rq_info['nr_u'].offset
    head = fifo_head.fh_list
    while head.next != fifo_head.fh_list :
        head = head.next
        req = readSU("struct ptlrpc_request", int(head) - offset)
        if pattern == None or pattern.match(req_client(req)) :
            show_ptlrpc_request(req)

def find_service(name) :
    ptlrpc_all_services = readSymbol("ptlrpc_all_services")
    services = readSUListFromHead(ptlrpc_all_services,
                "srv_list", "struct ptlrpc_service")
    for srv in services :
        if srv.srv_name == name :
            return srv
        elif name == "list" :
            print(srv.srv_name)

    return None

def show_waiting(service, pattern) :
    for i in range(service.srv_ncpts) :
        svcpt = service.srv_parts[i]
        print(svcpt, "incoming:", svcpt.scp_nreqs_incoming,
              "active:", svcpt.scp_nreqs_active,
              "hp active:", svcpt.scp_nhreqs_active)
        show_policy(svcpt.scp_nrs_reg.nrs_policy_primary, pattern)
        show_policy(svcpt.scp_nrs_reg.nrs_policy_fallback, pattern)

def get_history_reqs(service):
    rq_info = getStructInfo('struct ptlrpc_request')
    srv_rq_info = getStructInfo('struct ptlrpc_srv_req')
    nrs_rq_info = getStructInfo('struct ptlrpc_nrs_request')
    offset = rq_info['rq_srv'].offset + srv_rq_info['sr_hist_list'].offset

    for i in range(service.srv_ncpts) :
        svcpt = service.srv_parts[i]
        for req in readStructNext(svcpt.scp_hist_reqs.next, "next",
                                  maxel=500000) :
            if req == svcpt.scp_hist_reqs :
                break
            yield readSU("struct ptlrpc_request", int(req) - offset)

@lru_cache(maxsize=None)
def get_history_list(service):
    return list(get_history_reqs(service))

def show_resends(req) :
    exp = req.rq_export
    rq_info = getStructInfo('struct ptlrpc_request')
    srv_rq_info = getStructInfo('struct ptlrpc_srv_req')
    offset = rq_info['rq_srv'].offset + srv_rq_info['sr_exp_list'].offset

    for r in readStructNext(exp.exp_reg_rpcs.next, "next", maxel=60000) :
        rr = readSU("struct ptlrpc_request", int(r) - offset)
        if rr != req and rr.rq_xid == req.rq_xid :
            show_ptlrpc_request(rr)

    for r in readStructNext(exp.exp_hp_rpcs.next, "next", maxel=60000) :
        rr = readSU("struct ptlrpc_request", int(r) - offset)
        if rr != req and rr.rq_xid == req.rq_xid :
            show_ptlrpc_request(rr)

if ( __name__ == '__main__'):
    import argparse

    parser =  argparse.ArgumentParser()
    parser.add_argument("-r","--request", dest="req", default = 0)
    parser.add_argument("-s","--set", dest="set", default = 0)
    parser.add_argument("-n","--num", dest="n", default = 0)
    parser.add_argument("-i","--import", dest="imp", default = 0)
    parser.add_argument("-e","--export", dest="exp", default = 0)
    parser.add_argument("-u","--running", dest="running",
                        action='store_true')
    parser.add_argument("-w","--waiting", dest="waiting",
                       default = "")
    parser.add_argument("-W","--cli-waiting", dest="cli_waiting",
                       action='store_true')
    parser.add_argument("-c","--client", dest="client", default = "")
    parser.add_argument("-p","--pid", dest="pid",
                       default = 0)
    parser.add_argument("-H","--history", dest="history",
                       default = 0)
    parser.add_argument("-V","--verbose", dest="verbose", action='store_true')
    parser.add_argument('object', nargs='?')
    args = parser.parse_args()

    if args.n != 0 :
        max_req = args.n

    pattern = None
    if args.client != "" :
        pattern = re.compile(args.client)

    if args.req != 0 :
        req = readSU("struct ptlrpc_request", int(args.req, 16))
        show_ptlrpc_request(req)
        if args.verbose :
            show_resends(req)
    elif args.set != 0 :
        s = readSU("struct ptlrpc_request_set", int(args.set, 16))
        show_ptlrpc_set(s)
    elif args.imp != 0 :
        imp = readSU("struct obd_import", int(args.imp, 16))
        show_import("", imp)
        imp_show_state_history("", imp)
        imp_show_requests(imp)
        imp_show_history(imp)
    elif args.exp != 0 :
        exp = readSU("struct obd_export", int(args.exp, 16))
        show_export("", exp)
    elif args.running != 0 :
        show_processing(pattern)
    elif args.waiting != "" :
        show_waiting(find_service(args.waiting), pattern)
    elif args.cli_waiting != 0 :
        show_cli_waiting()
    elif args.pid != 0 :
        show_pid(int(args.pid), None)
    elif args.history != 0 :
        svc = find_service(args.history)
        if svc :
            for req in get_history_reqs(svc) :
                show_ptlrpc_request(req)
        else :
            print("Wrong service name", args.history)
    elif args.object :
        if args.object[:3] == "req" :
            req = readSU("struct ptlrpc_request", int(args.object[4:], 16))
            print(args.object[5:], req)
            show_ptlrpc_request(req)
    else :
        show_ptlrpcds()
