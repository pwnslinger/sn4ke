import os, sys, subprocess, shutil, time, copy, fnmatch
from collections import defaultdict
import copy

CWD = os.path.dirname(os.path.abspath(__file__))

def executeCommand(args, debug=False):
    """ Executes a command and times it.

        Args:
             args: a list of strings that constitute the bash command.
             debug: boolean flag, if true, prints the output to the commandline

        Returns:
             out:  the output of running the command
             error: the error resulting from the command, if any.
             exec_time: the time spent to execute the command.
    """
    start_time = time.time()
    p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    end_time = time.time()
    out = decode(out)
    error = decode(err)
    if debug == True:
        print (str(args))
        print (out)
        print (error)
    exec_time = str(end_time - start_time)
    return out, error, exec_time


def decode(string):
        return string.decode('utf8', 'ignore')
