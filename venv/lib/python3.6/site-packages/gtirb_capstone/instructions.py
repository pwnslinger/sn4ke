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

import gtirb
import capstone
import capstone.x86
import capstone.arm64
import capstone.arm
import capstone.mips
import capstone.ppc
from enum import Enum
from typing import Iterator, List, Union
from dataclasses import dataclass


class AccessType(Enum):
    UNKNOWN = "unknown"
    READ = "read"
    WRITE = "write"
    READ_WRITE = "read_write"


# Union of all possible operands
CapstoneOp = Union[
    capstone.x86.X86Op,
    capstone.arm.ArmOp,
    capstone.arm64.Arm64Op,
    capstone.mips.MipsOp,
    capstone.ppc.PpcOp,
]
# Union of all possible memory operands
CapstoneMemoryAccess = Union[
    capstone.x86.X86OpMem,
    capstone.arm.ArmOpMem,
    capstone.arm64.Arm64OpMem,
    capstone.mips.MipsOpMem,
    capstone.ppc.PpcOpMem,
]


@dataclass
class MemoryAccess:
    addr: int
    type: AccessType
    # the memory operand
    op_mem: CapstoneMemoryAccess


class GtirbInstructionDecoder:
    """
    Class to obtain instruction information of gtirb basic blocks.
    """

    GTIRB_ISA_TO_CAPSTONE = {
        gtirb.Module.ISA.ARM: capstone.CS_ARCH_ARM,
        gtirb.Module.ISA.ARM64: capstone.CS_ARCH_ARM64,
        gtirb.Module.ISA.MIPS32: capstone.CS_ARCH_MIPS,
        gtirb.Module.ISA.MIPS64: capstone.CS_ARCH_MIPS,
        gtirb.Module.ISA.PPC32: capstone.CS_ARCH_PPC,
        gtirb.Module.ISA.PPC64: capstone.CS_ARCH_PPC,
        gtirb.Module.ISA.IA32: capstone.CS_ARCH_X86,
        gtirb.Module.ISA.X64: capstone.CS_ARCH_X86,
    }

    GTIRB_ISA_TO_CAPSTONE_MODE = {
        gtirb.Module.ISA.ARM: capstone.CS_MODE_ARM,
        gtirb.Module.ISA.ARM64: capstone.CS_MODE_ARM,
        gtirb.Module.ISA.MIPS32: capstone.CS_MODE_MIPS32,
        gtirb.Module.ISA.MIPS64: capstone.CS_MODE_MIPS64,
        gtirb.Module.ISA.PPC32: capstone.CS_MODE_32,
        gtirb.Module.ISA.PPC64: capstone.CS_MODE_64,
        gtirb.Module.ISA.IA32: capstone.CS_MODE_32,
        gtirb.Module.ISA.X64: capstone.CS_MODE_64,
    }

    def __init__(self, arch: gtirb.Module.ISA):

        self._arch = arch
        self._cs = capstone.Cs(
            self.GTIRB_ISA_TO_CAPSTONE[self._arch],
            self.GTIRB_ISA_TO_CAPSTONE_MODE[self._arch],
        )
        self._cs.detail = True

    def get_instructions(
        self, block: gtirb.CodeBlock
    ) -> Iterator[capstone.CsInsn]:
        """
        Get capstone instructions of a basic block.
        Note: This function gets raw instructions, without
        taking into account symbolic expressions.
        """
        if self._arch == gtirb.Module.ISA.ARM:
            if block.decode_mode == 1:
                self._cs.mode = capstone.CS_MODE_THUMB
            else:
                self._cs.mode = capstone.CS_MODE_ARM
        addr = (
            block.byte_interval.address
            if block.byte_interval.address is not None
            else 0
        )
        return self._cs.disasm(
            block.byte_interval.contents[
                block.offset : block.offset + block.size
            ],
            addr + block.offset,
        )

    def get_access_type(self, op: CapstoneOp) -> AccessType:
        """
        Get the capstone operand's access type.
        """
        if op.access == capstone.CS_AC_READ:
            return AccessType.READ
        elif op.access == capstone.CS_AC_WRITE:
            return AccessType.WRITE
        elif op.access == capstone.CS_AC_READ | capstone.CS_AC_WRITE:
            return AccessType.READ_WRITE
        return AccessType.UNKNOWN

    GTIRB_ISA_TO_CAPSTONE_MEM_OP = {
        gtirb.Module.ISA.ARM: capstone.arm.ARM_OP_MEM,
        gtirb.Module.ISA.ARM64: capstone.arm64.ARM64_OP_MEM,
        gtirb.Module.ISA.MIPS32: capstone.mips.MIPS_OP_MEM,
        gtirb.Module.ISA.MIPS64: capstone.mips.MIPS_OP_MEM,
        gtirb.Module.ISA.PPC32: capstone.ppc.PPC_OP_MEM,
        gtirb.Module.ISA.PPC64: capstone.ppc.PPC_OP_MEM,
        gtirb.Module.ISA.IA32: capstone.x86.X86_OP_MEM,
        gtirb.Module.ISA.X64: capstone.x86.X86_OP_MEM,
    }

    def get_memory_accesses(
        self, block: gtirb.CodeBlock
    ) -> List[MemoryAccess]:
        """
        Get memory accesses of a basic block.
        Each memory access has an addr, an access type and the
        capstone memory operand.

        NOTE: The address of the memory access is the address
        of the displacement in x86/x64 but it is the address
        of the instruction in all other architectures.
        """

        mem_type = self.GTIRB_ISA_TO_CAPSTONE_MEM_OP[self._arch]

        memory_accesses = []
        for insn in self.get_instructions(block):
            # FIXME find out displacement offsets in other architectures
            disp_offset = (
                insn.disp_offset
                if self._arch in [gtirb.Module.ISA.IA32, gtirb.Module.ISA.X64]
                else 0
            )
            for op in insn.operands:
                if op.type == mem_type:
                    memory_accesses.append(
                        MemoryAccess(
                            addr=insn.address + disp_offset,
                            type=self.get_access_type(op),
                            op_mem=op.mem,
                        )
                    )
        return memory_accesses
