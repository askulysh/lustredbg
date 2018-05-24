# lnet functions

from __future__ import print_function

from pykdump.API import *

def nid2str(nid) :
    lnd = nid >> 48
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

def print_nid(nid) :
    print(nid2str(nid))

