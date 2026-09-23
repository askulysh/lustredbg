# ldiskfs functions

from __future__ import print_function

from pykdump.API import *
from LinuxDump import percpu

LDISKFS_MIN_DESC_SIZE_64BIT = 64

# on-disk xattr layout, see lustre/ldiskfs/xattr.h
LDISKFS_GOOD_OLD_INODE_SIZE = 128
LDISKFS_XATTR_MAGIC = 0xEA020000
LDISKFS_XATTR_PAD = 4
LDISKFS_XATTR_ROUND = LDISKFS_XATTR_PAD - 1

ldiskfs_xattr_index_c = '''
#define LDISKFS_XATTR_INDEX_USER               1
#define LDISKFS_XATTR_INDEX_POSIX_ACL_ACCESS    2
#define LDISKFS_XATTR_INDEX_POSIX_ACL_DEFAULT   3
#define LDISKFS_XATTR_INDEX_TRUSTED             4
#define LDISKFS_XATTR_INDEX_LUSTRE              5
#define LDISKFS_XATTR_INDEX_SECURITY            6
#define LDISKFS_XATTR_INDEX_SYSTEM              7
#define LDISKFS_XATTR_INDEX_RICHACL             8
#define LDISKFS_XATTR_INDEX_ENCRYPTION          9
'''
ldiskfs_xattr_index = CDefine(ldiskfs_xattr_index_c)

ldiskfs_xattr_prefix = {
    ldiskfs_xattr_index.LDISKFS_XATTR_INDEX_USER: "user.",
    ldiskfs_xattr_index.LDISKFS_XATTR_INDEX_POSIX_ACL_ACCESS:
        "system.posix_acl_access",
    ldiskfs_xattr_index.LDISKFS_XATTR_INDEX_POSIX_ACL_DEFAULT:
        "system.posix_acl_default",
    ldiskfs_xattr_index.LDISKFS_XATTR_INDEX_TRUSTED: "trusted.",
    ldiskfs_xattr_index.LDISKFS_XATTR_INDEX_LUSTRE: "lustre.",
    ldiskfs_xattr_index.LDISKFS_XATTR_INDEX_SECURITY: "security.",
    ldiskfs_xattr_index.LDISKFS_XATTR_INDEX_SYSTEM: "system.",
    ldiskfs_xattr_index.LDISKFS_XATTR_INDEX_RICHACL: "system.richacl",
    ldiskfs_xattr_index.LDISKFS_XATTR_INDEX_ENCRYPTION: "encryption.",
}

def bh_get_b_data_addr(bh) :
    b_data_crash = exec_crash_command("buffer_head.b_data %x" % bh)
    return int(b_data_crash.split()[2], 16)

def ldiskfs_get_group_desc(sbi, block_group) :
    if block_group >= sbi.s_groups_count :
        print("wrong block_group", block_group)
        return

    group_desc = block_group >> sbi.s_desc_per_block_bits;
    offset = block_group & (sbi.s_desc_per_block - 1);

    g = sbi.s_group_desc[group_desc]
    b_data = bh_get_b_data_addr(g)
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
            if bh and bh.b_bdev == bdev and bh.b_blocknr == block and bh.b_size == size:
                return bh
    return 0

# x86_64 targets only -> 4K pages
PAGE_SHIFT = 12

def xarray_entry(xarray, index) :
    node = xarray.xa_head
    if not (long(node) & 2) :
        if index :
            return 0
        return node
    node = readSU("struct xa_node", node & ~3)
    if (index >> node.shift) > 63 :
        return 0
    while node :
        offset = (index >> node.shift) & 63
        node = node.slots[offset]
        if not node or not (long(node) & 2) :
            return node
        node = readSU("struct xa_node", node & ~3)

def bdev_mapping(bdev) :
    try :
        return bdev.bd_mapping             # kernel >= 5.10-ish
    except :
        return bdev.bd_inode.i_mapping      # older kernels (e.g. RHEL8)

def find_page_buffer(bdev, blocksize, block) :
    """ Look up the buffer_head for 'block' via the block device's page
        cache (address_space xarray) instead of just the tiny per-cpu
        bh_lru: a block can be long resident in the buffer cache without
        ever having gone through *this* cpu's bh_lru. """
    try :
        mapping = bdev_mapping(bdev)
        blocks_per_page = (1 << PAGE_SHIFT) // blocksize
        index = block // blocks_per_page
        page_ptr = xarray_entry(mapping.i_pages, index)
        if not page_ptr or (long(page_ptr) & 1) :
            return 0                        # not present / shadow entry
        page = readSU("struct page", long(page_ptr) & ~3)
        if not page.private :
            return 0
        first = readSU("struct buffer_head", page.private)
        bh = first
        while True :
            if bh.b_blocknr == block and bh.b_size == blocksize :
                return bh
            bh = readSU("struct buffer_head", bh.b_this_page)
            if Addr(bh) == Addr(first) :
                return 0
    except :
        return 0

IAM_LVAR_ROOT_MAGIC = 0xb01dface
IAM_LVAR_LEAF_MAGIC = 0x1973
IAM_LFIX_ROOT_MAGIC = 0xbedabb1ed

def bh_for_each_lru() :
    bh_lrus = percpu.get_cpu_var("bh_lrus")
    for var in bh_lrus :
        bh_lru = readSU("struct bh_lru", var)
        for bh in bh_lru.bhs :
            if bh == 0 :
                continue
            try :
                addr = bh_get_b_data_addr(bh)
                header = readSU("struct lvar_leaf_header", addr)
                if header.vlh_magic == IAM_LVAR_LEAF_MAGIC :
                    print(header)
                else :
                    header = readSU("struct lvar_root", addr)
                    if header.vlh_magic == IAM_LVAR_ROOT_MAGIC :
                        print(header)
                    else :
                        header = readSU("struct iam_lfix_root", addr)
                        if header.vlh_magic == IAM_LFIX_ROOT_MAGIC :
                            print(header)
                        else :
                            header = readSU("struct iam_lfix_root", addr)
                            if header.vlh_magic == IAM_LFIX_ROOT_MAGIC :
                                print(header)
            except :
                header = 0


def sb_getblk(sb, block) :
    bh = lookup_bh_lru(sb.s_bdev, block, sb.s_blocksize)
    if bh :
        return bh
    return find_page_buffer(sb.s_bdev, sb.s_blocksize, block)

def ldiskfs_xattr_name(name_index, name) :
    prefix = ldiskfs_xattr_prefix.get(name_index)
    if prefix is None :
        return "unknown(%d).%s" % (name_index, name.decode(errors="replace"))
    if prefix.endswith(".") :
        return prefix + name.decode(errors="replace")
    return prefix

def walk_ldiskfs_xattr_entries(first_addr, value_base) :
    """ Walk a chain of 'struct ldiskfs_xattr_entry' (ibody or block form)
        starting at first_addr, yielding (name_index, name, value_addr,
        value_len, value_inum) for each entry.  value_base is the address
        entry.e_value_offs is relative to: IFIRST(header) for ibody EAs,
        bh->b_data (block start) for external xattr block EAs. """
    entry_size = struct_size("struct ldiskfs_xattr_entry")
    addr = first_addr
    while readU32(addr) != 0 :
        entry = readSU("struct ldiskfs_xattr_entry", addr)
        name = readmem(addr + entry_size, entry.e_name_len)
        yield (entry.e_name_index, name, value_base + entry.e_value_offs,
               entry.e_value_size, entry.e_value_inum)
        reclen = ((entry.e_name_len + LDISKFS_XATTR_ROUND + entry_size) &
                  ~LDISKFS_XATTR_ROUND)
        addr = addr + reclen

def get_ldiskfs_inode_info(inode) :
    off = member_offset("struct ldiskfs_inode_info", "vfs_inode")
    return readSU("struct ldiskfs_inode_info", Addr(inode) - off)

def ibody_xattr_entries(raw_inode, extra_isize) :
    """ In-inode ('ibody') EAs stored past the fixed 128-byte on-disk
        inode, see IHDR()/IFIRST() in lustre/ldiskfs/xattr.h. """
    if extra_isize == 0 :
        return
    hdr_addr = Addr(raw_inode) + LDISKFS_GOOD_OLD_INODE_SIZE + extra_isize
    if readU32(hdr_addr) != LDISKFS_XATTR_MAGIC :
        return
    first = hdr_addr + struct_size("struct ldiskfs_xattr_ibody_header")
    for e in walk_ldiskfs_xattr_entries(first, first) :
        yield e

def block_xattr_entries(sb, i_file_acl) :
    """ External xattr block EAs pointed to by i_file_acl, see BHDR()/
        BFIRST() in lustre/ldiskfs/xattr.h.  Only works if the block is
        still resident in the per-cpu buffer-head LRU cache. """
    if i_file_acl == 0 :
        return
    bh = sb_getblk(sb, i_file_acl)
    if not bh :
        print("xattr block", i_file_acl, "not resident in buffer cache")
        return
    b_data = bh_get_b_data_addr(bh)
    if readU32(b_data) != LDISKFS_XATTR_MAGIC :
        print("xattr block", i_file_acl, "bad magic")
        return
    first = b_data + struct_size("struct ldiskfs_xattr_header")
    for e in walk_ldiskfs_xattr_entries(first, b_data) :
        yield e

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
    bh = sb_getblk(sb, block)
    if bh :
        return readSU("struct ldiskfs_inode", bh_get_b_data_addr(bh) + offset)
    else :
        print("can't find inode in bhlru")
        return 0

if ( __name__ == '__main__'):
    import argparse

    parser =  argparse.ArgumentParser()
    parser.add_argument("-i", "--inode", dest="inode", default = 0)
    args = parser.parse_args()
    if args.inode != 0 :
        inode = readSU("struct inode", int(args.inode, 16))
        print(get_ldiskfs_inode(inode))
    else :
        bh_for_each_lru()

