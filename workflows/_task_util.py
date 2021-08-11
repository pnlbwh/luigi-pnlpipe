from plumbum import local

def _mask_name(mask_name, mask_qc=True):

    qc_mask= local.path(mask_name.replace('_mask.nii.gz', 'Qc_mask.nii.gz'))
    
    msg= """\n
Quality checked mask not found
Check the quality of created mask {}
Once you are done, save the (edited) mask as {}
\n""".format(mask_name, qc_mask)
    
    if mask_qc:
        if not qc_mask.exists():
            raise FileNotFoundError(msg)
        else:
            return qc_mask
    
    else:
        print(msg)
        return mask_name