import os, sys

CWD = os.path.dirname(os.path.abspath(__file__))
from bashUtil import executeCommand

def getSummaryDir():
    # make the summary directory if does not exist
    # also makes the ir-coverage/ directory
    #pk summaryDir = os.path.join(os.getenv("HOME"), ".srciror_fast")
    summaryDir = CWD + '/../Examples_revng_fast/mutation_results/srciror/' 
    if not os.path.exists(summaryDir):
        os.makedirs(summaryDir)
    return summaryDir


def findSrcIndices(arg_list, ext):
    source_indices = [i for i, word in enumerate(arg_list) if word.endswith(ext)]
    return source_indices


def run(task, taskFunction):
    llvm_bin_dir = os.environ["SRCIROR_LLVM_BIN"]
    clang = os.path.join(llvm_bin_dir, 'clang')
    #clang = os.path.join('/home/pc-5/fi-bin/revng_dir/orchestra/root/bin/', 'clang') # pk: changed to the local installation
    opt = os.path.join(llvm_bin_dir, 'opt')
    mutation_lib = os.environ["SRCIROR_LLVMMutate_LIB"] # path to llvm-build/Release+Asserts/lib/LLVMMutate.so
    if task == "coverage":
        our_lib = os.environ["SRCIROR_COVINSTRUMENTATION_LIB"] # path to IRMutation/InstrumentationLib/SRCIRORCoverageLib.o
    else:
        our_lib = ""
    coverageDir = os.path.join(getSummaryDir(), "ir-coverage")  # guarantees directory is made
    if not os.path.exists(coverageDir):
        os.makedirs(coverageDir)
    log_file = os.path.join(coverageDir, "hash-map")
    opt_command = opt + " -load " + mutation_lib
    args = sys.argv[1:]

    if '-fstack-usage' in args: # TODO: What is -fstack-usage?
        args.remove('-fstack-usage')
    compiler = clang
    #print('logging compile flags: ' + ' '.join(args))

    # if the build system is checking for the version flags, we don't mess it up, just delegate to the compiler
    if "--version" in args or "-V" in args:
        out, err, _ = executeCommand([compiler] + args, True)
        return 1

    ###### instrument ######
    # if the command contains a flag that prevents linking, then it's
    # not generating an executable, then we should be able to generate
    # bitcode and instrument it for the task
    # 1. find if command is compiling some source .c file
    src_indices = findSrcIndices(args, ".c")
    if not src_indices: # there is no source code to instrument, so we want to try and link, no changes
        #print('Looking to link: ' + str([compiler, our_lib] + args))
        out, err, _ = executeCommand([compiler, our_lib] + args, True)
        #print(str(out))
        #print(str(err))
        return 1    # TODO: Why do we return 1 instead of 0?

    # if there are multiple src files, only care about the first
    src_index = src_indices[0]
    src_file = args[src_indices[0]]

    # 2. see if there is a specified -o; if exists, use it to determine name of intermediate .ll file
    new_args = list(args)
    try:
        dash_o_index = new_args.index('-o')
        out_name = new_args[dash_o_index + 1]
        #print("we got the dash o index")
        #print("the out name is : " + out_name)
    except:
        out_name = src_file # if does not exist, use the src file name as the base
        #print("we did not find dash o index, so we are using src: " + src_file)
        dash_o_index = len(new_args)    # filling up the args with some empty placeholders for upcoming update
        new_args += ["-o", ""]
    bitcode_file = os.path.dirname(out_name) + os.path.basename(out_name).split(".")[0] + ".ll" # expect only one . in the name
    #print("the bitcode file name is: " + bitcode_file)

    # 3. put flags to generate bitcode
    new_args[dash_o_index + 1] = bitcode_file
    #print("we are emitting llvm bitcode: " + " ".join([clang, '-S', '-emit-llvm'] + new_args))
    executeCommand([clang, '-S', '-emit-llvm'] + new_args)

    # 4. instrument the bitcode for the specified task
    taskFunction(bitcode_file, src_file, opt_command, log_file)

    # 5. compile the .ll into the real output so compilation can proceed peacefully
    #    replace the input C src file with the bitcode file we determined
    compiling_args = list(args)
    compiling_args[src_index] = bitcode_file
    clang_pk = os.path.join('/home/pc-5/fi-bin/revng_dir/orchestra/root/bin/', 'clang') # pk: changed to the local installation
    # pk command = [clang] + compiling_args + [our_lib]
    command = [clang_pk] + compiling_args + [our_lib]
    #print("we are generating the output from the .ll with the command " + " ".join(command))
    out, err, _ = executeCommand(command, True)
    #print("out: ") # pk
    #print(str(out))
    #print("err: ") # pk
    #print(str(err))
    #print("done ") # pk
    
    ll_dir = CWD+'/../Examples_revng_fast/mutation_results/ll/'
    bin_dir = CWD+'/../Examples_revng_fast/mutation_results/bin/'
    if os.path.isdir(ll_dir):
        for ll_name in os.listdir(ll_dir):
            bin_name = ll_name[:-3] 
            output_arg = ["-o", bin_dir + bin_name]
            #command = [clang_pk] + [ll_dir + ll_name] + [' -o '] +  [bin_dir + bin_name]
            command = [clang_pk] + [ll_dir + ll_name] 
            #print(command)
            #print("we are generating the output from the .ll with the command " + " ".join(command))
            out, err, _ = executeCommand(command + output_arg , True)



    return 1


def run_ll(task, taskFunction, runCompile): #pk
    llvm_bin_dir = os.environ["SRCIROR_LLVM_BIN"]
    clang = os.path.join(llvm_bin_dir, 'clang')
    opt = os.path.join(llvm_bin_dir, 'opt')
    revng_bin_dir = os.environ["REVDIR"] # pk
    revng = os.path.join(revng_bin_dir, 'revng') # pk
    revng = revng + " --verbose translate " # pk
    #pk mutation_lib = os.environ["SRCIROR_LLVMMutate_LIB"] # path to llvm-build/Release+Asserts/lib/LLVMMutate.so
    mutation_lib = os.environ["SRCIROR_LLVMMutate_LIB"] # path to llvm-build/Release+Asserts/lib/LLVMMutateRevng.so
    if task == "coverage":
        our_lib = os.environ["SRCIROR_COVINSTRUMENTATION_LIB"] # path to IRMutation/InstrumentationLib/SRCIRORCoverageLib.o
    else:
        our_lib = ""
    coverageDir = os.path.join(getSummaryDir(), "ir-coverage")  # guarantees directory is made
    if not os.path.exists(coverageDir):
        os.makedirs(coverageDir)
    log_file = os.path.join(coverageDir, "hash-map")
    opt_command = opt + " -load " + mutation_lib
    args = sys.argv[1:]

    if '-fstack-usage' in args: # TODO: What is -fstack-usage?
        args.remove('-fstack-usage')
    compiler = clang
    #print('logging compile flags: ' + ' '.join(args))

    # if the build system is checking for the version flags, we don't mess it up, just delegate to the compiler
    if "--version" in args or "-V" in args:
        out, err, _ = executeCommand([compiler] + args, True)
        return 1

    ###### instrument ######
    # if the command contains a flag that prevents linking, then it's
    # not generating an executable, then we should be able to generate
    # bitcode and instrument it for the task
    # 1. find if command has the input bitcode .ll 

    #pk src_indices = findSrcIndices(args, ".c")
    inp_bc_indices = findSrcIndices(args, ".ll")
    out_index = [i for i, word in enumerate(args) if word=="-o"][0] # pk

    if not inp_bc_indices:
        #print("Error: no bitcode .ll file given")
        return 1    # TODO: Why do we return 1 instead of 0?

    # if there are multiple bc files, only care about the first
    inp_bc_index = inp_bc_indices[0]
    inp_bc_file = args[inp_bc_indices[0]]

    # 2. see if there is a specified -o; if exists, use it to determine name of intermediate .ll file
    new_args = list(args)
    try:
        dash_o_index = new_args.index('-o')
        out_name = new_args[dash_o_index + 1]
        #print("we got the dash o index")
        #print("the out name is : " + out_name)
    except:
        out_name = inp_bc_file # if does not exist, use the src file name as the base
        #print("we did not find dash o index, so we are using src: " + inp_bc_file)
        dash_o_index = len(new_args)    # filling up the args with some empty placeholders for upcoming update
        new_args += ["-o", ""]
    #pk bitcode_file = os.path.dirname(out_name) + os.path.basename(out_name).split(".")[0] + "_coverage.ll" # expect only one . in the name
    bitcode_file = os.path.dirname(out_name) + os.path.basename(out_name) + '_mutate' + ".ll" 
    #print("the bitcode file name is: " + bitcode_file)

#pk: no need to generate bitcode
#pk    # 3. put flags to generate bitcode
#pk    new_args[dash_o_index + 1] = bitcode_file
#pk    print("we are emitting llvm bitcode: " + " ".join([clang, '-S', '-emit-llvm'] + new_args))
#pk    executeCommand([clang, '-S', '-emit-llvm'] + new_args)

    # 4. instrument the bitcode for the specified task
    #pk taskFunction(bitcode_file, inp_bc_file, opt_command, log_file)
    taskFunction(bitcode_file, inp_bc_file, opt_command, log_file)

    # 5. compile the .ll into the real output so compilation can proceed peacefully
    #    replace the input C src file with the bitcode file we determined
    compiling_args = list(args)
    #print(inp_bc_index)
    if task == "coverage":
        compiling_args[inp_bc_index] = bitcode_file
        dash_o_index = compiling_args.index('-o')
        compiling_args[dash_o_index+1] = compiling_args[dash_o_index+1] + "_mutated"
        command = [clang] + compiling_args + [our_lib]
    else:
        compiling_args[inp_bc_index] = inp_bc_file
        compiling_args.pop(out_index) # pk: no -o necessary
        compiling_args.insert(0," --ll ") # pk: --ll necessary before input ll file
        command = [revng] + compiling_args + [our_lib] # pk

    #print("out_index:")
    #print(out_index)

    #clang_pk = os.path.join('/home/pc-5/fi-bin/revng_dir/orchestra/root/bin/', 'clang') # pk: changed to the local installation  #pk
    # command = [clang] + compiling_args + [our_lib]
    #print("compiling_args:")
    #print(compiling_args)
    #command = [clang_pk] + compiling_args + [our_lib] # pk
#    print("we are generating the output from the .ll with the command " + " ".join(command))
    
#    if task != "coverage": # pk: don't compile for coverage
#        out, err, _ = executeCommand(command, True) # pk: don't compile for coverage

#    print("out: ") # pk
#    print(str(out))
#    print("err: ") # pk
#    print(str(err))
#    print("done ") # pk
    
    #if task != "coverage":
    if runCompile:
        ll_dir = CWD+'/../Examples_revng_fast/mutation_results/ll/'
        bin_dir = CWD+'/../Examples_revng_fast/mutation_results/bin/'
        if os.path.isdir(ll_dir):
            for ll_name in os.listdir(ll_dir):
                bin_name = ll_name[:-3] 
#                os.system('cp ' + ll_dir+ll_name + ' ' + ll_dir+'/../../') # copy ll file here
                os.system('mv ' + ll_dir+ll_name + ' ' + ll_dir+'/../../') # move ll file here
                copyFile = "cp " + out_name + "_lifted.ll.need.csv " + ll_dir+'/../../'+ bin_name + "_lifted.ll.need.csv"
                os.system(copyFile)
                copyFile = "cp " + out_name + "_lifted.ll.li.csv " + ll_dir+'/../../'+ bin_name + "_lifted.ll.li.csv"
                os.system(copyFile)
#                print(ll_name)
#                copyFile = "cp " + out_name + "_lifted.ll.need.csv " + bin_dir + bin_name + "_lifted.ll.need.csv"
#                os.system(copyFile)
#                copyFile = "cp " + out_name + "_lifted.ll.li.csv " + bin_dir + bin_name + "_lifted.ll.li.csv"
#                os.system(copyFile)
#                print(copyFile)
                output_arg = ["-o", bin_dir + bin_name]
                #command = [clang_pk] + [ll_dir + ll_name] + [' -o '] +  [bin_dir + bin_name] # pk
                #command = [clang_pk] + [ll_dir + ll_name]  # pk
                #command = [clang] + [ll_dir + ll_name] 
                #print(compiling_args)
                #command = [revng] + [' --ll ', ll_dir + ll_name, bin_dir + bin_name] # pk
                command = [revng] + [' --ll ', ll_dir+'/../../'+ll_name, ll_dir+'/../../'+out_name] # pk
                #print(command)
                #print("we are generating the output from the .ll with the command " + " ".join(command))
#                out, err, _ = executeCommand(command + output_arg , True)
                com = revng + ' --ll ' + ll_dir+'/../../'+ll_name +' ' + ll_dir+'/../../'+out_name
                #print(com)
                os.system(com)

                os.system('mv ' + ll_dir+'/../../'+bin_name+'.translated' + ' ' + bin_dir+bin_name) # move executable to bin directory
                # remove extra files
                os.system('rm ' +  ll_dir+'/../../'+ll_name+'.linked.ll') # delete generated file 
                os.system('rm ' +  ll_dir+'/../../'+ll_name+'.linked.ll.o') # delete generated file 
                os.system('rm ' +  ll_dir+'/../../'+ll_name) # delete copied ll file 
                rmFile = "rm " + ll_dir+'/../../'+ bin_name + "_lifted.ll.need.csv"
                os.system(rmFile)
                rmFile = "rm " + ll_dir+'/../../'+ bin_name + "_lifted.ll.li.csv"
                os.system(rmFile)


    return 1


def compile_ll(ll_dir, ll_name): #pk
    llvm_bin_dir = os.environ["SRCIROR_LLVM_BIN"]
    revng_bin_dir = os.environ["REVDIR"] # pk
    revng = os.path.join(revng_bin_dir, 'revng') # pk
    # revng = revng + " --verbose translate " # pk
    revng = revng + " translate " # pk
    args = sys.argv[1:]

    inp_bc_indices = findSrcIndices(args, ".ll")

    if not inp_bc_indices:
        print("Error: no bitcode .ll file given")
        return 1    # TODO: Why do we return 1 instead of 0?

    # if there are multiple bc files, only care about the first
    inp_bc_file = args[inp_bc_indices[0]]

    # 2. see if there is a specified -o; if exists, use it to determine name of intermediate .ll file
    new_args = list(args)
    try:
        dash_o_index = new_args.index('-o')
        out_name = new_args[dash_o_index + 1]
    except:
        out_name = inp_bc_file # if does not exist, use the src file name as the base
        #print("we did not find dash o index, so we are using src: " + inp_bc_file)
        dash_o_index = len(new_args)    # filling up the args with some empty placeholders for upcoming update
        new_args += ["-o", ""]

    # 5. compile the .ll into the real output so compilation can proceed peacefully
    #    replace the input C src file with the bitcode file we determined
    # ll_dir = CWD+'/../Examples_revng_fast/mutation_results/ll/'
    bin_dir = CWD+'/../Examples_revng_fast/mutation_results/bin/'
    bin_name = ll_name[:-3] 
    # print(bin_dir)
    # print(bin_name)
    # print(ll_dir)
    # print(ll_name)
    copyFile = "cp " + out_name + "_lifted.ll.need.csv " + CWD+'/../Examples_revng_fast/'+ bin_name + "_lifted.ll.need.csv"
    os.system(copyFile)
    copyFile = "cp " + out_name + "_lifted.ll.li.csv " + CWD+'/../Examples_revng_fast/'+ bin_name + "_lifted.ll.li.csv"
    os.system(copyFile)
    output_arg = ["-o", bin_dir + bin_name]
    # command = [revng] + [' --ll ', ll_dir+ll_name, ll_dir+out_name] # pk
    com = revng + ' --ll ' + CWD+'/../Examples_revng_fast/'+ll_name +' ' + CWD+'/../Examples_revng_fast/'+out_name
    os.system(com)

    os.system('mv ' + CWD+'/../Examples_revng_fast/'+bin_name+'.translated' + ' ' + bin_dir+bin_name) # move executable to bin directory
    # remove extra files
    os.system('rm ' +  CWD+'/../Examples_revng_fast/'+ll_name+'.linked.ll') # delete generated file 
    os.system('rm ' +  CWD+'/../Examples_revng_fast/'+ll_name+'.linked.ll.o') # delete generated file 
    os.system('rm ' +  CWD+'/../Examples_revng_fast/'+ll_name) # delete copied ll file 
    rmFile = "rm " + CWD+'/../Examples_revng_fast/'+ bin_name + "_lifted.ll.need.csv"
    os.system(rmFile)
    rmFile = "rm " + CWD+'/../Examples_revng_fast/'+ bin_name + "_lifted.ll.li.csv"
    os.system(rmFile)


    return 1
