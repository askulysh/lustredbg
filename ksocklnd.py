# kiblnd functions

from __future__ import print_function

from pykdump.API import *
from lnet import *

max_req = 10
ksocknal_data = readSymbol("ksocknal_data")

def get_peers():
    for i in range(0, ksocknal_data.ksnd_peer_hash_size) :
        for peer in readSUListFromHead(ksocknal_data.ksnd_peers[i],
                "ksnp_list", "struct ksock_peer_ni") :
            yield peer

def show_peers() :
    for peer in get_peers() :
        print(peer)
        print_nid(peer.ksnp_id.nid)

def find_tx(addr) :
    for peer in get_peers() :
        print_nid(peer.ibp_nid)
        txs = readSUListFromHead(peer.ibp_tx_queue,
                    "tx_list", "struct kib_tx")
        for tx in txs :
            md = tx.tx_lntmsg[0].msg_md
            if md.md_iov.iov[0].iov_base == addr :
                print(tx)
                return

def find_tx_in_list(handle, txs) :
    for tx in txs :
        print(tx)
        if tx.tx_lnetmsg[j] == 0 :
            continue
        md = tx.tx_lnetmsg[j].msg_md
        if md.md_lh.lh_cookie == handle :
            return tx
    return 0

def find_tx_in_conn_queue(handle, head) :
    txs = readSUListFromHead(head,
            "tx_list", "struct ksock_tx")
    tx = find_tx_in_list(handle, txs)
    if tx != 0 :
        print("found ", tx, " in ", head)
    return tx

def find_tx_in_conn(handle, conn) :
#    tx = find_tx_in_conn_queue(handle, conn.ksnc_tx_list)
#    if tx != 0 :
#        return tx
    tx = find_tx_in_conn_queue(handle, conn.ksnc_tx_queue)
    if tx != 0 :
        return tx
    return tx

def find_tx_in_conn_list(handle, conns) :
    for conn in conns :
        print(conn)
        tx = find_tx_in_conn(handle, conn)
        if tx != 0 :
            return tx
    return 0

def find_tx_by_handle(handle) :
    for peer in get_peers() :
        print_nid(peer.ksnp_id.nid)
        txs = readSUListFromHead(peer.ksnp_tx_queue,
                "tx_list", "struct ksock_tx")
        print(txs)
        tx = find_tx_in_list(handle, txs)
        if tx != 0 :
            print("found ", tx, " in ksnp_tx_queue")
            return tx
        conns = readSUListFromHead(peer.ksnp_conns,
              "ksnc_list", "struct ksock_conn")
        tx = find_tx_in_conn_list(handle, conns)
        if tx != 0 :
            return tx

    print("ksnd_zombie_conns :")
    conns = readSUListFromHead(ksocknal_data.ksnd_zombie_conns,
            "ksnc_list", "struct ksock_conn")
    tx = find_tx_in_conn_list(handle, conns)
    if tx != 0 :
        return tx
    print("ksnd_enomem_conns :")
    conns = readSUListFromHead(ksocknal_data.ksnd_enomem_conns,
            "ksnc_list", "struct ksock_conn")
    tx = find_tx_in_conn_list(handle, conns)

    return tx

if ( __name__ == '__main__'):
    import argparse

    parser =  argparse.ArgumentParser()
    parser.add_argument("-r","--request", dest="req", default = 0)
    parser.add_argument("-b", "--bulk", dest="bulk", default = 0)
    parser.add_argument("-n","--num", dest="n", default = 0)
    args = parser.parse_args()
    if args.n != 0 :
        max_req = n
    if args.req != 0 :
        req = readSU("struct ptlrpc_request", int(args.req, 16))
        find_tx(req.rq_reqbuf)
    elif args.bulk != 0 :
        desc = readSU("struct ptlrpc_bulk_desc", int(args.bulk, 16))
        for i in range(0, desc.bd_md_max_brw) :
            print("cookie", desc.bd_mds[i].cookie)
            tx = find_tx_by_handle(desc.bd_mds[i].cookie)
            print(tx)
    else :
        show_peers()
        find_tx_by_handle(0)

