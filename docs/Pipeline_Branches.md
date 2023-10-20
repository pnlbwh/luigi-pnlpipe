Luigi pipeline routes:

T1+T2 templates:
    StructMask, Freesurfer
    
dwi+T2 templates:
    EddyEpi, Ukf, Wma800
    
Provided that Freesurfer pipeline was run:
    dwi+T2 templates:
        EddyEpi, Ukf, Fs2Dwi, Wmql, Wmqlqc, TractMeasures
            

Only T1 template
    StructMask, Freesurfer
    
dwi+T1 template
    SynB0, Ukf, Wma800

ap_pa_template
    TopupEddy, Ukf, Wma800
    
Only dwi template:
    DwiAlign, GibbsUn, CnnMask, PnlEddy, FslEddy, Ukf, Wma800
    
    
Upto GibbsUn run via Luigi, HcpPipe run outside Luigi:
    Only dwi template:
        HcpPipe, Ukf, Wma800
        
        
Provided that Freesurfer task was run before:
    Only dwi template:
        DwiAlign, GibbUn, CnnMask, PnlEddy, FslEddy, Ukf, Fs2Dwi, Wmql, Wmqlqc, TractMeasures
