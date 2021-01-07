#define DEBUG_TYPE "mutation"
#include "llvm/Pass.h"
#include "llvm/ADT/Statistic.h"
#include "llvm/IR/Constants.h"
#include "llvm/IR/DebugInfoMetadata.h"
#include "llvm/IR/Function.h"
#include "llvm/IR/Instruction.h"
#include "llvm/IR/Instructions.h"
#include "llvm/IR/InstIterator.h"
#include "llvm/IR/Module.h"
#include "llvm/Support/CommandLine.h"
#include "llvm/Support/raw_ostream.h"
#include "llvm/Transforms/Utils/BasicBlockUtils.h"

using namespace llvm;

static cl::opt<unsigned> MutationLocation("mutation_loc", cl::desc("Specify the instruction number that you would like to mutate"), cl::value_desc("unsigned integer"));

static cl::opt<unsigned> FileCode("file_code", cl::desc("Specify the hash of the file name we are instrumenting for coverage"), cl::value_desc("unsigned integer"));

static cl::opt<unsigned> MutationOperandLocation("mutation_op_loc", cl::desc("Specify the instruction number that you would like to mutate"), cl::value_desc("unsigned integer"));

static cl::opt<unsigned> MutationOp("mutation_op", cl::desc("Specify operator to mutate with e.g., 8:add, 10:sub, 12:mul"), cl::value_desc("unsigned integer"));

static cl::opt<int> MutationValue("mutation_val", cl::desc("Specify the value that will be used to replace the found integer constants"), cl::value_desc("integer"));

static cl::opt<int> IcmpPred("icmp_pred", cl::desc("Specify the icmp instruction predicate id"), cl::value_desc("integer"));

static cl::opt<int> DeleteLocation("del_loc", cl::desc("Specify the instruction number to be deleted"), cl::value_desc("integer"));

STATISTIC(InstCount, "Counts number of instructions");
STATISTIC(ConstantCount, "Counts number of constants");
STATISTIC(IcmpCount, "Counts number of Icmp instructions");
STATISTIC(LogicalCount, "Counts number of logical instructions");
STATISTIC(ArithCount, "Counts number of arithmetic instructions");

namespace {
  struct ICRMutate : public FunctionPass {
    static char ID; // Pass identification, replacement for typeid
    ICRMutate() : FunctionPass(ID) {}

    virtual bool runOnFunction(Function &F) {
      if (F.getName() != "root") // pk: skip extra functions
        return false; // pk
      for (inst_iterator I = inst_begin(F), E = inst_end(F); I != E; ++I) {
        InstCount++;
        findAndMutateConstantOperands(&*I, &F);
      }
      return false;
    }

    void findAndMutateConstantOperands(Instruction *I, Function* F){
      // loop through operands,
      int counter = -1;
      for (User::op_iterator i = I->op_begin(), e = I->op_end(); i != e; ++i) {
        counter++;
        Value *v = *i;
        if (isa<Constant>(v)) {
          if (dyn_cast<ConstantInt>(v)) {
            if (InstCount == MutationLocation && counter == MutationOperandLocation) {
             *i = ConstantInt::get(v->getType(), MutationValue);
              break;
            }
          }
        }
      }
    }

  };
}

char ICRMutate::ID = 0;
static RegisterPass<ICRMutate> X("icrmutate", "Apply Constant Replacement Mutation");

namespace {
  struct Coverage : public ModulePass {
    static char ID; // Pass identification, replacement for typeid
    // pk Function *hook;
    FunctionCallee hook;
    CallInst *PutCall;

    Coverage() : ModulePass(ID) {}

    void walkFunction(Function *F, Module& M){
      for (inst_iterator I = inst_begin(F), E = inst_end(F); I != E; ++I) {
        Instruction *Inst = &*I;
        InstCount += 1;
        // to avoid: PHI nodes not grouped at top of basic block!
        if (!isa<PHINode>(Inst)) {
          Value *Args[2];
          Args[0] = ConstantInt::get(Type::getInt32Ty(F->getContext()), InstCount);
          Args[1] = ConstantInt::get(Type::getInt64Ty(F->getContext()), FileCode);
          Instruction *newInst = CallInst::Create(hook, Args, "", Inst);    // Insert call to the coverage helper to record
        }
      }
    }
    
    virtual bool runOnModule(Module &M) {
      // Insert the coverage helper function into the module
      //pk Constant *PutFn;
      FunctionCallee PutFn; //pk
// pk      PutFn = M.getOrInsertFunction("SRCIRORLlvmCoverage", Type::getVoidTy(M.getContext()), Type::getInt32Ty(M.getContext()), Type::getInt64Ty(M.getContext()), NULL);
      PutFn = M.getOrInsertFunction("SRCIRORLlvmCoverage", Type::getVoidTy(M.getContext()), Type::getInt32Ty(M.getContext()), Type::getInt64Ty(M.getContext()));
      //hook = cast<Function *>(PutFn); //pk
      hook = PutFn; //pk
      //pk hook = cast<Function>(PutFn);
      for (Module::iterator I = M.begin(), E = M.end(); I != E; ++I) {
        Function *F = &*I;
        if (F->getName() != "root") // pk: skip extra functions
          continue; // pk
        walkFunction(F, M);
      }
      return true;
    }

  };
}

char Coverage::ID = 0;
static RegisterPass<Coverage> V("coverage", "Instrument for coverage collection");


// enum Predicate {eq=1,ne=2,ugt=3,uge=4,ult=5,ule=6,sgt=7,sge=8,slt=9,sle=10};
enum InstrMut {e_arith = 60, e_icmp = 61, e_logical = 62};

namespace {
  struct GetICRMutationLocs : public FunctionPass {
    static char ID; // Pass identification, replacement for typeid
    GetICRMutationLocs() : FunctionPass(ID) {}

    virtual bool runOnFunction(Function &F) {
      if (F.getName() != "root") // pk: skip extra functions
        return false; // pk
      for (inst_iterator I = inst_begin(F), E = inst_end(F); I != E; ++I) {
        InstCount++;
        findConstantOperands(&*I, &F);
      }
      return false;
    }

    void findConstantOperands(Instruction *I, Function* F){
      // loop through operands,
      int counter = -1;
      for (User::op_iterator i = I->op_begin(), e = I->op_end(); i != e; ++i) {
        counter++;
        Value *v = *i;
        if (isa<Constant>(v)) {
          if (ConstantInt* CI = dyn_cast<ConstantInt>(v)) {
            int IntegerValue = CI->getSExtValue();  // TODO: Is it okay to always sign-extend?
            errs() << InstCount << ":" << counter << ":" << CI->getValue() << ":";
            switch (IntegerValue) {
              case 1:
                errs() << -1 << "," << 0 <<"," << 2 << ",\n";
                break;
              case -1:
                errs() << 1 << "," << 0 << "," << -2 << ",\n";
                break;
              case 0:
                errs() << 1 << "," << -1 << ",\n";
                break;
              default:
                errs() << 0 << "," << 1 << "," << -1 << "," << IntegerValue + 1 << "," << IntegerValue - 1 << "," << IntegerValue * -1 << ",\n";
            }
          }
        }
      }
    }

  };
}

char GetICRMutationLocs::ID = 0;
static RegisterPass<GetICRMutationLocs> Y("getICRMutationLocs", "Get the locations where we can apply ICR mutation.");


namespace {
  // pk struct GetBinaryOperators : public BasicBlockPass {   // TODO: Can/should this be a FunctionPass?
  struct GetBinaryOperators : public FunctionPass {   // TODO: Can/should this be a FunctionPass?
    static char ID; // Pass identification, replacement for typeid
    // pk GetBinaryOperators() : BasicBlockPass(ID) {}
    GetBinaryOperators() : FunctionPass(ID) {}

    bool checkOpcode(unsigned opcode, int operators[], int len, int op_type) {
      bool done = false;
      for (int i = 0; i < len; i++) {
        if (operators[i] == opcode) {
          done = true;
          errs() << InstCount << ":" << op_type << ":"; //TODO: Do we want to output the original opcode as well?
          for (int j = 0; j < len; j++) {
            if (i != j) {
              errs () << operators[j] << ",";
            }
          }
          errs() << "\n";
          break;
        }
      }
      return done;
    }

    void outputIcmpPredicates(int skip) {
      int cmpinsts[] = {CmpInst::ICMP_EQ, CmpInst::ICMP_NE, CmpInst::ICMP_UGT, CmpInst::ICMP_UGE, CmpInst::ICMP_ULT, CmpInst::ICMP_ULE, CmpInst::ICMP_SGT, CmpInst::ICMP_SGE, CmpInst::ICMP_SLT, CmpInst::ICMP_SLE};
      int len = 10;
      for (int i = 0; i < len; i++) {
        if (cmpinsts[i] != skip)
          errs() << cmpinsts[i] << ",";
      }
      errs() << "\n";
    }

    void handle_cmp(CmpInst *cmpInst) {
      outputIcmpPredicates(cmpInst->getPredicate());
    }

    // pk virtual bool runOnBasicBlock(BasicBlock &BB) {
    virtual bool runOnFunction(Function &F) {

      if (F.getName() != "root") // pk: skip extra functions
        return false; // pk

      for (Function::iterator b = F.begin(), be = F.end(); b != be; ++b) {
		    BasicBlock* BB = &*b;

	    int arithmeticOps[] = {Instruction::Add, Instruction::Sub, Instruction::Mul, Instruction::UDiv, Instruction::SDiv, Instruction::URem, Instruction::SRem};
	    int floatingOps[] = {Instruction::FAdd, Instruction::FSub, Instruction::FMul, Instruction::FDiv, Instruction::FRem};
	    int logicalOps[] = {Instruction::And, Instruction::Or, Instruction::Xor};

	    for (BasicBlock::iterator DI = BB->begin(); DI != BB->end();) {
	      Instruction *I = &*DI++;
	      InstCount++;
	      if (ICmpInst *cmpInst = dyn_cast<ICmpInst>(I)) {
	        errs() << InstCount << ":" << e_icmp << ":";
	        handle_cmp(cmpInst);
	      } else {
	        unsigned opcode = I->getOpcode();
	        bool done = checkOpcode(opcode, arithmeticOps, sizeof(arithmeticOps) / sizeof(int), e_arith);
	        if (!done) {
	          done = checkOpcode(opcode, logicalOps, sizeof(logicalOps) / sizeof(int), e_logical);
	          if (!done) {
	            checkOpcode(opcode, floatingOps, sizeof(floatingOps) / sizeof(int), e_arith);
	          }
	        }
	      }
	    }
	  }


      return false;
    }

  };
}

char GetBinaryOperators::ID = 0;
static RegisterPass<GetBinaryOperators> Z("getBinaryOperators", "Get the occurences of the given binary operators we want to mutate");

namespace {
  // pk struct SwapBinaryOperators : public BasicBlockPass {
  struct SwapBinaryOperators : public FunctionPass {
    static char ID;
    // pk SwapBinaryOperators() : BasicBlockPass(ID) {}
    SwapBinaryOperators() : FunctionPass(ID) {}

    Instruction* getRequestedMutationBinaryOp(Instruction* I) {
      // TODO: Is there a better way to convert integer representation of opcode to BinaryOp instance?
      switch (MutationOp) {
        case Instruction::Add:
          return BinaryOperator::Create(Instruction::Add, I->getOperand(0), I->getOperand(1), "optimute");
        case Instruction::Sub:
          return BinaryOperator::Create(Instruction::Sub, I->getOperand(0), I->getOperand(1), "optimute");
        case Instruction::Mul:
          return BinaryOperator::Create(Instruction::Mul, I->getOperand(0), I->getOperand(1), "optimute");
        case Instruction::UDiv:
          return BinaryOperator::Create(Instruction::UDiv, I->getOperand(0), I->getOperand(1), "optimute");
        case Instruction::SDiv:
          return BinaryOperator::Create(Instruction::SDiv, I->getOperand(0), I->getOperand(1), "optimute");
        case Instruction::URem:
          return BinaryOperator::Create(Instruction::URem, I->getOperand(0), I->getOperand(1), "optimute");
        case Instruction::SRem:
          return BinaryOperator::Create(Instruction::SRem, I->getOperand(0), I->getOperand(1), "optimute");

        case Instruction::FAdd:
          return BinaryOperator::Create(Instruction::FAdd, I->getOperand(0), I->getOperand(1), "optimute");
        case Instruction::FSub:
          return BinaryOperator::Create(Instruction::FSub, I->getOperand(0), I->getOperand(1), "optimute");
        case Instruction::FMul:
          return BinaryOperator::Create(Instruction::FMul, I->getOperand(0), I->getOperand(1), "optimute");
        case Instruction::FDiv:
          return BinaryOperator::Create(Instruction::FDiv, I->getOperand(0), I->getOperand(1), "optimute");
        case Instruction::FRem:
          return BinaryOperator::Create(Instruction::FRem, I->getOperand(0), I->getOperand(1), "optimute");

        case Instruction::And:
          return BinaryOperator::Create(Instruction::And, I->getOperand(0), I->getOperand(1), "optimute");
        case Instruction::Or:
          return BinaryOperator::Create(Instruction::Or, I->getOperand(0), I->getOperand(1), "optimute");
        case Instruction::Xor:
          return BinaryOperator::Create(Instruction::Xor, I->getOperand(0), I->getOperand(1), "optimute");
      }
    }


    Instruction* getRequestedMutantIcmpInst(Instruction* I, ICmpInst* cmpInst) {
      switch(IcmpPred) {
        case CmpInst::ICMP_EQ:
          return CmpInst::Create(cmpInst->getOpcode(), CmpInst::ICMP_EQ, I->getOperand(0), I->getOperand(1), "optimute");
        case CmpInst::ICMP_NE:
          return CmpInst::Create(cmpInst->getOpcode(), CmpInst::ICMP_NE, I->getOperand(0), I->getOperand(1), "optimute");
        case CmpInst::ICMP_UGT:
          return CmpInst::Create(cmpInst->getOpcode(), CmpInst::ICMP_UGT, I->getOperand(0), I->getOperand(1), "optimute");
        case CmpInst::ICMP_UGE:
          return CmpInst::Create(cmpInst->getOpcode(), CmpInst::ICMP_UGE, I->getOperand(0), I->getOperand(1), "optimute");
        case CmpInst::ICMP_ULT:
          return CmpInst::Create(cmpInst->getOpcode(), CmpInst::ICMP_ULT, I->getOperand(0), I->getOperand(1), "optimute");
        case CmpInst::ICMP_ULE:
          return CmpInst::Create(cmpInst->getOpcode(), CmpInst::ICMP_ULE, I->getOperand(0), I->getOperand(1), "optimute");
        case CmpInst::ICMP_SGT:
          return CmpInst::Create(cmpInst->getOpcode(), CmpInst::ICMP_SGT, I->getOperand(0), I->getOperand(1), "optimute");
        case CmpInst::ICMP_SGE:
          return CmpInst::Create(cmpInst->getOpcode(), CmpInst::ICMP_SGE, I->getOperand(0), I->getOperand(1), "optimute");
        case CmpInst::ICMP_SLT:
          return CmpInst::Create(cmpInst->getOpcode(), CmpInst::ICMP_SLT, I->getOperand(0), I->getOperand(1), "optimute");
        case CmpInst::ICMP_SLE:
          return CmpInst::Create(cmpInst->getOpcode(), CmpInst::ICMP_SLE, I->getOperand(0), I->getOperand(1), "optimute");
      }
    }


    // pk virtual bool runOnBasicBlock(BasicBlock &BB) {
    virtual bool runOnFunction(Function &F) {

      if (F.getName() != "root") // pk: skip extra functions
        return false; // pk

		for (Function::iterator b = F.begin(), be = F.end(); b != be; ++b) {
			BasicBlock* BB = &*b;


			// figure out what instruction type are we dealing with
			// if icmp, figure out what predicate do we need
			for (BasicBlock::iterator DI = BB->begin(); DI != BB->end();) {
			  Instruction *I = &*DI++;
			  InstCount++;
			  if (ICmpInst *cmpInst = dyn_cast<ICmpInst>(I)) {
			    if (InstCount == MutationLocation) {
			      Instruction *altI = getRequestedMutantIcmpInst(I, cmpInst);
			      ReplaceInstWithInst(I, altI);
			    }
			  }
			  else if (isa<BinaryOperator>(*I)) {
			    if (InstCount == MutationLocation) {
			         Instruction* altI = getRequestedMutationBinaryOp(I);
			         ReplaceInstWithInst(I, altI);
			     }
			  }
			}
		
		}

		return false;
    }

  };
}

char SwapBinaryOperators::ID = 0;
static RegisterPass<SwapBinaryOperators> C("swapBinaryOperators", "Replace the binary operator.");


namespace {
  // pk struct DeleteInstr : public BasicBlockPass {
  struct DeleteInstr : public FunctionPass {
    static char ID; // Pass identification, replacement for typeid
    // pk DeleteInstr() : BasicBlockPass(ID) {}
    DeleteInstr() : FunctionPass(ID) {}

    // pk virtual bool runOnBasicBlock(BasicBlock &BB) {
    virtual bool runOnFunction(Function &F) {

      if (F.getName() != "root") // pk: skip extra functions
        return false; // pk

		for (Function::iterator b = F.begin(), be = F.end(); b != be; ++b) {
			BasicBlock *BB = &*b;



			for (BasicBlock::iterator DI = BB->begin(); DI != BB->end();) {
			  Instruction *I = &*DI++;
			  InstCount++;
			  if (InstCount == DeleteLocation) {
			    I->eraseFromParent();
			  }
			}

    	}

		return false;
    }

  };
}
char DeleteInstr::ID = 0;
static RegisterPass<DeleteInstr> D("deleteInstr", "Delete an Instruction Mutation");

//////////////////////////////////////////////////////////////
/// CODE BELOW IS NOT REVIEWED/CLEANED, WE MAY NOT NEED IT ///
//////////////////////////////////////////////////////////////

// InstCount, "Counts number of instructions";
// ConstantCount, "Counts number of constants";
// IcmpCount, "Counts number of Icmp instructions";
// LogicalCount, "Counts number of logical instructions";
// ArithCount, "Counts number of arithmetic instructions";

namespace {
  // pk struct GetStats : public BasicBlockPass {
  struct GetStats : public FunctionPass {
    static char ID;
    // pk GetStats() : BasicBlockPass(ID) {}
    GetStats() : FunctionPass(ID) {}

    bool checkOpcode(unsigned opcode, int operators[], int len, int op_type) {
      for (int i = 0; i < len; i++) {
        if (operators[i] == opcode)
          return true;
      }
      return false;
    }

    void findConstantOperands(Instruction *I){
      // loop through operands,
      int counter = -1;
      for (User::op_iterator i = I->op_begin(), e = I->op_end(); i != e; ++i) {
        counter++;
        Value *v = *i;
        if (isa<Constant>(v)) {
          if (dyn_cast<ConstantInt>(v))
            ConstantCount++;
        }
      }
    }

    // pk virtual bool runOnBasicBlock(BasicBlock &BB) {
    virtual bool runOnFunction(Function &F) {

      if (F.getName() != "root") // pk: skip extra functions
        return false; // pk

		for (Function::iterator b = F.begin(), be = F.end(); b != be; ++b) {
			BasicBlock *BB = &*b;


			int arithmeticOps[] = {Instruction::Add, Instruction::Sub, Instruction::Mul, Instruction::UDiv, Instruction::SDiv};
			int floatingOps[] = {Instruction::FAdd, Instruction::FMul, Instruction::FDiv};
			int logicalOps[] = {Instruction::And, Instruction::Or, Instruction::Xor};

			for(BasicBlock::iterator DI = BB->begin(); DI != BB->end(); ) {
			  Instruction *I = &*DI++;
			  InstCount++;

			  findConstantOperands(I);
			  if (dyn_cast<ICmpInst>(I)) {
			    IcmpCount++;
			  } else {
			    unsigned opcode = I->getOpcode();
			    bool done = checkOpcode(opcode, arithmeticOps, sizeof(arithmeticOps)/4, e_arith);
			    if (done)
			      ArithCount++;
			    else {
			      done = checkOpcode(opcode, logicalOps, sizeof(logicalOps)/4, e_logical);
			      if (done)
			        LogicalCount++;
			      else {
			        done = checkOpcode(opcode, floatingOps, sizeof(floatingOps)/4, e_arith);
			        if (done)
			          ArithCount++;
			      }
			    }
			  }
			// // print the summary of findings so far
			//   errs() << "Inst Summary: " << InstCount << "," << IcmpCount << "," << ConstantCount << "," << ArithCount << "," << LogicalCount << "\n";
			}
			// print the summary of findings so far
			errs() << InstCount << "," << IcmpCount << "," << ConstantCount << "," << ArithCount << "," << LogicalCount << "\n";

		}
		return false; // pk
    }

  };
}
char GetStats::ID = 0;
static RegisterPass<GetStats> G("getStats", "Get some stats about mutation locs");


namespace {
static const int num_opcodes = 59;
static int opcodeCount[num_opcodes];
static int constCount[num_opcodes];

  // pk struct AllInstStats : public BasicBlockPass {
  struct AllInstStats : public FunctionPass {
    static char ID;
    // pk AllInstStats() : BasicBlockPass(ID) {}
    AllInstStats() : FunctionPass(ID) {}

    void printOpcodeStats() {
      for (int i = 0; i < num_opcodes; i++) {
        if (i==0) {
          errs() << "Total:" << constCount[i] << ":" << opcodeCount[i] << ",";
        }
        else {
          errs() << Instruction::getOpcodeName(i) << ":" << constCount[i] << ":" << opcodeCount[i] << ",";
        }
        if (i == num_opcodes -1) {
          errs() << "\n";
        }
      }
    }

    void findConstantOperands(Instruction *I){
      // loop through operands,
      int counter = -1;
      for (User::op_iterator i = I->op_begin(), e = I->op_end(); i != e; ++i) {
        counter++;
        Value *v = *i;
        if (isa<Constant>(v)) {
          if (dyn_cast<ConstantInt>(v))
            constCount[I->getOpcode()]++;
        }
      }
    }


    // pk virtual bool runOnBasicBlock(BasicBlock &BB) {
    virtual bool runOnFunction(Function &F) {

      if (F.getName() != "root") // pk: skip extra functions
        return false; // pk

		for (Function::iterator b = F.begin(), be = F.end(); b != be; ++b) {
			BasicBlock *BB = &*b;


			for (BasicBlock::iterator DI = BB->begin(); DI != BB->end(); ) {
			  Instruction *I = &*DI++;
			  opcodeCount[0]++;
			  errs() << "the opcode is " << I->getOpcode() << "\n";
			  errs() << "LLVM thinks the opcode is: " << I->getOpcodeName() << "\n";
			  opcodeCount[I->getOpcode()]++;
			  findConstantOperands(I);
			}
			printOpcodeStats();

		}

		return false;
    }

  };
}
char AllInstStats::ID = 0;
static RegisterPass<AllInstStats> A("allInstStats", "Get stats about all instructions");
