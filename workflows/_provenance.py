from _deps_tree import print_tree, print_history_tree
from os.path import join as pjoin, dirname

import json

def _get_provenance(task):
    prov = {}
    prov['name'] = task.task_family
    prov['params'] = task.to_str_params()
    prov['deps'] = [_get_provenance(t) for t in task.deps()]

    return prov

def json_provenance(task, output=None):
    if not output:
        output = task.output()

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
