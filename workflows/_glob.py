from glob import glob
from os.path import abspath, join as pjoin

def _glob(bids_data_dir, template, id, ses):

    # making the user specify sub-* and ses-*
    # the middle dash (-) should make the substitution stricter and safer
    if 'sub-*/' not in template:
        raise ValueError('Template should contain sub-*/ and if needed ses-*/ strings')

    if ses:
        template= template.replace('ses-*', f'ses-{ses}')
    template= template.replace('sub-*', f'sub-{id}')
    template= pjoin(abspath(bids_data_dir), template)


    filename= glob(template)
    if len(filename)>1:
        raise AttributeError(f'Multiple files exist with the template {template}\n'
            'Please provide a unique representative template')

    elif not filename:
        raise FileNotFoundError(f'No file found using the template {template}\n'
            'Correct the bids-data-dir and/or template and try again\n')

    else:
        return (template, filename[0])


if __name__=='__main__':
    bids_data_dir= '/data/pnl/DIAGNOSE_CTE_U01/rawdata/'
    
    id= '1001'
    ses= '01'

    print('\n# Success cases #\n')
    template= 'sub-*/ses-*/dwi/*_dwi.nii.gz'
    print(_glob(bids_data_dir, template, id, ses))
    
    ses=None
    template= 'sub-*/ses-*/dwi/*_dwi.nii.gz'
    print(_glob(bids_data_dir, template, id, ses))

    print('\n# Fail cases #\n')
    template= 'sub-/ses-01/dwi/*_dwi.nii.gz'
    try:
        _glob(bids_data_dir, template, id, ses)
    except ValueError as e:
        print(e)

    template= 'sub-*/ses-01/dwi/hello*_dwi.nii.gz'
    _glob(bids_data_dir, template, id, ses)


