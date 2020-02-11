#!/usr/bin/env python

import argparse
from conversion import read_cases
from luigi import build
from _define_outputs import IO
from dwi_pipe import Ukf
from os.path import abspath, isfile

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='''pnlpipe glued together using Luigi, 
                                    optional parameters can be set by environment variable LUIGI_CONFIG_PATH, 
                                    see luigi-pnlpipe/scripts/struct_pipe_params.cfg as example''',
                                     formatter_class= argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('--bids-data-dir', required= True, type=str, default= argparse.SUPPRESS,
                        help='/path/to/bids/data/directory')
    parser.add_argument('-c', required= True, type=str, default= argparse.SUPPRESS,
                        help='a single caseid or a .txt file where each line is a caseid')
    parser.add_argument('--dwi-template', type=str, default='sub-id/dwi/*_dwi.nii.gz',
                        help='glob bids-data-dir/t1-template to find input data')
    parser.add_argument('--t2-template', type=str,
                        help='glob bids-data-dir/t2-template to find input data')
    parser.add_argument('--num-workers', type=int, default=1, help='number of Luigi workers')

    # parser.add_argument('--bids-derivatives', type= str, default='luigi-pnlpipe', help= 'name of bids derivatives directory')

    args = parser.parse_args()
    
    cases = read_cases(abspath(args.c)) if isfile(abspath(args.c)) else [args.c]
    args.bids_data_dir= abspath(args.bids_data_dir)

    UkfTasks = []
    for id in cases:
        inter = IO(id, args.bids_data_dir)
        
        UkfTasks.append(Ukf(bids_data_dir = args.bids_data_dir,
                            id=id,
                            dwi_template = args.dwi_template,
                            dwi_align_prefix=inter['dwi_align_prefix'],
                            eddy_prefix=inter['eddy_prefix'],
                            eddy_epi_prefix=inter['eddy_epi_prefix'],
                            eddy_bse_masked_prefix=inter['eddy_bse_masked_prefix'],
                            eddy_bse_betmask_prefix=inter['eddy_bse_betmask_prefix'],
                            eddy_epi_bse_masked_prefix=inter['eddy_epi_bse_masked_prefix'],
                            eddy_epi_bse_betmask_prefix=inter['eddy_epi_bse_betmask_prefix'],
                            struct_template= args.t2_template,
                            struct_align_prefix=inter['t2_align_prefix'],
                            mabs_mask_prefix=inter['t2_mabsmask_prefix'],
                            tract_prefix= inter['eddy_epi_tract_prefix']))

    
    build(UkfTasks, workers=args.num_workers)

