from __future__ import print_function
from pykdump.API import *
import os

# Author: Andriy Skulysh <askulysh@gmail.com>
# Based on https://wiki.hpdd.intel.com/download/attachments/12127633/lustre_log.py
# Author: John L. Hammond <john.hammond@intel.com>
# Based on ideas from Brian Behlendorf lustre crash extension, see:
# https://github.com/brkorb/lustre-crash-tools/.
#

bits_per_long = 64

def page_to_phys(page) :
    lines = exec_crash_command("kmem 0x%x" % page)
    o = lines.splitlines()[1].split()

    return int('0x' + o[1], 0)

def page_to_virt(page) :
    lines = exec_crash_command("kmem 0x%x" % page)
    o = lines.splitlines()[1].split()
    lines = exec_crash_command('ptov 0x' + o[1])

    return int('0x' + lines.splitlines()[1].split()[0], 0)

def lustre_log_dump(log_file):

    try:
        cpu_possible_bits = readSymbol("cpu_possible_mask").bits
    except :
        cpu_possible_bits = readSymbol("__cpu_possible_mask").bits
    cpu_possible_list = []

    i = 0
    for b in cpu_possible_bits:
        for j in range(0, bits_per_long):
            if b & (1 << j) != 0:
                cpu_possible_list.append(i + j)
        i = i + bits_per_long

    print("bits", cpu_possible_bits)
    print("cpus", cpu_possible_list)
    cfs_trace_data = readSymbol('cfs_trace_data')

    def walk(m_nr_pages, m_page_list):
        if m_nr_pages == 0:
            return  
        for tage in readSUListFromHead(m_page_list, "linkage",
                                       "struct cfs_trace_page",
                                       m_nr_pages + 1) :
            addr = page_to_virt(tage.page)
            buf = readmem(addr, tage.used)
            log_file.write(buf)

    for p in cfs_trace_data: 
        if p == 0:
            continue
        v = readSU("union cfs_trace_data_union", p)
        for cpu in cpu_possible_list:
            tcd = v[cpu].tcd
            print(tcd)
            print("dumping %d pages from cpu %d" %
                    (tcd.tcd_cur_pages, cpu)) 
            walk(tcd.tcd_cur_pages, tcd.tcd_pages)
            print("dumping %d daemon pages from cpu %d" %
                    (tcd.tcd_cur_daemon_pages, cpu)) 
            walk(tcd.tcd_cur_daemon_pages, tcd.tcd_daemon_pages)
            print("dumping %d stock pages from cpu %d" %
                    (tcd.tcd_cur_stock_pages, cpu)) 
            walk(tcd.tcd_cur_stock_pages, tcd.tcd_stock_pages)

if ( __name__ == '__main__'):
    import argparse

    parser =  argparse.ArgumentParser()
    parser.add_argument("-f","--file", dest="file", default = 0)
    args = parser.parse_args()
    if args.file != 0 :
        print("dumping to", args.file)
        with open(args.file, "wb") as log_file:
            lustre_log_dump(log_file)

