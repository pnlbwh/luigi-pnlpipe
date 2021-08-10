from plumbum import local

def _mask_name(mask_name, mask_qc=True):

    qc_mask= local.path(mask_name.replace('_mask.nii.gz', 'Qc_mask.nii.gz'))
    
    if mask_qc:
        if not qc_mask.exists():
            raise FileNotFoundError('\n\nQuality checked mask not found\n'
                  'Check the quality of created mask {}\n'
                  'Once you are done, save the (edited) mask as {}\n\n'
                  .format(mask_name, qc_mask))
        else:
            return qc_mask
    
    else:
        return mask_name