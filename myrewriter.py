#
# Copyright (C) 2020 GrammaTech, Inc.
#
# This code is licensed under the MIT license. See the LICENSE file in
# the project root for license terms.
#
# This project is sponsored by the Office of Naval Research, One Liberty
# Center, 875 N. Randolph Street, Arlington, VA 22203 under contract #
# N68335-17-C-0700.  The content of the information does not necessarily
# reflect the position or policy of the Government and no official
# endorsement should be inferred.
#
import random
import logging
from gtirb_functions import Function
from gtirb_capstone import RewritingContext

import argparse
import logging
from gtirb import IR
import subprocess
import IPython

from capstone import *
# from capstone.x86 import *

def rewrite_functions(ir, logger=logging.Logger("null"), context=None, fname=None):
    logger.info("Preparing IR for rewriting...")
    ctx = RewritingContext(ir) if context is None else context
    ctx.cp.detail = True

    for m in ctx.ir.modules:
        functions = Function.build_functions(m)
        print("%d functions in binary" % (len(functions)))
        for f in functions:
            print("fname %s" %(f.get_name()))
            if fname == None or fname == f.get_name():
                rewrite_function(m, f, ctx, logger=logger)


def myshow_byteinterval_asm(ctx, byte_interval, logger=logging.Logger("null")):
    """Disassemble and print the contents of a code block."""

    addr = (
        byte_interval.address
        if byte_interval.address is not None
        else 0
    )

    for i in ctx.cp.disasm(
        byte_interval.contents,
        addr,
    ):
        if i.address+1 in byte_interval.symbolic_expressions:
            symexpr = "yes"
        else:
            symexpr = ""
        logger.debug("\t0x%x:\t%s\t%s\t%s" % (i.address, i.mnemonic, i.op_str, symexpr))

def myshow_block_asm(ctx, block, logger=logging.Logger("null")):
    """Disassemble and print the contents of a code block."""

    addr = (
        block.byte_interval.address
        if block.byte_interval.address is not None
        else 0
    )

    for i in ctx.cp.disasm(
        block.byte_interval.contents[
            block.offset : block.offset + block.size
        ],
        addr + block.offset,
    ):
        if i.address+1 in block.byte_interval.symbolic_expressions:
            symexpr = "yes"
        else:
            symexpr = ""
        logger.debug("\t0x%x:\t%s\t%s\t%s" % (i.address, i.mnemonic, i.op_str, symexpr))


def rewrite_function(module, func, ctx, logger=logging.Logger("null")):
    logger.debug("\nRewriting function: %s" % func.get_name())

    blocks = func.get_all_blocks()

    for b in blocks:
        bytes = b.byte_interval.contents[b.offset : b.offset + b.size]
        offset = 0
        bi = b.byte_interval
        for i in ctx.cp.disasm(bytes, offset):
            if i.group(CS_GRP_JUMP):
                # just copy the bytes of the jump
                encoding = i.bytes.copy()
                # get a ref to the symbolic location this jump is pointing to
                symexpr = bi.symbolic_expressions[b.offset+i.address+1]
                # insert the copy before the existing jump
                ctx.modify_block_insert(module, b, encoding, offset, logger=logger)
                # make sure the copy points to the same symbolic location
                bi.symbolic_expressions[b.offset+i.address+1] = symexpr
                # increment twice so we don't keep duplicating this jump
            offset += i.size

def main():
    ap = argparse.ArgumentParser(
        description="Show (un)reachable code in GTIRB"
    )
    ap.add_argument("infile")
    ap.add_argument(
        "-o", "--outfile", default=None, help="GTIRB output filename"
    )
    ap.add_argument(
        "--rebuild",
        metavar="FILENAME",
        default=None,
        help="Rebuild binary as FILENAME",
    )
    ap.add_argument(
        "-v", "--verbose", action="store_true", help="Verbose output"
    )
    ap.add_argument("-q", "--quiet", action="store_true", help="No output")
    args = ap.parse_args()

    logging.basicConfig(format="%(message)s")
    logger = logging.getLogger("myrwriter")
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    elif not args.quiet:
        logger.setLevel(logging.INFO)

    if args.rebuild is not None and args.outfile is None:
        logger.error("Error: with --rebuild, --outfile is required")
        exit(1)

    logger.info("Loading IR... " + args.infile)
    ir = IR.load_protobuf(args.infile)

    logger.info("Rewriting stuff...")
    rewrite_functions(ir, logger=logger, fname="main")

    if args.outfile is not None:
        logger.info("Saving new IR...")
        ir.save_protobuf(args.outfile)

    logger.info("Done.")

    if args.rebuild is not None:
        logger.info("Pretty printing...")
        args_pp = [
            "gtirb-pprinter",
            args.outfile,
            "--keep-all",
            "--skip-section",
            ".eh_frame",
            "-b",
            args.rebuild,
            "-c",
            "-nostartfiles",
        ]
        ec = subprocess.call(args_pp)
        return ec
    return 0


if __name__ == "__main__":
    main()
