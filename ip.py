#!/usr/bin/env python

from __future__ import print_function

from pykdump.API import *
import code
import ptlrpc as ptlrpc
import ldlm_lock as ldlm
import obd as obd
import mdt as mdt
import osd as osd
import lnet as lnet
import kiblnd as kiblnd
#import cl_lock as cl_lock
#import cl_io as cl_io

def exit():
    sys.exit()

print()
print('+++ Starting interactive shell ...')
print('+++ Use exit() to exit')
print()

code.interact(local=locals())
