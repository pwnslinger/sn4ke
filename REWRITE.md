# Gtirb-rewriter

# Install
1. Clone the github repository including the sub-modules using the following command:  
`git clone --recurse-submodules --depth 1 https://github.com/pwnslinger/sn4ke.git`
2.  Activate the virtual env:  
`. ./venv/bin/activate`  
3. For `ddisasm` installtion please follow the instruction from their [README.md](https://github.com/GrammaTech/ddisasm):  
`sudo apt-get install ddisasm`
4. Please install the added submodules using pip:  
    ```
    cd gtirb-capstone
    pip install .
    ```
5. Install the following sub-modules:  
    * Capstone
    * Gtirb-capstone
    * Gtirb-functions
    * Gtirb-pprinter
    * Keystone

# Run
All originals binaries are located under [`./tests`](./tests) directory. For mutation you just need to pass the binary like the following: 

`time ipython --pdb myrewriter.py tests/bzip2_base.amd64-m64-gcc42-nn.gtirb`

You can find the mutation results under the `./results/bzip2_base.amd64-m64-gcc42-nn/bin/` directory. 

```
$> ls -lah results/bzip2_base.amd64-m64-gcc42-nn/bin | head -n 20
total 497M
drwxr-xr-x 2 pwnslinger pwnslinger 780K Jan  6 16:18 .
drwxr-xr-x 4 pwnslinger pwnslinger 4.0K Jan  6 12:34 ..
-rwxr-xr-x 1 pwnslinger pwnslinger  68K Jan  6 12:36 bzip2_base.amd64-m64-gcc42-nn:bsPutUInt32:arithOp:5:shr:add
-rwxr-xr-x 1 pwnslinger pwnslinger  68K Jan  6 12:36 bzip2_base.amd64-m64-gcc42-nn:bsPutUInt32:arithOp:5:shr:rol
-rwxr-xr-x 1 pwnslinger pwnslinger  68K Jan  6 12:36 bzip2_base.amd64-m64-gcc42-nn:bsPutUInt32:arithOp:5:shr:ror
-rwxr-xr-x 1 pwnslinger pwnslinger  68K Jan  6 12:36 bzip2_base.amd64-m64-gcc42-nn:bsPutUInt32:arithOp:5:shr:shl
-rwxr-xr-x 1 pwnslinger pwnslinger  68K Jan  6 12:36 bzip2_base.amd64-m64-gcc42-nn:bsPutUInt32:arithOp:5:shr:sub
-rwxr-xr-x 1 pwnslinger pwnslinger  68K Jan  6 12:36 bzip2_base.amd64-m64-gcc42-nn:bsPutUInt32:arithOp:7:shr:add
-rwxr-xr-x 1 pwnslinger pwnslinger  68K Jan  6 12:36 bzip2_base.amd64-m64-gcc42-nn:bsPutUInt32:arithOp:7:shr:rol
-rwxr-xr-x 1 pwnslinger pwnslinger  68K Jan  6 12:36 bzip2_base.amd64-m64-gcc42-nn:bsPutUInt32:arithOp:7:shr:ror
-rwxr-xr-x 1 pwnslinger pwnslinger  68K Jan  6 12:36 bzip2_base.amd64-m64-gcc42-nn:bsPutUInt32:arithOp:7:shr:shl
-rwxr-xr-x 1 pwnslinger pwnslinger  68K Jan  6 12:36 bzip2_base.amd64-m64-gcc42-nn:bsPutUInt32:arithOp:7:shr:sub
-rwxr-xr-x 1 pwnslinger pwnslinger  68K Jan  6 12:35 bzip2_base.amd64-m64-gcc42-nn:bsPutUInt32:brOp:9:jmp:ja
-rwxr-xr-x 1 pwnslinger pwnslinger  68K Jan  6 12:35 bzip2_base.amd64-m64-gcc42-nn:bsPutUInt32:brOp:9:jmp:jae
-rwxr-xr-x 1 pwnslinger pwnslinger  68K Jan  6 12:35 bzip2_base.amd64-m64-gcc42-nn:bsPutUInt32:brOp:9:jmp:jb
-rwxr-xr-x 1 pwnslinger pwnslinger  68K Jan  6 12:35 bzip2_base.amd64-m64-gcc42-nn:bsPutUInt32:brOp:9:jmp:jbe
-rwxr-xr-x 1 pwnslinger pwnslinger  68K Jan  6 12:35 bzip2_base.amd64-m64-gcc42-nn:bsPutUInt32:brOp:9:jmp:je
-rwxr-xr-x 1 pwnslinger pwnslinger  68K Jan  6 12:35 bzip2_base.amd64-m64-gcc42-nn:bsPutUInt32:brOp:9:jmp:jecxz
-rwxr-xr-x 1 pwnslinger pwnslinger  68K Jan  6 12:35 bzip2_base.amd64-m64-gcc42-nn:bsPutUInt32:brOp:9:jmp:jg

```


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

# Transfer files
To transfer mutations from server to your local use the following command:  
`scp -r mohsen@cips.dyndns.org:~/sn4ke/results/lbm_base.amd64-m64-gcc42-nn .`  

# Bug Reports 
During our research we reported the following issues to Grammatech to help us with. 

1. There was a segmentation fault received on bzip2 binary. Issue happened when we tried to reassemble the GTIRB representation back to an executable. We reported the issue and the problem is related to the remaining .ctors and .dtors sections, which seems to conflict with the ones added by the linker. Here is the link:  [issue #3: re-compilation error on bzip2](https://github.com/GrammaTech/gtirb-pprinter/issues/3)  

# Tips on running the experiments  
In some rare cases, mutated binary creates a series of fork processes and filled up the CPU on our clusters. One remediation is to check for CPU and memory utilization during benchspec run to keep usage under a certain threshold. While we extended the disk space to 1TB on each cluster, on EC2 servers, swap partition took a lot of space to make sure server can stay up and functional. This race continues until server reaches a state in which the whole disk space has been used up. To prevent this we suggest the following:  

1. After each successful experiment, clean-up the `benchspec/CPU2006/*/run/*` directory. These files are not needed for the next run and dumped here from the previous run.  
2. Kill orphan childs of infinite looped processes or forked ones, because these processes eat up a lot of memory and increase paging.  For example, we want to kill orphan processes of `milc` binary:  
    ```bash
        $ df -h
            Filesystem      Size  Used Avail Use% Mounted on
            udev             30G     0   30G   0% /dev
            tmpfs           5.9G  920K  5.9G   1% /run
            /dev/xvda1      970G  579G  391G  60% /
            tmpfs            30G     0   30G   0% /dev/shm
        $ pkill -9 -f milc
        $ df -h
            Filesystem      Size  Used Avail Use% Mounted on
            udev             30G     0   30G   0% /dev
            tmpfs           5.9G  920K  5.9G   1% /run
            /dev/xvda1      970G  195G  776G  21% /
            tmpfs            30G     0   30G   0% /dev/shm
    ```  
    To perform this task automatically, we created a service to kill processes under certain names, `PROC`, with a lifespan more than a `THRESHOLD` seconds.  
    ```bash
    PROC=$1
    THRESHOLD=$2
    for p in $(ps -eo comm,pid,etimes | awk '/^PROC/ {if ($3 > THRESHOLD) {print $2}}'); do kill -9 $p; done
    ```  