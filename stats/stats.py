from os.path import basename

import glob
import re
import ipdb

results = {}


def post_process():
    for bench_name, bench_value in results.items():
        for set_name, set_value in bench_value.items():
            for type_name, type_value in set_value.items():
                total = sum(results[bench_name][set_name][type_name].values())
                for k,v in type_value.items():
                    type_value[k] = round((v/total)*100, 2)

def iterate(path='.'):
    for rname in glob.glob(path+'/*/*/*'):
        if not rname.endswith('.txt'):
            continue
        try:
            set_type, _, bench, bench_set = basename(rname).split('_')
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

            bset_key = bench_set.split('.')[0]
            if bset_key not in results[bench].keys():
                results[bench][bset_key] = dict()

            if set_type not in results[bench][bset_key].keys():
                results[bench][bset_key][set_type] = dict()

            if mutantOpt not in results[bench][bset_key][set_type].keys():
                results[bench][bset_key][set_type][mutantOpt] = 1
            else:
                # any jump like instructions
                if orig[0] == 'j' and mutantOpt == 'nopOp':
                    try:
                        results[bench][bset_key][set_type]['brOp'] += 1
                    except KeyError:
                        results[bench][bset_key][set_type]['brOp'] = 1
                else:
                    results[bench][bset_key][set_type][mutantOpt] += 1


if __name__ == '__main__':
    iterate('./results')
    post_process()
    ipdb.set_trace()
