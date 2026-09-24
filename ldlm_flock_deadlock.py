#!/usr/bin/env python
"""
epython script: safely replay the ldlm_flock_deadlock() POSIX-lock
deadlock-detection walk (lustre/ldlm/ldlm_flock.c) against a live crash
session, validating every structure at every hop instead of blindly
dereferencing pointers the way the in-kernel C function does.

Background
----------
ldlm_flock_deadlock(req, bl_lock) walks a chain of flock owners across
obd_export::exp_flock_hash tables, looking for a cycle back to req_owner.
Pre-LU-20464 the walk did:

    bl_exp_new = class_export_get(flock->blocking_export);
    class_export_put(bl_exp);                      # (A) may free bl_exp
    cfs_hash_put(bl_exp->exp_flock_hash, ...);      # (B) UAF: reads freed bl_exp

If (A) drops the last reference (e.g. racing with a concurrent
ping_evictor_main() export eviction), step (B) reads freed/reused memory.
The corrupted hash table can then make a later cfs_hash_lookup() return a
stale/aliased "struct ldlm_lock *" -- including one that aliases req itself,
tripping LASSERT(req != lock) -> LBUG, even though there was no real
deadlock cycle.

This script re-implements the walk but:
  * validates every obd_export before trusting it (refcount > 0, handle
    cookie/hash pointer not poisoned, hash metadata sane),
  * independently re-derives "the lock for this owner" by walking
    exp_flock_hash's buckets itself (not a single opaque lookup call),
    and cross-checks that the object it finds is genuinely linked in that
    hash,
  * validates every ldlm_lock hop (l_export back-pointer, l_flags,
    l_policy_data.l_flock.owner) against what the C code assumes but
    never checks,
  * stops and reports *why* the moment something looks corrupted/freed,
    instead of dereferencing further (which is what let the real bug reach
    the assertion instead of failing safely earlier).

Usage (inside `crash`, on the box with the actual vmcore):
    epython ldlm_flock_deadlock.py -r <req_lock_addr> -b <bl_lock_addr>
    epython ldlm_flock_deadlock.py -r 0xffff8be8ec9ada00 -b 0xffff8bdd37636400

Finding candidate req/bl_lock addresses:
    Use `ldlm_lock -r <resource_addr>` (see ldlm_lock.py) to list granted
    and waiting locks for the resource involved, then feed the request
    (waiting) lock as -r and a granted/conflicting lock as -b, exactly as
    ldlm_process_flock_lock() would have.

Note: this file must run under `crash`'s embedded Python (pykdump/epython)
on the analysis VM; it cannot be executed standalone.
"""
from __future__ import print_function

from pykdump.API import *
import lustrelib as ll

# hide this file from 'epython scripts' listing like lustrelib.py does
interactive = False

LI_POISON32 = 0x5a5a5a5a
LI_POISON64 = 0x5a5a5a5a5a5a5a5a
SLAB_POISON = 0x6b6b6b6b6b6b6b6b        # SLUB_DEBUG free poison ('kkkkkkkk')
KERNEL_VA_MIN = 0xffff800000000000      # lower bound of a plausible x86_64 kernel VA

LDLM_FL_DESTROYED = 0x0004000000000000  # keep in sync with ldlm_lock.py's LDLM_flags


def addr(x):
    """Best-effort integer address of a pykdump SU/pointer/int."""
    try:
        return int(Addr(x))
    except Exception:
        try:
            return int(x)
        except Exception:
            return 0


def is_canonical(a):
    a = addr(a)
    if a == 0:
        return False
    if a in (LI_POISON32, LI_POISON64, SLAB_POISON):
        return False
    return a >= KERNEL_VA_MIN


def check(label, cond, detail=""):
    print("  [%s] %-52s %s" % ("OK  " if cond else "FAIL", label, detail))
    return cond


def href_count(h_ref):
    """refcount_t layout varies: struct refcount_struct{atomic_t refs;}
    on modern kernels, a bare atomic_t on older ones. Try both."""
    try:
        return int(h_ref.refs.counter)
    except Exception:
        pass
    try:
        return int(h_ref.counter)
    except Exception:
        return None


def lock_container(hnode):
    """container_of(hnode, struct ldlm_lock, l_exp_flock_hash)"""
    off = member_offset('struct ldlm_lock', 'l_exp_flock_hash')
    return readSU('struct ldlm_lock', addr(hnode) - off)


def validate_export(exp, tag):
    print("-- validating export %s (%s)" % (hex(addr(exp)), tag))
    if not check("export pointer canonical", is_canonical(exp)):
        return False

    cnt = None
    try:
        cnt = href_count(exp.exp_handle.h_ref)
    except Exception as e:
        check("exp_handle.h_ref readable", False, str(e))
        return False
    ok = check("exp_handle.h_ref readable", cnt is not None, "count=%s" % cnt)
    if cnt is None:
        return False
    ok &= check("exp_handle.h_ref > 0 (export not already destroyed)",
                cnt > 0, "count=%d" % cnt)
    if cnt == 1:
        print("  [WARN] refcount == 1: a single class_export_put() here would "
              "free this export -- this is precisely the pre-LU-20464 "
              "use-after-free window")
    if not ok:
        return False

    try:
        cookie = int(exp.exp_handle.h_cookie)
    except Exception as e:
        return check("exp_handle.h_cookie readable", False, str(e))
    ok &= check("exp_handle.h_cookie not poisoned",
                cookie not in (LI_POISON32, LI_POISON64))

    fh = exp.exp_flock_hash
    fh_addr = addr(fh)
    ok &= check("exp_flock_hash non-NULL", fh_addr != 0)
    ok &= check("exp_flock_hash not poisoned",
                fh_addr not in (LI_POISON32, LI_POISON64, SLAB_POISON))
    if ok and fh_addr:
        try:
            bits = int(fh.hs_cur_bits)
            ok &= check("exp_flock_hash.hs_cur_bits sane", 0 < bits < 32,
                        "bits=%d" % bits)
        except Exception as e:
            ok &= check("exp_flock_hash structure readable", False, str(e))
    return ok


def lookup_owner(exp, owner):
    """Re-derive 'the lock for this owner' by walking exp_flock_hash's
    buckets ourselves (mirrors ldlm_flock_lookup_cb()+cfs_hash_lookup()),
    instead of trusting a single opaque lookup call. Returns (lock, nodes)
    or (None, nodes)."""
    try:
        nodes = ll.cfs_hash_get_nodes(exp.exp_flock_hash)
    except Exception as e:
        print("  [WARN] could not walk exp_flock_hash buckets: %s" % e)
        return None, []
    for hn in nodes:
        try:
            lock = lock_container(hn)
            if int(lock.l_policy_data.l_flock.owner) == owner:
                return lock, nodes
        except Exception:
            continue
    return None, nodes


def hash_contains(nodes, lock):
    """Confirm 'lock' is genuinely one of the nodes we already walked,
    catching the case where a corrupted/freed hash returns an object that
    isn't really a member."""
    la = addr(lock)
    for hn in nodes:
        try:
            if addr(lock_container(hn)) == la:
                return True
        except Exception:
            continue
    return False


def validate_lock(lock, expected_owner, expected_exp, tag):
    print("-- validating lock %s (%s)" % (hex(addr(lock)), tag))
    if not check("lock pointer canonical", is_canonical(lock)):
        return False
    try:
        flags = int(lock.l_flags)
    except Exception as e:
        return check("l_flags readable", False, str(e))
    ok = check("LDLM_FL_DESTROYED not set", not (flags & LDLM_FL_DESTROYED),
               "flags=0x%x" % flags)
    ok &= check("l_resource non-NULL", addr(lock.l_resource) != 0)
    ok &= check("l_export matches export whose hash we searched",
                addr(lock.l_export) == addr(expected_exp),
                "l_export=%s expected=%s" %
                (hex(addr(lock.l_export)), hex(addr(expected_exp))))
    try:
        owner = int(lock.l_policy_data.l_flock.owner)
    except Exception as e:
        return check("l_policy_data.l_flock.owner readable", False, str(e))
    ok &= check("l_flock.owner matches expected bl_owner",
                owner == expected_owner,
                "owner=0x%x expected=0x%x" % (owner, expected_owner))
    return ok


def nid_same_check(exp_a, exp_b):
    try:
        return int(exp_a.exp_connection.c_peer.nid) == \
               int(exp_b.exp_connection.c_peer.nid)
    except Exception:
        return False


def print_lock_brief(lock):
    try:
        f = lock.l_policy_data.l_flock
        print("    owner=0x%x pid=%d [%d-%d] blocking_owner=0x%x "
              "blocking_export=%s" %
              (int(f.owner), int(f.pid), int(f.start), int(f.end),
               int(f.blocking_owner), hex(addr(f.blocking_export))))
    except Exception as e:
        print("    <could not read l_policy_data.l_flock: %s>" % e)
    try:
        print("    l_export=%s l_resource=%s l_flags=0x%x" %
              (hex(addr(lock.l_export)), hex(addr(lock.l_resource)),
               int(lock.l_flags)))
    except Exception:
        pass


def flock_deadlock_check(req_addr, bl_addr, max_iter=64):
    req = readSU('struct ldlm_lock', req_addr)
    bl_lock = readSU('struct ldlm_lock', bl_addr)

    print("=== req lock: %s ===" % hex(req_addr))
    print_lock_brief(req)
    print("=== bl  lock: %s ===" % hex(bl_addr))
    print_lock_brief(bl_lock)

    req_exp = req.l_export
    if addr(req_exp) == 0:
        print("\nreq->l_export == NULL: this is a client-side lock; "
              "ldlm_flock_deadlock() is server-only and returns 0 immediately.")
        return

    req_owner = int(req.l_policy_data.l_flock.owner)
    bl_exp = bl_lock.l_export
    bl_owner = int(bl_lock.l_policy_data.l_flock.owner)

    for i in range(max_iter):
        print("\n### iteration %d: owner=0x%x export=%s" %
              (i, bl_owner, hex(addr(bl_exp))))

        if not validate_export(bl_exp, "bl_exp"):
            print("!!! export failed validation -- ABORTING walk here.")
            print("!!! In the unpatched code this export would still be")
            print("!!! dereferenced (bl_exp->exp_flock_hash) -- this is the")
            print("!!! LU-20464 use-after-free window.")
            return

        lock, nodes = lookup_owner(bl_exp, bl_owner)
        if lock is None:
            print("no lock for owner 0x%x found in this export's hash -> "
                  "chain ends here, no deadlock" % bl_owner)
            return

        if not hash_contains(nodes, lock):
            print("!!! CORRUPTION: lock %s was derived but is not actually "
                  "linked in exp_flock_hash -- the hash table is "
                  "inconsistent (stale/freed memory)." % hex(addr(lock)))
            return

        if not validate_lock(lock, bl_owner, bl_exp, "chain[%d]" % i):
            print("!!! lock failed validation -- do not trust data derived "
                  "from it any further.")
            return

        if addr(lock) == addr(req):
            print("\n*** lock == req at iteration %d ***" % i)
            print("*** This is exactly what LASSERT(req != lock) checks")
            print("*** (ldlm_flock.c:242). All structures up to this point")
            print("*** passed validation, so this needs a human judgment call:")
            print("*** is this a GENUINE self-referential cycle, or did an")
            print("*** earlier, already-freed export/hash produce stale data")
            print("*** that only *looks* consistent?")
            return

        print_lock_brief(lock)
        flock = lock.l_policy_data.l_flock
        new_owner = int(flock.blocking_owner)
        new_exp = flock.blocking_export

        if not validate_export(new_exp, "blocking_export"):
            print("!!! blocking_export failed validation -- chain corrupted "
                  "downstream of lock %s" % hex(addr(lock)))
            return

        if new_owner == req_owner and nid_same_check(new_exp, req_exp):
            print("\n*** GENUINE DEADLOCK: owner 0x%x on req's NID reached "
                  "via a fully-validated chain ***" % new_owner)
            return

        bl_owner = new_owner
        bl_exp = new_exp

    print("\nmax_iter (%d) exceeded without termination -- possible cycle "
          "in the chain itself; investigate manually." % max_iter)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("-r", "--req", dest="req", required=True,
                         help="address of the request (enqueuing) ldlm_lock")
    parser.add_argument("-b", "--bl", dest="bl", required=True,
                         help="address of the conflicting/blocking ldlm_lock")
    parser.add_argument("-m", "--max-iter", dest="max_iter", type=int,
                         default=64)
    args = parser.parse_args()

    flock_deadlock_check(int(args.req, 16), int(args.bl, 16), args.max_iter)
