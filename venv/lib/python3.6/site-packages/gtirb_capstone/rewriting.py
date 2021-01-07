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

from gtirb import ByteInterval, Offset
import gtirb
import keystone
import capstone
import logging
import copy
from gtirb_capstone.instructions import GtirbInstructionDecoder
from functools import lru_cache


class GtirbCapstoneError(Exception):
    pass


class RewritingContext(object):
    """Simple class to carry around our ir and associated capstone/keystone
    objects for use in rewriting that IR.
    """

    ks = None
    ir = None

    def __init__(self, ir, ks=None):
        self.ir = ir
        self.cp = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)

        if ks is None:
            # Setup keystone
            self.ks = keystone.Ks(keystone.KS_ARCH_X86, keystone.KS_MODE_64)
            self.ks.syntax = keystone.KS_OPT_SYNTAX_ATT
        else:
            self.ks = ks
       
        self.prepare_for_rewriting()

    def __copy__(self):
        new_instance = RewritingContext(self.ir)
        new_instance.__dict__.update(self.__dict__)
        return new_instance

    def __deepcopy__(self, memodict={}):
        new_instance = RewritingContext(self.ir)
        new_instance.__dict__.update(self.__dict__)
        new_instance.ir = copy.deepcopy(self.ir, memodict)
        return new_instance

    def prepare_for_rewriting(self):
        """Prepare an IR for rewriting using gtirb-capstone.

        Call this before you call any other method.
        """

        for m in self.ir.modules:
            # Remove CFI directives, since we will most likely be
            # invalidating most (or all) of them.
            # TODO: can we not do this?
            if "cfiDirectives" in m.aux_data:
                del m.aux_data["cfiDirectives"]

    def isolate_byte_interval(self, module, block):
        """Creates a new byte interval that consists of a single existing
        block.
        """

        # TODO: we should remove this function if no users depend on it;
        # it was used in previous versions of this library, but now isn't,
        # but is technically a public method, so...

        section = block.byte_interval.section
        bi = block.byte_interval
        new_bi = ByteInterval(
            contents=bi.contents[block.offset : block.offset + block.size],
            address=bi.address + block.offset,
        )
        new_bi.section = section

        # Move symbolic expressions over
        ses = filter(
            lambda item: item[0] >= block.offset
            and item[0] < block.offset + block.size,
            block.byte_interval.symbolic_expressions.items(),
        )
        for se in ses:
            new_bi.symbolic_expressions[se[0] - block.offset] = se[1]

        # Remove this block from the old byte_interval
        bi.blocks.remove(block)
        # Update the block
        block.byte_interval = new_bi
        block.offset = 0

    def modify_block(
        self, block, new_bytes, offset, overlapping=False, delta=0, logger=logging.Logger("null")
    ):
        """Insert bytes into a block."""

        offset += block.offset

        logger.debug("  Before:")
        self.show_block_asm(block, logger=logger)

        # n_bytes = len(new_bytes)
        bi = block.byte_interval

        if overlapping:
            bi.size += delta

        bi.contents = (
            bi.contents[:offset] + bytes(new_bytes) + bi.contents[offset:]
        )

        # adjust blocks that occur after the insertion point
        # TODO: what if blocks overlap over the insertion point?
        for b in bi.blocks:
            if b != block and b.offset >= offset:
                b.offset += delta

        # adjust sym exprs that occur after the insertion point
        bi.symbolic_expressions = {
            (k + delta if k >= offset else k): v
            for k, v in bi.symbolic_expressions.items()
        }

        # adjust aux data if present
        # TODO: what other aux data uses byte interval offsets?
        sym_expr_sizes = bi.module.aux_data.get("symbolicExpressionSizes")
        if sym_expr_sizes is not None:
            sym_expr_sizes.data = {
                (
                    Offset(bi, k.displacement + delta)
                    if k.element_id == bi and k.displacement >= offset
                    else k
                ): v
                for k, v in sym_expr_sizes.data.items()
            }

        # all done
        logger.debug("  After:")
        self.show_block_asm(block, logger=logger)

    def modify_block_insert(
        self, module, block, new_bytes, offset, logger=logging.Logger("null")
    ):
        """Insert bytes into a block."""

        offset += block.offset

        logger.debug("  Before:")
        self.show_block_asm(block, logger=logger)

        n_bytes = len(new_bytes)
        bi = block.byte_interval

        # adjust block itself
        block.size += n_bytes

        # adjust byte interval the block goes in
        bi.size += n_bytes
        bi.contents = (
            bi.contents[:offset] + bytes(new_bytes) + bi.contents[offset:]
        )

        # adjust blocks that occur after the insertion point
        # TODO: what if blocks overlap over the insertion point?
        for b in bi.blocks:
            if b != block and b.offset >= offset:
                b.offset += n_bytes

        # adjust sym exprs that occur after the insertion point
        bi.symbolic_expressions = {
            (k + n_bytes if k >= offset else k): v
            for k, v in bi.symbolic_expressions.items()
        }

        # adjust aux data if present
        # TODO: what other aux data uses byte interval offsets?
        sym_expr_sizes = bi.module.aux_data.get("symbolicExpressionSizes")
        if sym_expr_sizes is not None:
            sym_expr_sizes.data = {
                (
                    Offset(bi, k.displacement + n_bytes)
                    if k.element_id == bi and k.displacement >= offset
                    else k
                ): v
                for k, v in sym_expr_sizes.data.items()
            }

        # all done
        logger.debug("  After:")
        self.show_block_asm(block, logger=logger)

    @lru_cache()
    def get_instruction_decoder(
        self, arch: gtirb.Module.ISA
    ) -> GtirbInstructionDecoder:
        """
        Return an instruction decoder for a given an isa.
        """
        return GtirbInstructionDecoder(arch)

    def show_block_asm(
        self,
        block: gtirb.CodeBlock,
        arch: gtirb.Module.ISA = None,
        logger=logging.Logger("null"),
    ):
        """
        Disassemble and print the contents of a code block using
        the given architecture. If no architecture is given,
        it is taken from the block's module. If the block
        is not in a module, the function throws an error.
        """

        if arch is None:
            if (
                block.byte_interval is not None
                and block.byte_interval.section is not None
                and block.byte_interval.section.module is not None
            ):
                arch = block.byte_interval.section.module.isa
        if arch is None:
            raise GtirbCapstoneError("Undefined architecture")

        for i in self.get_instruction_decoder(arch).get_instructions(block):
            logger.debug("\t0x%x:\t%s\t%s" % (i.address, i.mnemonic, i.op_str))
