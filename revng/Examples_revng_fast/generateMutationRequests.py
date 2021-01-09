import argparse
import os
from os.path import expanduser
import random

CWD = os.path.dirname(os.path.abspath(__file__))
HOME = expanduser("~")

def parseLines (testName):
    #print('home:')
    #print(HOME)
    #print(HOME+'/.srciror_fast/ir-coverage/hash-map')
    hash_value = '0'
    #with open(HOME+'/.srciror_fast/ir-coverage/hash-map', 'r') as hash_map:
    with open(CWD+'/mutation_results/srciror/ir-coverage/hash-map', 'r') as hash_map:
        for line in hash_map:
            #print('line: ')
            #print(line)
            if testName in line:
                file_name = line.strip().split(':')[0]
                hash_value = line.strip().split(':')[1]
                #print(file_name)
                #print(hash_value)
                #print(line)

	req = []
	req_num = 0 
    #with open(HOME+'/.srciror_fast/bc-mutants/'+hash_value, 'r') as mutations:
    i = 0 # for debugging
    with open(CWD+'/mutation_results/srciror/bc-mutants/'+hash_value, 'r') as mutations:
        for line in mutations:
            # i = i+1 # for debugging
            # print("i={}".format(i))
            # if (i==2): # for debugging
            #     print("i is 2")
            #     break # for debugging
            parts = line.strip().split(':')
            mutation_type = parts[0]
            if mutation_type == 'binaryOp':
                inst_count = parts[1]
                op_type = parts[2]
                values = parts[3].strip().split(',')[:-1]
                #print(mutation_type)
                #print(inst_count)
                #print(op_type)
                #print(values)
                for value in values:
                    req_num = req_num + 1
                    mut = file_name + ':' + mutation_type + ':' + inst_count + ':' + op_type + ':' + value + '\n'
                    req.append(mut)
                    #with open(HOME+"/.srciror_fast/mutation_requests.txt", "a+") as mutation_req:
#tmp                    with open(CWD+"/mutation_results/srciror/mutation_requests.txt", "a+") as mutation_req:
   #tmp                     mutation_req.write(file_name + ':' + mutation_type + ':' + inst_count + ':' + op_type + ':' + value + '\n')
            elif mutation_type == 'const':
                inst_count = parts[1]
                op_count = parts[2]
                extra = parts[3]
                values = parts[4].strip().split(',')[:-1]
                for value in values:
                    req_num = req_num + 1
                    mut = file_name + ':' + mutation_type + ':' + inst_count + ':' + op_count + ':' + extra + ':' + value + '\n'
                    req.append(mut)
                    #with open(HOME+"/.srciror_fast/mutation_requests.txt", "a+") as mutation_req:
                    #with open(HOME+"/.srciror_fast/mutation_requests.txt", "a+") as mutation_req:
      #tmp              with open(CWD+"/mutation_results/srciror/mutation_requests.txt", "a+") as mutation_req:
         #tmp               mutation_req.write(file_name + ':' + mutation_type + ':' + inst_count + ':' + op_count + ':' + extra + ':' + value + '\n')
            
    if req_num > 1000:
        req = random.sample(req, 1000)

    with open(CWD+"/mutation_results/srciror/mutation_requests.txt", "a+") as mutation_req:
        mutation_req.writelines(req)


if __name__=="__main__":

    parser = argparse.ArgumentParser(description='Parse the mutations for a test file')
    parser.add_argument('--testName', default="test.c",
                        help='C code name. Default: test.c')
    args = parser.parse_args()

    parseLines(testName = args.testName);
