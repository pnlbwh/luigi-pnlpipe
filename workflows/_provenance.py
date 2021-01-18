from _deps_tree import print_tree, print_history_tree
from os.path import join as pjoin, dirname, isfile
from os import getpid
from subprocess import check_call
from tempfile import gettempdir

import json

def _get_provenance(task):
    prov = {}
    prov['name'] = task.task_family
    prov['params'] = task.to_str_params()
    prov['deps'] = [_get_provenance(t) for t in task.deps()]

    return prov

def _get_env():
    
    # get hashes
    hash_file= pjoin(gettempdir(), f'hashes-{getpid()}.txt')
    if not isfile(hash_file):
        check_call(' '.join(pjoin(dirname(__file__), 'getenv.sh'), hash_file), shell=True)
    
    # read hashes
    with open(hash_file) as f:
        content= f.read().split()
    
    # save hashes in a dictionary for integrating with json provenance
    hash_dict={}
    for line in content:
        key,value=line.split(',')
        hash_dict[key]=value
        
    return hash_dict

def json_provenance(task, output=None):
    if not output:
        output = task.output()
    
    prov= _get_provenance(task)

    prov['env']= _get_env()

    with open(output.dirname.join(output.stem + '.log.json'), 'w') as f:
        json.dump(_get_provenance(task), f)

def write_provenance(obj, output=None):

    if not output:
        output= obj.output()

    tree= print_tree(obj)
    history_tree= print_history_tree(obj)
    json_provenance(obj, output)
      
    with open(pjoin(dirname(__file__), 'provenance.html')) as f:
        template= f.read()
    
    logfile= output.dirname.join(output.stem)+'.log.html'
    with open(logfile,'w') as f:
        template= template.replace('{{output}}',output.basename)
        template= template.replace('{{textHistory}}',tree)
        template= template.replace('{{htmlHistory}}',history_tree)
        f.write(template)
