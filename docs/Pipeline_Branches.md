---

There are many tasks in our Luigi pipeline defined in [different modules](../workflows):

* struct_pipe.py
* dwi_pipe.py
* fs2dwi_pipe.py

Some of them can be run standalone. Others require a task to be run beforehand. Such various routes are outlined below:

#### T1 + T2 templates

    StructMask, Freesurfer
    
#### dwi + T2 templates

    EddyEpi, Ukf, Wma800
    
Provided that Freesurfer pipeline was run:

    EddyEpi, Ukf, Fs2Dwi, Wmql, Wmqlqc, TractMeasures
            

#### Only T1 template

    StructMask, Freesurfer
    
#### dwi+T1 template

    SynB0, Ukf, Wma800

#### ap_pa_template

    TopupEddy, Ukf, Wma800
    
#### Only dwi template

    DwiAlign, GibbsUn, CnnMask, PnlEddy, FslEddy, Ukf, Wma800
    
Provided that Freesurfer task was run:

    DwiAlign, GibbsUn, CnnMask, PnlEddy, FslEddy, Ukf, Fs2Dwi, Wmql, Wmqlqc, TractMeasures

Provided that GibbsUn was run:

    HcpPipe, Ukf, Wma800

        
