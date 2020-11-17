from _deps_tree import print_tree, print_history_tree
from os.path import join as pjoin, dirname

def write_provenance(obj, output=None):

    if not output:
        output= obj.output()

    tree= print_tree(obj)
    history_tree= print_history_tree(obj)
      
    with open(pjoin(dirname(__file__), 'provenance.html')) as f:
        template= f.read()
    
    logfile= output.dirname.join(output.stem)+'.log.html'
    with open(logfile,'w') as f:
        template= template.replace('{{output}}',output.basename)
        template= template.replace('{{textHistory}}',tree)
        template= template.replace('{{htmlHistory}}',history_tree)
        f.write(template)



