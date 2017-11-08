# ldiskfs functions

from __future__ import print_function

from pykdump.API import *

LDISKFS_MIN_DESC_SIZE_64BIT = 64

def ldiskfs_get_group_desc(sbi, block_group) :
    if block_group >= sbi.s_groups_count :
        print("wrong block_group", block_group)
        return

    group_desc = block_group >> sbi.s_desc_per_block_bits;
    offset = block_group & (sbi.s_desc_per_block - 1);

    print(sbi.s_group_desc[group_desc])
    return readSU("struct ldiskfs_group_desc",
           sbi.s_group_desc[group_desc].b_data + offset * sb.s_desc_size)

def ldiskfs_inode_table(sbi, bg) :
    ret = bg.bg_inode_table_lo
    if sbi.s_desc_size >= LDISKFS_MIN_DESC_SIZE_64BIT :
        ret = ret | (bg.bg_inode_table_hi << 32)
    return ret

def get_ldiskfs_inode(inode) :
    ino = inode.i_ino
    sb = inode.i_sb
    sbi = readSU("struct ldiskfs_sb_info", sb.s_fs_info)
    block_group = int((ino - 1) / sbi.s_inodes_per_group)
    gdp = ldiskfs_get_group_desc(sbi, block_group)

    # Figure out the offset within the block group inode table
    inodes_per_block = sb.s_blocksize / sbi.s_inode_size;
    inode_offset = (ino - 1) % sbi.s_inodes_per_group;
    block = ldiskfs_inode_table(sbi, gdp) + (inode_offset / inodes_per_block);
    offset = (inode_offset % inodes_per_block) * sb.s_inode_size;
    print(block, offset)

if ( __name__ == '__main__'):
    import argparse

    parser =  argparse.ArgumentParser()
    parser.add_argument("-i","--inode", dest="inode", default = 0)
    args = parser.parse_args()
    if args.inode != 0 :
        inode = readSU("struct inode", int(args.inode, 16))
        get_ldiskfs_inode(inode)

