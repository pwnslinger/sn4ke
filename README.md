# SN4KE  
[![DOI](https://zenodo.org/badge/278747355.svg)](https://zenodo.org/badge/latestdoi/278747355)  
Binary mutation engine based on [ddisasm](https://github.com/GrammaTech/ddisasm) and [Rev.ng](https://github.com/revng/revng) with a massive set of source-level muatation operators. 

## REWRITING  
To get more insight on our rewriting engine and mutations please take a look at [REWRITE.md](./REWRITE.md).  

## Expetiment results  
You can get access to our expetiment results and mutation breakdown through [this](https://docs.google.com/spreadsheets/d/11-Dt99bzEwhrv9GtTNtObHdDoniOTLmQ3BMDW8RMwzc/edit?usp=sharing) link. Just in case the above URL was not valid anymore, you can find the results under [results.xlsx](./stats/results.xlsx).

## Citing SN4KE  
SN4KE has been accepted to the [Binary Analysis Research (BAR)](https://www.ndss-symposium.org/ndss2021/cfp-bar-workshop/) workshop co-located with NDSS'21. If you want to refer to our work, please use the following BibTeX for citation.  

```
@misc{ahmadi2021sn4ke,
    title={SN4KE: Practical Mutation Testing at Binary Level},
    author={Mohsen Ahmadi and Pantea Kiaei and Navid Emamdoost},
    year={2021},
    eprint={2102.05709},
    archivePrefix={arXiv},
    primaryClass={cs.SE}
}
```  

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
