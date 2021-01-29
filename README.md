# sn4ke
binary mutator

## Gtirb-capstone 
I modified the baseline Gtirb-capstone module to support capstone in the
context. This is a patch for the master branch and will be merged later on. 

Please get this branch using the following: 

`git clone --depth=1 --branch=wip/dev https://github.com/pwnslinger/gtirb-capstone/` 

and install it effectively: 

`python setup.py install` 

For detailed instructions on how to run and interact with gtirb-based mutation engine, please take a look at [Rewriter](./REWRITE.md) doc.  

## Test 

The following pass simply duplicates the any jump group of instructions using
Grammatech framework: 

First you need to generate the gtirb from binary: 

`ddisasm thing --ir thing.gtirb` 

Then fed the generated IR to our binary rewriter: 

`python myrewriter.py --rebuild patched -o patched.gtirb thing.gtirb` 

Before patch: 

```asm
#-----------------------------------
.align 2
.globl main
.type main, @function
#-----------------------------------
main:

.cfi_startproc
.cfi_lsda 255
.cfi_personality 255
.cfi_def_cfa 7, 8
.cfi_offset 16, -8
            push RBP
.cfi_def_cfa_offset 16
.cfi_offset 6, -16
            mov RBP,RSP
.cfi_def_cfa_register 6
            sub RSP,16
            mov RAX,QWORD PTR FS:[40]
            mov QWORD PTR [RBP-8],RAX
            xor EAX,EAX
            lea RAX,QWORD PTR [RBP-12]
            mov RSI,RAX
            lea RDI,QWORD PTR [RIP+.L\_824]
            mov EAX,0
            call __isoc99_scanf@PLT

            mov EAX,DWORD PTR [RBP-12]
            cmp EAX,4919
            jne .L_766
``` 

After patch: 

```asm
#-----------------------------------
.align 2
.globl main
.type main, @function
#-----------------------------------
main:

            push RBP
            mov RBP,RSP
            sub RSP,16
            mov RAX,QWORD PTR FS:[40]
            mov QWORD PTR [RBP-8],RAX
            xor EAX,EAX
            lea RAX,QWORD PTR [RBP-12]
            mov RSI,RAX
            lea RDI,QWORD PTR [RIP+.L\_824]
            mov EAX,0
            call __isoc99_scanf@PLT

            mov EAX,DWORD PTR [RBP-12]
            cmp EAX,4919
            jne .L_766
            jne .L_766
``` 
