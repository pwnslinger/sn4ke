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
import signal
import random
import argparse
import logging
import subprocess
from gtirb_functions import Function
from gtirb_capstone import RewritingContext
from gtirb_capstone.instructions import GtirbInstructionDecoder
from gtirb import IR
from tqdm import tqdm, trange
from colorama import Fore
from capstone import *
from capstone.x86 import *

def rewrite_functions(infile, logger=logging.Logger("null"), context=None, fname=None):
    #logger.info("Generating GTIRB IR...")
    #gtirb_protobuf(infile)
    logger.info("Loading IR... " + infile)
    ir = IR.load_protobuf(infile)

    logger.info("Preparing IR for rewriting...")
    ctx = RewritingContext(ir) if context is None else context

    ctx.cp.detail = True

    for m in ctx.ir.modules:
        functions = Function.build_functions(m)
        print("%d functions in binary" % (len(functions)))
        bar = tqdm(functions, desc="Loop over functions", bar_format="{l_bar}%s{bar}%s{r_bar}" % (Fore.YELLOW, Fore.RESET))
        for f in bar:
            bar.set_description_str(f'Current function: {f.get_name()}')
            if fname == None or fname == f.get_name():
                rewrite_function(m, f, ctx, logger=logger)
    
    total_mutations = len(mutation_list)
    logger.info("#%s unique mutantion patterns found..."%str(total_mutations))
    print("#%s unique mutantion patterns found..."%str(total_mutations))
    
    f = 0
    RANDOM_SAMPLING = 1000

    logger.info("Randomly selecting %s non-trivial compileable mutants..."%str(RANDOM_SAMPLING))

    selected_mutants = []

    pbar = tqdm(total=RANDOM_SAMPLING, desc="Build Progress..", bar_format="{l_bar}%s{bar}%s{r_bar}" % (Fore.GREEN, Fore.RESET))

    while len(selected_mutants) < RANDOM_SAMPLING:
        # prevent infinite loop if we ran our of non-trivial compile-able mutant samples
        if len(mutation_list) == 0:
            break
        m = random.choice(mutation_list)
        # if there is any weird case of name duplication, continue
        if str(m) in selected_mutants:
            mutation_list.remove(m)
            continue
        pbar.set_description_str(f'Current mutation: {str(m)}')
        if m.build(ctx, logger):
            selected_mutants.append(str(m))
            # prevent duplication of mutants in list
            mutation_list.remove(m)
        else:
            # we dont wanna iterate over the failed ones again
            f += 1
            mutation_list.remove(m)
        pbar.update(len(selected_mutants)//10)
    pbar.close()

    logger.info("------------[ Statistics ]------------")
    logger.info("%s%% of mutants couldn't pass either compilation or trivial test."%str(round((f/total_mutations)*100, 2)))
    print("%s%% of mutants couldn't pass either compilation or trivial test."%str(round((f/total_mutations)*100, 2)))

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
            }

insn_arithmetic = {X86_INS_ADD: 'add', X86_INS_SUB: 'sub', X86_INS_ROR: 'ror', 
                    X86_INS_SHL: 'shl', X86_INS_SHR: 'shr', X86_INS_ROL: 'rol', 
                    }

insn_logic = {X86_INS_XOR: 'xor', X86_INS_OR: 'or', X86_INS_AND: 'and'}

insn_arilogic = {X86_INS_NEG: 'neg', X86_INS_NOT: 'not', X86_INS_INC: 'inc', 
                X86_INS_MUL: 'mul', X86_INS_DIV: 'div', X86_INS_DEC: 'dec',
                }

insn_flag_manip = {X86_INS_SETAE: 'setae', X86_INS_SETA: 'seta', X86_INS_SETBE: 'setbe', X86_INS_SETB: 'setb', 
                    X86_INS_SETE: 'sete', X86_INS_SETGE: 'setge', X86_INS_SETG: 'setg', X86_INS_SETLE: 'setle', 
                    X86_INS_SETL: 'setl', X86_INS_SETNE: 'setne', X86_INS_SETNO: 'setno', X86_INS_SETNP: 'setnp', 
                    X86_INS_SETNS: 'setns', X86_INS_SETO: 'seto', X86_INS_SETP: 'setp', X86_INS_SETS: 'sets'
                    }

def ks_wrapper(asm):
    proc = subprocess.Popen(['kstool', 'x64', asm],stdout=subprocess.PIPE)
    stdout = proc.stdout.read().decode("utf-8")
    try:
        opcodes = re.findall(r'\[\s(.*)\s\]', stdout)[0].split(' ')
    except IndexError:
        return tuple((-1,-1)), 1
    return tuple(([int(x,16) for x in opcodes], len(opcodes))), 0

def mutate_asm(insn_id, insn):
    asm = ""
    if insn_id == X86_INS_NOP:
        n_bytes = insn.size
        asm = "nop;"*n_bytes
    if insn_id == X86_INS_JMP:
        imm_val = insn.op_str
        asm = "%s %s;"% ("jmp", imm_val)
    if insn_id in insn_branch.keys():
        imm_val = insn.op_str
        asm = "%s %s;"% (insn_branch[insn_id], imm_val)
    if insn_id in insn_arithmetic:
        operands = re.findall(r':\s\w+(\s.*)>', str(insn))[0]
        asm = insn_arithmetic[insn_id] + operands
    if insn_id in insn_logic:
        operands = re.findall(r':\s\w+(\s.*)>', str(insn))[0]
        asm = insn_logic[insn_id] + operands
    if insn_id in insn_arilogic:
        operand = re.findall(r':\s\w+\s(.*)>', str(insn))[0]
        asm = insn_arilogic[insn_id] + operand
    return asm

def gen_name(module_name, fname, category, offset, orig, repl, logger=logging.Logger("null")):
    mutation_name = "%s:%s:%s:%s:%s:%s"%(module_name, fname, category, offset, orig, repl)
    logger.info(mutation_name)
    return mutation_name

def trivial_test(filename:str, timeout=2) -> bool:
    
    args = ['-h', '--help', '', './test.txt']
    status = True
    
    for arg in args:
        cmd = [filename, arg]
        # success run output - preexec_fn is not thread safe, use set_new_session=True instead!
        #proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE, stdout=subprocess.PIPE, shell=True, preexec=os.setsid)
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE, stdout=subprocess.PIPE, shell=True, start_new_session=True)
        try:
            _, stderr = proc.communicate(input=b'\n\n', timeout=timeout)
            # check if process is still running!
            if proc.poll() is None:
                # kill group of orphan processes under shell session ID - get rid of orphan processes livin' around and 100% cpu!
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            #import ipdb; ipdb.set_trace()
        except subprocess.TimeoutExpired:
            return False
        if stderr:
            # in case of error
            if proc.returncode - 128 == signal.SIGSEGV:
                status = False
                proc.kill()
                break
        subprocess.call(['pkill', '-9', '-f', filename])
        proc.kill()
    return status

def save_ir(ctx, fname, logger=logging.Logger("null")):
    logger.info("Saving new IR...")
    basename = fname.split(':')[0]
    ir_dir = './results/%s/ir'%basename
    if not os.path.exists(ir_dir):
        os.makedirs(ir_dir)
    ir_out = os.path.join(ir_dir, fname + ".gtirb")
    ctx.ir.save_protobuf(ir_out)
    logger.info("Done.")

def compile_ir(fname, logger=logging.Logger("null")):
    '''
    relocation R_X86_64_8 against symbol `_init' can not be used when making a PIE object; recompile with -fPIC
    I tracked this error and it comes from gtirb-pprinter@src/gtirb_pprinter/ElfBinaryPrinter.cpp#L105
    // if DYN, pie. if EXEC, no-pie. if both, pie overrides no-pie. If none, do not specify either argument.
    module.aux_data['binaryType']
    AuxData(type_name='sequence<string>', data=['DYN'], )
    '''
    logger.info("Rebuild the mutation...")
    basename = fname.split(':')[0]
    bin_dir = './results/%s/bin'%basename

    if not os.path.exists(bin_dir):
        os.makedirs(bin_dir)

    ir_out = os.path.join('./results/%s/ir/%s'%(basename, fname + ".gtirb"))
    bin_out = os.path.join(bin_dir, fname)
    
    args_pp = [
        "gtirb-pprinter",
        ir_out,
        "--keep-all",
        "--skip-section",
        ".eh_frame",
        #"--compiler-args", 
        #"-lm",
        "-b",
        bin_out,
        "-c",
        "-nostartfiles",
    ]
    p = subprocess.Popen(args_pp, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    _, stderr = p.communicate()
    logger.info(stderr)

    # takes a lot of space and we probably wont need them..
    os.unlink(ir_out)

    if p.returncode:
        return False
    else:
        return True    

def log(bin_name, text):
    log_path = './results/%s/failed.txt'%bin_name
    with open(log_path, 'a+') as f:
        f.write(text)

class Instruction(object):
    def __init__(self, insn_str, encoding, insn_sz):
        self._insn_str = insn_str
        self._encoding = encoding
        self._insn_sz = insn_sz

    @property
    def insn_str(self):
        return self._insn_str

    @property
    def encoding(self):
        return self._encoding

    @property
    def insn_sz(self):
        return self._insn_sz

class Mutation(object):
    def __init__(self, mname, fname, block, insn, offset, category, instruction):
        self._mname = mname
        self._fname = fname
        self._block = block
        self._insn = insn
        self._offset = offset
        self._cat = category
        self._repl = instruction

    @property
    def mname(self):
        return self._mname
    
    @property
    def fname(self):
        return self._fname

    @property
    def block(self):
        return self._block

    @property
    def insn(self):
        return self._insn

    @property
    def offset(self):
        return self._offset
    
    @property
    def cat(self):
        return self._cat

    @property
    def repl(self):
        return self._repl

    def build(self, ctx, logger=logging.Logger("null")):
        return build_mutation(self._block, ctx, self._insn, self._offset, self._cat, self._fname, \
                    self._repl.encoding, self._repl.insn_sz, self._repl.insn_str, logger=logger)
    
    def __str__(self):
        return gen_name(self._mname, self._fname, self._cat, self._offset, self._insn.mnemonic, self._repl.insn_str)
    

def build_mutation(block, ctx, insn, offset, group_name, fname, encoding, count, repl, logger=logging.Logger("null")):
    
    # check instruction size for overlappings, if any
    ins_sz = insn.size

    # re-open the ir and populate fields to prevent overwriting the modifications
    ctx_ = copy.deepcopy(ctx)

    for b in ctx_.ir.code_blocks:
        if block.offset == b.offset:
            block_ = b

    if ins_sz < count:
        ctx_.modify_block(block_, encoding, offset, True, count-ins_sz, logger=logger)
    
    else:
        # apply mutation on byteinterval
        ctx_.modify_block(block_, encoding, offset, logger=logger)

    mutation_name = gen_name(ctx.ir.modules[0].name, fname, group_name, offset, insn.mnemonic, repl, logger=logger)

    
    # saving resulting ir
    save_ir(ctx_, mutation_name, logger=logger)

    # compile ir
    if not compile_ir(mutation_name, logger=logger):
        return False

    # trivial test
    bin_path = './results/%s/bin/%s'%(ctx.ir.modules[0].name, mutation_name)
    status = trivial_test(bin_path)

    if not status:
        logger.info('Trivial Test: Failed, filename = %s'%mutation_name)
        log(ctx.ir.modules[0].name, '%s\n'%mutation_name)
        os.unlink(bin_path)
        return False
    
    return True

mutation_list = []

def mutation(block, ctx, insn, offset, group_name, fname, group=None, logger=logging.Logger("null")):
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
            instruction = Instruction(group[i], encoding, count)
            m = Mutation(ctx.ir.modules[0].name, fname, block, insn, offset, group_name, instruction)
            mutation_list.append(m)
            #build_mutation(block, ctx, insn, offset, group_name, fname, encoding, count, group[i], logger=logger)
    else:
        # handle nop cases : skip instruction
        if group_name == "nopOp":
            asm = mutate_asm(X86_INS_NOP, insn)

            (encoding, count), err = ks_wrapper(asm)

            if err:
                return

            logger.info("\nReplacing %s with %s"% (str(insn), asm))
            instruction = Instruction('nop', encoding, count)
            m = Mutation(ctx.ir.modules[0].name, fname, block, insn, offset, group_name, instruction)
            mutation_list.append(m)
            #build_mutation(block, ctx, insn, offset, group_name, fname, encoding, count, "nop", logger=logger)
        # handle jump case only - taken branch
        elif group_name == "brOp":
            if insn.id == X86_INS_JMP:
                return
            asm = mutate_asm(X86_INS_JMP, insn)

            (encoding, count), err = ks_wrapper(asm)

            if err:
                return

            logger.info("\nReplacing %s with %s"% (str(insn), asm))
            instruction = Instruction('jmp', encoding, count)
            m = Mutation(ctx.ir.modules[0].name, fname, block, insn, offset, group_name, instruction)
            mutation_list.append(m)
            #build_mutation(block, ctx, insn, offset, group_name, fname, encoding, count, "jmp", logger=logger)

def gtirb_protobuf(filename):
    disasm_args = ['ddisasm',
                    filename,
                    '--ir',
                    "%s.gtirb"%filename,
                    '-j 4',
                    ]
    return subprocess.call(disasm_args)

def rewrite_function(module, func, ctx, logger=logging.Logger("null")):
    logger.info("\nRewriting function: %s" % func.get_name())

    blocks = func.get_all_blocks()
    fname = func.get_name()

    for b in blocks:
        bytes = b.byte_interval.contents[b.offset : b.offset + b.size]
        offset = 0

        #for i in ctx.cp.disasm(bytes, offset):
        for i in tuple(GtirbInstructionDecoder(module.isa).get_instructions(b)):
            # mutation on jump instructions 
            if i.group(CS_GRP_JUMP):
                #if i.id in insn_branch.keys():
                #branch_mutator(module, ctx, b, i, offset, logger)
                
                # try all branch mutatation cases
                #mutation(b, ctx, i, offset, "brOp", fname, insn_branch, logger=logger)

                # just try replacement with jmp
                mutation(b, ctx, i, offset, "brOp", fname, logger=logger)

                # skip instruction
                mutation(b, ctx, i, offset, "nopOp", fname, logger=logger)
                
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
                dst, src = i.operands
                if dst.type == X86_OP_REG and dst.reg in (X86_REG_EBP, X86_REG_ESP, X86_REG_RSP, X86_REG_RBP):
                    continue

                # swapping operators
                mutation(b, ctx, i, offset, "arithOp", fname, insn_arithmetic, logger=logger)

                # skip instruction
                mutation(b, ctx, i, offset, "nopOp", fname, logger=logger)

                # Constant: replaces every integer constant c with a value from the set {-1, 0, 1, -c, c-1, c+1}\{c}
                if src.type == X86_OP_IMM:
                    insn_str = re.findall(r':\s(.*\s.*,\s).*>', str(i))[0]
                    c = random.randint(1,16)
                    const_mutations = [-1, 0, 1, -c, c-1, c+1, c]
                    
                    for const in const_mutations:
                        asm = insn_str + str(const)

                        (encoding, count), err = ks_wrapper(asm)

                        if err:
                            continue

                        if encoding is None:
                            continue
                        
                        logger.info("\nReplacing %s with %s"% (str(i), asm))
                        instruction = Instruction('imm:%s'%const, encoding, count)
                        m = Mutation(module.name, fname, b, i, offset, 'constOp', instruction)
                        mutation_list.append(m)
                        #build_mutation(b, ctx, i, offset, "constOp", fname, encoding, count, 'imm:%s'%const, logger=logger)
                        
            if i.id in insn_logic.keys():
                # swapping operators
                mutation(b, ctx, i, offset, "logicOp", fname, insn_logic, logger=logger)

                # skip instruction
                mutation(b, ctx, i, offset, "nopOp", fname, logger=logger)

            if i.id in insn_arilogic.keys():
                # swapping operators
                mutation(b, ctx, i, offset, "arilogicOp", fname, insn_arilogic, logger=logger)

                # skip instruction
                mutation(b, ctx, i, offset, "nopOp", fname, logger=logger)

            offset += i.size

def main():
    ap = argparse.ArgumentParser(
        description="Binrary mutation using GTIRB"
    )
    ap.add_argument("infile")
    ap.add_argument("--fname", default=None)
    ap.add_argument(
        "-v", "--verbose", action="store_true", help="Verbose output"
    )
    ap.add_argument("-q", "--quiet", action="store_true", help="No output")

    args = ap.parse_args()

    logging.basicConfig(format="%(message)s",
                        level=logging.INFO,
                        filename='./%s.log'%os.path.basename(args.infile),
                        filemode='w')

    # leave it here plz :)
    with open('./test.txt', 'wb') as f:
        f.write(b"!!TEST!!")

    # define a Handler which writes INFO messages or higher to the sys.stderr
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    # set a format which is simpler for console use
    formatter = logging.Formatter('%(message)s')
    # tell the handler to use this format
    console.setFormatter(formatter)
    logger = logging.getLogger("sn4ke")
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        # add the handler to the root logger
        logger.addHandler(console)
    elif not args.quiet:
        logger.setLevel(logging.INFO)

    logger.info("Rewriting stuff...")

    rewrite_functions(args.infile, logger=logger, fname=args.fname)

    return 0


if __name__ == "__main__":
    main()
