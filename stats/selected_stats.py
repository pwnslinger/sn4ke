from os.path import basename

import glob
import re
import ipdb

results = {}


def post_process():
    for bench_name, set_value in results.items():
        total = sum(results[bench_name].values())
        for k,v in set_value.items():
            set_value[k] = round((v/total)*100, 2)

def iterate(path='.'):
    for rname in glob.glob(path+'/*'):
        if not rname.endswith('.txt'):
            continue
        try:
            bench, _, _ = basename(rname).split('_')
        except ValueError:
            continue
        with open(rname) as f:
            mutant_lst = f.readlines()
        for mutant in mutant_lst:
            try:
                function_name = basename(mutant).split(':')[1]
                mutantOpt = basename(mutant).split(':')[2]

                orig = basename(mutant).split(':')[4]
                #TODO: noOp of jumps should be under brOp
            except IndexError:
                result = re.findall(r'nn\_(.*)\_(.*Op)\_\d+\_(\w+)\_', basename(mutant))[0]
                function_name = result[0]
                mutantOpt = result[1]
                orig = result[2]
            if bench not in results.keys():
                results[bench] = dict()

            if mutantOpt not in results[bench].keys():
                results[bench][mutantOpt] = 1
            else:
                # any jump like instructions
                if orig[0] == 'j' and mutantOpt == 'nopOp':
                    try:
                        results[bench]['brOp'] += 1
                    except KeyError:
                        results[bench]['brOp'] = 1
                else:
                    results[bench][mutantOpt] += 1


if __name__ == '__main__':
    iterate('./selected_results/')
    post_process()
    ipdb.set_trace()
