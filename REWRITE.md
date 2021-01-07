# Gtirb-rewriter

# Install
1. Clone the github repository including the sub-modules using the following command:  
`git clone --recurse-submodules --depth 1 https://github.com/pwnslinger/sn4ke.git`
2.  Activate the virtual env:  
`. ./venv/bin/activate`  
3. Please install the added submodules using pip:  
    ```
    cd gtirb-capstone
    pip install .
    ```

# Run
All originals binaries are located under [`./tests`](./tests) directory. For mutation you just need to pass the binary like the following: 

`time ipython --pdb myrewriter.py tests/bzip2_base.amd64-m64-gcc42-nn`


# Adjustments
In some cases for compilation, you might need to pass specific arguments to the GCC e.g. libraries or -fPIC, etc. To make sure our mutated binaries are executable, I'd suggest testing them against ddisasm and gtirb without any mutation passes like the following approach:

1. Generate the `.gtirb` IR from binary:  
`ddisasm gobmk_base.amd64-m64-gcc42-nn --ir gobmk_base.amd64-m64-gcc42-nn.gtirb`  
2. Reassemble the binary from resulting gtirb IR:  
`gtirb-pprinter gobmk_base.amd64-m64-gcc42-nn.gtirb --keep-all --skip-section .eh_frame -b test -c -nostartfiles`  

We should expect receiving the following error: 

```
Generating binary file
Printing modulegobmk_base.amd64-m64-gcc42-nn to temporary file /tmp/fileMWpM2q.s
Calling compiler
Compiler arguments: -o test /tmp/fileMWpM2q.s -nostartfiles -pie 
/usr/bin/ld: warning: Cannot create .eh_frame_hdr section, --eh-frame-hdr ignored.
/usr/bin/ld: error in /tmp/ccbIF6Ix.o(.eh_frame); no .eh_frame_hdr table will be created.
/tmp/ccbIF6Ix.o: In function `set_depth_values':
(.text+0x4f0e3): undefined reference to `pow'
/tmp/ccbIF6Ix.o: In function `review_move_reasons':
(.text+0x56c99): undefined reference to `pow'
(.text+0x57154): undefined reference to `pow'
/tmp/ccbIF6Ix.o:(.plt+0xe8): undefined reference to `pow'
collect2: error: ld returned 1 exit status
```

Based on the linker error, we need to pass math library (`-lm`) the the GCC using `--compiler-args`:  

```
$> gtirb-pprinter gobmk_base.amd64-m64-gcc42-nn.gtirb --keep-all --skip-section .eh_frame --compiler-args -lm -b test -c -nostartfiles 
[INFO]  Reading GTIRB file:     "gobmk_base.amd64-m64-gcc42-nn.gtirb"
Generating binary file
Printing modulegobmk_base.amd64-m64-gcc42-nn to temporary file /tmp/fileQtPVZl.s
Calling compiler
Compiler arguments: -o test /tmp/fileQtPVZl.s -lm -nostartfiles -pie 
/usr/bin/ld: warning: Cannot create .eh_frame_hdr section, --eh-frame-hdr ignored.
/usr/bin/ld: error in /tmp/cc4CSqVs.o(.eh_frame); no .eh_frame_hdr table will be created.
```  

You should put these adjustments under [./myrewriter.py#compile_ir](./myrewriter.py#L184-L194) function. 

