# ldlm_lock functions

from __future__ import print_function

from pykdump.API import *
from LinuxDump.Time import *

__LDLM_flags_c = '''
#define LDLM_FL_LOCK_CHANGED            0x0000000000000001
#define LDLM_FL_BLOCK_GRANTED           0x0000000000000002
#define LDLM_FL_BLOCK_CONV              0x0000000000000004
#define LDLM_FL_BLOCK_WAIT              0x0000000000000008
#define LDLM_FL_AST_SENT                0x0000000000000020
#define LDLM_FL_REPLAY                  0x0000000000000100
#define LDLM_FL_INTENT_ONLY             0x0000000000000200
#define LDLM_FL_HAS_INTENT              0x0000000000001000
#define LDLM_FL_FLOCK_DEADLOCK          0x0000000000008000
#define LDLM_FL_DISCARD_DATA            0x0000000000010000
#define LDLM_FL_NO_TIMEOUT              0x0000000000020000
#define LDLM_FL_BLOCK_NOWAIT            0x0000000000040000
#define LDLM_FL_TEST_LOCK               0x0000000000080000
#define LDLM_FL_CANCEL_ON_BLOCK         0x0000000000800000
#define LDLM_FL_NO_EXPANSION		0x0000000020000000
#define LDLM_FL_DENY_ON_CONTENTION      0x0000000040000000
#define LDLM_FL_AST_DISCARD_DATA        0x0000000080000000
#define LDLM_FL_FAIL_LOC                0x0000000100000000
#define LDLM_FL_SKIPPED                 0x0000000200000000
#define LDLM_FL_CBPENDING               0x0000000400000000
#define LDLM_FL_WAIT_NOREPROC           0x0000000800000000
#define LDLM_FL_CANCEL                  0x0000001000000000
#define LDLM_FL_LOCAL_ONLY              0x0000002000000000
#define LDLM_FL_FAILED                  0x0000004000000000
#define LDLM_FL_CANCELING               0x0000008000000000
#define LDLM_FL_LOCAL                   0x0000010000000000
#define LDLM_FL_LVB_READY               0x0000020000000000
#define LDLM_FL_KMS_IGNORE              0x0000040000000000
#define LDLM_FL_CP_REQD                 0x0000080000000000
#define LDLM_FL_CLEANED                 0x0000100000000000
#define LDLM_FL_ATOMIC_CB               0x0000200000000000
#define LDLM_FL_BL_AST                  0x0000400000000000
#define LDLM_FL_BL_DONE                 0x0000800000000000
#define LDLM_FL_NO_LRU                  0x0001000000000000
#define LDLM_FL_FAIL_NOTIFIED           0x0002000000000000
#define LDLM_FL_DESTROYED               0x0004000000000000
#define LDLM_FL_SERVER_LOCK             0x0008000000000000
#define LDLM_FL_RES_LOCKED              0x0010000000000000
#define LDLM_FL_WAITED                  0x0020000000000000
#define LDLM_FL_NS_SRV                  0x0040000000000000
#define LDLM_FL_EXCL                    0x0080000000000000
#define LDLM_FL_RESENT                  0x0100000000000000
'''

LDLM_flags = CDefine(__LDLM_flags_c)

if (symbol_exists("xtime")):
    xtime = readSymbol("xtime")
    def get_seconds():
        return xtime.tv_sec
else :
    if (symbol_exists("wall_to_monotonic")):
        tk = readSymbol()
        def get_seconds():
            return tk.xtime.tv_sec
    else:
        tk = readSymbol("timekeeper")
        def get_seconds():
            return tk.xtime_sec

def print_ldlm_lock(ldlm_lock, prefix) :
    print("%s 0x%x/0x%x refc %u" % (prefix, ldlm_lock.l_handle.h_cookie,
                            ldlm_lock.l_remote_handle.cookie,
                            ldlm_lock.l_refc.counter))
    print(prefix, "flags:", dbits2str(ldlm_lock.l_flags, LDLM_flags))
    if ldlm_lock.l_req_mode == ldlm_lock.l_granted_mode :
        print(prefix, "granted")
    else :
        print("%s enqueued %us ago" % (prefix,
                get_seconds() - ldlm_lock.l_last_activity))
    print("%s %s" % (prefix, ldlm_lock.l_conn_export.exp_obd.obd_name))
    if ldlm_lock.l_callback_timeout != 0 :
        print("will timeout in ", j_delay(ldlm_lock.l_callback_timeout))

if ( __name__ == '__main__'):
    import argparse

    parser =  argparse.ArgumentParser()
    parser.add_argument("-l","--lock", dest="lock", default = 0)
    args = parser.parse_args()
    if args.lock != 0 :
        l = readSU("struct ldlm_lock", int(args.lock, 0))
        print_ldlm_lock(l, "")

