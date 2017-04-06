# lnet functions

from __future__ import print_function

from pykdump.API import *

def nid2str(nid) :
    return ("%d.%d.%d.%d" % ((nid >>24) & 0xff, (nid >> 16) & 0xff,
                            (nid >> 8) & 0xff, nid & 0xff))
def print_nid(nid) :
    print(nid2str(nid))

