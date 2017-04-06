# kiblnd functions

from __future__ import print_function

from pykdump.API import *
from lnet import *


max_req = 10

def show_peers() :
    kiblnd_data = readSymbol("kiblnd_data")
    for i in xrange(0, kiblnd_data.kib_peer_hash_size) :
        peers = readSUListFromHead(kiblnd_data.kib_peers[i],
                "ibp_list", "struct kib_peer")
        if peers :
            print("i = %d" % i)
            for peer in peers :
                print(peer)
                print_nid(peer.ibp_nid)

def find_tx(req) :
    kiblnd_data = readSymbol("kiblnd_data")
    for i in xrange(0, kiblnd_data.kib_peer_hash_size) :
        peers = readSUListFromHead(kiblnd_data.kib_peers[i],
                "ibp_list", "struct kib_peer")
        if peers :
            for peer in peers :
                print_nid(peer.ibp_nid)
                txs = readSUListFromHead(peer.ibp_tx_queue,
                "tx_list", "struct kib_tx")
                for tx in txs :
                    md = tx.tx_lntmsg[0].msg_md
                    if md.md_iov.iov[0].iov_base == req.rq_reqbuf :
                        print(tx)
                        return

if ( __name__ == '__main__'):
    import argparse

    parser =  argparse.ArgumentParser()
    parser.add_argument("-r","--request", dest="req", default = 0)
    parser.add_argument("-n","--num", dest="n", default = 0)
    args = parser.parse_args()
    if args.n != 0 :
        max_req = n
    if args.req != 0 :
        req = readSU("struct ptlrpc_request", int(args.req, 0))
        find_tx(req)
    else :
        show_peers()
