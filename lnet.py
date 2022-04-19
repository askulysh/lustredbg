# lnet functions

from __future__ import print_function

from pykdump.API import *

def nid2str(nid) :
    if struct_exists("struct lnet_nid") :
        lnd = nid.nid_type
        nid = nid.nid_addr[0]
        nid = int.from_bytes(nid.to_bytes(4, byteorder="little"),
                             byteorder="big")
    else :
        lnd = (nid >> 48) & 0xff
    if lnd == 2 :
        return ("%d.%d.%d.%d" % ((nid >>24) & 0xff, (nid >> 16) & 0xff,
                                (nid >> 8) & 0xff, nid & 0xff))
    elif lnd == 5 :
        return ("%d.%d.%d.%d" % ((nid >>24) & 0xff, (nid >> 16) & 0xff,
                                (nid >> 8) & 0xff, nid & 0xff))
    elif lnd == 9 :
        return "lo"
    elif lnd == 13 :
        return ("%d@gni" % (nid & 0xffffffff))


LNET_COOKIE_TYPE_BITS = 2
LNET_COOKIE_MASK = (1 << LNET_COOKIE_TYPE_BITS) - 1

LNET_LH_HASH_BITS = 12
LNET_LH_HASH_SIZE = 1 << LNET_LH_HASH_BITS
LNET_LH_HASH_MASK = LNET_LH_HASH_SIZE - 1

the_lnet = readSymbol("the_lnet")
LNET_CPT_NUMBER = the_lnet.ln_cpt_number
LNET_CPT_BITS = the_lnet.ln_cpt_bits
LNET_CPT_MASK = (1 << LNET_CPT_BITS) - 1

def lnet_cpt_of_cookie(cookie) :
    cpt = (cookie >> LNET_COOKIE_TYPE_BITS) & LNET_CPT_MASK

    if cpt < LNET_CPT_NUMBER :
        return cpt
    else :
        return  cpt % LNET_CPT_NUMBER

def lnet_res_lh_lookup(rec, cookie) :

    if (cookie & LNET_COOKIE_MASK) != rec.rec_type :
        return 0

    hash = cookie >> (LNET_COOKIE_TYPE_BITS + LNET_CPT_BITS)
    handles = readSUListFromHead(rec.rec_lh_hash[hash & LNET_LH_HASH_MASK],
                "lh_hash_chain", "struct lnet_libhandle")
    for lh in handles :
        if lh.lh_cookie == cookie :
            return lh
    return 0

def lookup_md(cookie) :
    cpt = lnet_cpt_of_cookie(cookie)
    lh = lnet_res_lh_lookup(the_lnet.ln_md_containers[cpt], cookie)

    if lh == 0 :
        msg_container = the_lnet.ln_msg_containers[cpt]
        active_msgs = readSUListFromHead(msg_container.msc_active,
                "msg_activelist", "struct lnet_msg")

        for msg in active_msgs :
            if msg.msg_md.md_lh.lh_cookie == cookie:
                return msg
    else :
        off = getStructInfo('struct lnet_libmd')['md_lh'].offset
        md = readSU("struct lnet_libmd", lh - off)
        return md

    return 0

def lookup_msg(cookie) :
    cpt = lnet_cpt_of_cookie(cookie)
    msg_container = the_lnet.ln_msg_containers[cpt]
    active_msgs = readSUListFromHead(msg_container.msc_active,
                "msg_activelist", "struct lnet_msg")
    for msg in active_msgs :
        if msg.msg_md.md_lh.lh_cookie == cookie:
            return msg

    resending_msgs = readSUListFromHead(msg_container.msc_resending,
                "msg_list", "struct lnet_msg")
    for msg in active_msgs :
        if msg.msg_md.md_lh.lh_cookie == cookie:
            return msg

    return 0

def print_nid(nid) :
    print(nid2str(nid))

if ( __name__ == '__main__'):
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("-n","--nid", dest="nid", default = 0)
    parser.add_argument("-m","--md", dest="md", default = 0)
    parser.add_argument("-r", "--request", dest="req", default = 0)
    parser.add_argument("-b", "--bulk", dest="bulk", default = 0)
    args = parser.parse_args()
    if args.nid != 0 :
        print_nid(int(args.nid, 16))
    elif args.md != 0:
        print(lookup_md(int(args.md, 16)))
    elif args.req != 0 :
        req = readSU("struct ptlrpc_request", int(args.req, 16))
        print("request md:", lookup_md(req.rq_cli.cr_req_md_h.cookie))
        print("       msg:", lookup_msg(req.rq_cli.cr_req_md_h.cookie))
        print("reply md:", lookup_md(req.rq_cli.cr_reply_md_h.cookie))
    elif args.bulk != 0 :
        desc = readSU("struct ptlrpc_bulk_desc", int(args.bulk, 16))
        for i in range(0, desc.bd_md_max_brw) :
            print("cookie", desc.bd_mds[i].cookie)
            print(lookup_md(desc.bd_mds[i].cookie))

