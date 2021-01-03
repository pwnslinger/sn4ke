## File description:
- revng: to replace the default revng file after installing the revng tool
- mutateIR.sh: to replace the same file after installing the srciror mutator
- Mutate.cpp: srciror mutation pass adjusted for llvm version 10.0.1

## Steps to get the setup:
1. install llvm and clang version 10.0.1
2. add the adjusted mutation pass
3. install revng through their orchestra repository
4. install srciror
5. add the mutateIR.sh file under a folder named "Examples_revng" in the srciror directory
6. adjust the installation paths in the mutateIR.sh file
7. add the folder PythonWrappers_revng/ to the srciror directory
