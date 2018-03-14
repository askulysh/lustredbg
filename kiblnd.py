# kiblnd functions

from __future__ import print_function

from pykdump.API import *
from lnet import *


max_req = 10

def show_peers() :
    kiblnd_data = readSymbol("kiblnd_data")
    for i in range(0, kiblnd_data.kib_peer_hash_size) :
        peers = readSUListFromHead(kiblnd_data.kib_peers[i],
                "ibp_list", "struct kib_peer")
        if peers :
            print("i = %d" % i)
            for peer in peers :
                print(peer)
                print_nid(peer.ibp_nid)

def find_tx(addr) :
    kiblnd_data = readSymbol("kiblnd_data")
    for i in range(0, kiblnd_data.kib_peer_hash_size) :
        peers = readSUListFromHead(kiblnd_data.kib_peers[i],
                "ibp_list", "struct kib_peer")
        if peers :
            for peer in peers :
                print_nid(peer.ibp_nid)
                txs = readSUListFromHead(peer.ibp_tx_queue,
                "tx_list", "struct kib_tx")
                for tx in txs :
                    md = tx.tx_lntmsg[0].msg_md
                    if md.md_iov.iov[0].iov_base == addr :
                        print(tx)
                        return

def find_tx_by_handle(handle) :
    kiblnd_data = readSymbol("kiblnd_data")
    for i in range(0, kiblnd_data.kib_peer_hash_size) :
        peers = readSUListFromHead(kiblnd_data.kib_peers[i],
                "ibp_list", "struct kib_peer")
        if peers :
            for peer in peers :
                print_nid(peer.ibp_nid)
                txs = readSUListFromHead(peer.ibp_tx_queue,
                "tx_list", "struct kib_tx")
                for tx in txs :
                    for j in range(2) :
                        md = tx.tx_lntmsg[j].msg_md
                        if md.md_lh.lh_cookie == handle :
                            print(tx)
                            return


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
        find_tx_by_handle(desc.bd_mds[0].cookie)
    else :
        show_peers()
