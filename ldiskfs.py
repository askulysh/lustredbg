# ldiskfs functions

from __future__ import print_function

from pykdump.API import *
from LinuxDump import percpu

LDISKFS_MIN_DESC_SIZE_64BIT = 64

def ldiskfs_get_group_desc(sbi, block_group) :
    if block_group >= sbi.s_groups_count :
        print("wrong block_group", block_group)
        return

    group_desc = block_group >> sbi.s_desc_per_block_bits;
    offset = block_group & (sbi.s_desc_per_block - 1);

    g = sbi.s_group_desc[group_desc]
    b_data_crash = exec_crash_command("buffer_head.b_data %x" % g)
    b_data = int(b_data_crash.split()[2], 16)
    return readSU("struct ldiskfs_group_desc",
             b_data + offset * sbi.s_desc_size)

def ldiskfs_inode_table(sbi, bg) :
    ret = bg.bg_inode_table_lo
    if sbi.s_desc_size >= LDISKFS_MIN_DESC_SIZE_64BIT :
        ret = ret | (bg.bg_inode_table_hi << 32)
    return ret

def lookup_bh_lru(bdev, block, size) :
    bh_lrus = percpu.get_cpu_var("bh_lrus")
    for var in bh_lrus :
        bh_lru = readSU("struct bh_lru", var)
        for bh in bh_lru.bhs :
            print(bh)
            if bh.b_bdev == bdev and bh.b_blocknr == block and bh.b_size == size:
                return bh
    return 0

def sb_getblk(sb, block) :
    return lookup_bh_lru(sb.s_bdev, block, sb.s_blocksize)

def get_ldiskfs_inode(inode) :
    ino = inode.i_ino
    sb = inode.i_sb
    sbi = readSU("struct ldiskfs_sb_info", sb.s_fs_info)
    block_group = int((ino - 1) / sbi.s_inodes_per_group)
    gdp = ldiskfs_get_group_desc(sbi, block_group)

    # Figure out the offset within the block group inode table
    inodes_per_block = int(sb.s_blocksize / sbi.s_inode_size)
    inode_offset = (ino - 1) % sbi.s_inodes_per_group
    block = ldiskfs_inode_table(sbi, gdp) + int(inode_offset / inodes_per_block)
    offset = (inode_offset % inodes_per_block) * sbi.s_inode_size
    print(block, offset)
    bh = sb_getblk(sb, block)
    print(bh)

if ( __name__ == '__main__'):
    import argparse

    parser =  argparse.ArgumentParser()
    parser.add_argument("-i", "--inode", dest="inode", default = 0)
    args = parser.parse_args()
    if args.inode != 0 :
        inode = readSU("struct inode", int(args.inode, 16))
        get_ldiskfs_inode(inode)

