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
import os
import re
import copy
import logging
from gtirb_functions import Function
from gtirb_capstone import RewritingContext

import argparse
import logging
from gtirb import IR
import subprocess

from capstone import *
from capstone.x86 import *

def rewrite_functions(ir, logger=logging.Logger("null"), context=None, fname=None):
    logger.info("Preparing IR for rewriting...")
    ctx = RewritingContext(ir) if context is None else context
    ctx.cp.detail = True
    ctx_ = copy.copy(ctx)
    for m in ctx.ir.modules:
        functions = Function.build_functions(m)
        print("%d functions in binary" % (len(functions)))
        for f in functions:

            print("fname %s" %(f.get_name()))
            if fname == None or fname == f.get_name():
                ctx = copy.copy(ctx_)
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

insn_branch = {X86_INS_JAE: 'jae', X86_INS_JA: 'ja', X86_INS_JBE: 'jbe', X86_INS_JB: 'jb', X86_INS_JCXZ: 'jcxz', 
            X86_INS_JECXZ: 'jecxz', X86_INS_JE: 'je', X86_INS_JGE: 'jge', X86_INS_JG: 'jg', X86_INS_JLE: 'jle',  
            X86_INS_JL: 'jl', X86_INS_JMP: 'jmp', X86_INS_JNE: 'jne', X86_INS_JNO: 'jno', X86_INS_JNP: 'jnp', 
                X86_INS_JNS: 'jns', X86_INS_JO: 'jo', X86_INS_JP: 'jp', X86_INS_JRCXZ: 'jrcxz', X86_INS_JS: 'js',
                X86_INS_NOP: 'nop'}

insn_arithmetic = {X86_INS_ADD: 'add', X86_INS_SUB: 'sub', X86_INS_MUL: 'mul', X86_INS_DIV: 'div', 
                    X86_INS_INC: 'inc', X86_INS_DEC: 'dec', X86_INS_SHL: 'shl', X86_INS_SHR: 'shr',
                    X86_INS_ROL: 'rol', X86_INS_ROR: 'ror'}

insn_logic = {X86_INS_NEG: 'neg', X86_INS_NOT: 'not', X86_INS_XOR: 'xor', X86_INS_OR: 'or', X86_INS_AND: 'and'}

insn_flag_manip = {X86_INS_SETAE: 'setae', X86_INS_SETA: 'seta', X86_INS_SETBE: 'setbe', X86_INS_SETB: 'setb', 
                    X86_INS_SETE: 'sete', X86_INS_SETGE: 'setge', X86_INS_SETG: 'setg', X86_INS_SETLE: 'setle', 
                    X86_INS_SETL: 'setl', X86_INS_SETNE: 'setne', X86_INS_SETNO: 'setno', X86_INS_SETNP: 'setnp', 
                    X86_INS_SETNS: 'setns', X86_INS_SETO: 'seto', X86_INS_SETP: 'setp', X86_INS_SETS: 'sets'}

def ks_wrapper(asm):
    proc = subprocess.Popen(['kstool', 'x64', asm],stdout=subprocess.PIPE)
    stdout = proc.stdout.read().decode("utf-8")
    try:
        opcodes = re.findall(r'\[\s(.*)\s\]', stdout)[0].split(' ')
    except IndexError:
        return tuple((-1,-1)), 1
    return tuple(([int(x,16) for x in opcodes], len(opcodes))), 0

def mutate_asm(insn_id, insn):
    if insn_id in insn_branch.keys():
        imm_val = insn.op_str
        if insn_id == X86_INS_NOP:
            import ipdb; ipdb.set_trace()
            n_bytes = insn.size
            asm = "nop;"*n_bytes
        else:
            asm = "%s %s;"% (insn_branch[insn_id], imm_val)
    if insn_id in insn_arithmetic:
        operands = re.findall(r':\s\w+(\s.*)>', str(insn))[0]
        asm = insn_arithmetic[insn_id] + operands
    return asm

def gen_name(module_name, category, offset, orig, repl, logger=logging.Logger("null")):
    mutation_name = "%s:%s:%s:%s:%s"%(module_name, category, offset, orig, repl)
    logger.info(mutation_name)
    return mutation_name

def save_ir(ctx, fname, logger=logging.Logger("null")):
    logger.info("Saving new IR...")
    ir_out = fname + ".gtirb"
    ctx.ir.save_protobuf(ir_out)
    logger.info("Done.")

def compile_ir(fname, logger=logging.Logger("null")):
    logger.info("Rebuild the mutation...")
    ir_out = fname + ".gtirb"
    args_pp = [
        "gtirb-pprinter",
        ir_out,
        "--keep-all",
        "--skip-section",
        ".eh_frame",
        #"--compiler-args", 
        #"-fPIC",
        "-b",
        fname,
        "-c",
        "-nostartfiles",
    ]
    ec = subprocess.call(args_pp)
    if ec:
        '''
        relocation R_X86_64_8 against symbol `_init' can not be used when making a PIE object; recompile with -fPIC
        I tracked this error and it comes from gtirb-pprinter@src/gtirb_pprinter/ElfBinaryPrinter.cpp#L105
        // if DYN, pie. if EXEC, no-pie. if both, pie overrides no-pie. If none, do not specify either argument.
        module.aux_data['binaryType']
        AuxData(type_name='sequence<string>', data=['DYN'], )
        '''

        os.remove(ir_out)
        #import ipdb; ipdb.set_trace()

def mutation(module, block, ctx, insn, offset, group_name, group=None, logger=logging.Logger("null")):
    if group is not None:
        for i in group.keys():
            if insn.id == i:
                continue

            # mutate asm based on the group it belongs to
            asm = mutate_asm(i, insn)

            # convert to byte using keystone
            # encoding, count = ctx.ks.asm(asm)
            (encoding, count), err = ks_wrapper(asm)

            if err:
                continue

            if encoding is None:
                logger.debug("\nCouldn't handle %s"%group[i])
                continue

            logger.info("\nReplacing %s with %s"% (str(insn), asm))

            # check instruction size for overlappings, if any
            ins_sz = insn.size
            if ins_sz < count:
                ctx.modify_block(module, block, encoding, offset, True, count-ins_sz, logger=logger)
            
            else:
                # apply mutation on byteinterval
                ctx.modify_block(module, block, encoding, offset, logger=logger)

            mutation_name = gen_name(module.name, group_name, offset, insn.mnemonic, group[i], logger=logger)

            # saving resulting ir
            save_ir(ctx, mutation_name, logger=logger)

            # compile ir
            compile_ir(mutation_name, logger=logger)


def mutation_rewrite(module, ctx, block, asm, insn, offset, repl, logger=logging.Logger("null")):
    # convert to byte using keystone
    # use ks_wrapper cuz sometimes ks gets crazy!
    #encoding, _ = ctx.ks.asm(asm)
    encoding, _ = ks_wrapper(asm)
    #import ipdb; ipdb.set_trace()

    # apply mutation on byteinterval
    ctx.modify_block(module, block, encoding, offset, logger=logger)

    mutation_name = gen_name(module.name, "brOp", offset, insn.mnemonic, repl, logger=logger)

    # saving resulting ir
    save_ir(ctx, mutation_name, logger=logger)

    # compile ir
    compile_ir(mutation_name, logger=logger)
    

def branch_mutator(module, ctx, block, insn, offset, logger=logging.Logger("null")):

    # once go through fall-through
    if insn.id != X86_INS_JMP:
        imm_val = insn.op_str
        asm = "%s %s;"% ("jmp", imm_val)
        mutation_rewrite(module, ctx, block, asm, insn, offset, "jmp", logger)

    # nop instruction
    n_bytes = insn.size
    asm = "nop;"*n_bytes
    mutation_rewrite(module, ctx, block, asm, insn, offset, "nop", logger)

def rewrite_function(module, func, ctx, logger=logging.Logger("null")):
    logger.info("\nRewriting function: %s" % func.get_name())
    #module_ = module.copy()
    ctx_ = copy.copy(ctx)

    blocks = func.get_all_blocks()
    #blocks_ = blocks.copy()

    for b in blocks:
        bytes = b.byte_interval.contents[b.offset : b.offset + b.size]
        offset = 0

        #bi = b.byte_interval
        for i in ctx_.cp.disasm(bytes, offset):
            ctx = copy.copy(ctx_)
            #module = module_.copy()
            # mutation on jump instructions 
            if i.group(CS_GRP_JUMP):
                #if i.id in insn_branch.keys():
                #branch_mutator(module, ctx, b, i, offset, logger)
                mutation(module, b, ctx, i, offset, "brOp", insn_branch, logger=logger)
                
                '''
                # just copy the bytes of the jump
                encoding = i.bytes.copy()
                # get a ref to the symbolic location this jump is pointing to
                symexpr = bi.symbolic_expressions[b.offset+i.address+1]
                # insert the copy before the existing jump
                ctx.modify_block_insert(module, b, encoding, offset, logger=logger)
                # make sure the copy points to the same symbolic location
                bi.symbolic_expressions[b.offset+i.address+1] = symexpr
                # increment twice so we don't keep duplicating this jump
                '''
            if i.id in insn_arithmetic.keys():
                # skip esp, ebp e.g. sub rsp, 0x10
                dst, _ = i.operands
                if dst.type == X86_OP_REG and dst.reg in (X86_REG_EBP, X86_REG_ESP, X86_REG_RSP, X86_REG_RBP):
                    continue
                mutation(module, b, ctx, i, offset, "arithOp", insn_arithmetic, logger=logger)
                #import pdb; pdb.set_trace()

            offset += i.size

def main():
    ap = argparse.ArgumentParser(
        description="Binrary mutation using GTIRB"
    )
    ap.add_argument("infile")
    ap.add_argument(
        "-v", "--verbose", action="store_true", help="Verbose output"
    )
    ap.add_argument("-q", "--quiet", action="store_true", help="No output")

    args = ap.parse_args()

    ks_wrapper('add byte ptr [rax - 0x75], cl')

    logging.basicConfig(format="%(message)s")
    logger = logging.getLogger("sn4ke")
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    elif not args.quiet:
        logger.setLevel(logging.INFO)

    logger.info("Loading IR... " + args.infile)
    ir = IR.load_protobuf(args.infile)

    logger.info("Rewriting stuff...")
    rewrite_functions(ir, logger=logger, fname="main")

    return 0


if __name__ == "__main__":
    main()
