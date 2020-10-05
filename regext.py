from crash import register_epython_prog as rprog

from pykdump.API import *

import os
import sys

help = '''
Show device related information
'''

rprog("ptlrpc", "ptlrpc requst information",
      "-h   - list available options",
      help)

help = '''
Show device related information
'''

rprog("ldlm_lock", "Device information",
      "-h   - list available options",
      help)


rprog("obd", "Device information",
      "-h   - list available options",
      help)

rprog("mdt", "MDT device information",
      "-h   - list available options",
      help)

rprog("osd", "OSD device information",
      "-h   - list available options",
      help)

rprog("cl_lock", "cl_lock information",
      "-h   - list available options",
      help)

rprog("cl_io", "cl_io information",
      "-h   - list available options",
      help)

rprog("ip", "Interactive python",
      "",
      help)

rprog("analyze", "Automated vmcore analysis",
      "",
      help)
rprog("debug_flags", "Show debug flags",
      "",
      help)
