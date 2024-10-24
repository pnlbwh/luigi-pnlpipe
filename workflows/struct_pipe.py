#!/usr/bin/env python

from luigi import Task, ExternalTask, Parameter, BoolParameter, IntParameter
from luigi.util import inherits, requires
from glob import glob
from os.path import join as pjoin, abspath, isfile, basename, dirname
from os import getenv, remove
import re

from plumbum import local
from subprocess import Popen, check_call
from time import sleep

from scripts.util import N_PROC, FILEDIR, QC_POLL

from _task_util import _mask_name
from _glob import _glob
from _provenance import write_provenance

from warnings import warn

class SelectStructFiles(ExternalTask):
    id = Parameter()
    ses = Parameter(default='')
    bids_data_dir = Parameter()
    struct_template = Parameter(default='')

    def output(self):
        _, struct= _glob(self.bids_data_dir, self.struct_template, self.id, self.ses)
        return local.path(struct)


@requires(SelectStructFiles)
class StructAlign(Task):
    
    derivatives_dir= Parameter()
    
    def run(self):
        self.output().dirname.mkdir()

        cmd = (' ').join(['align.py',
                          '-i', self.input(),
                          '-o', self.output().rsplit('.nii.gz')[0]])
        p = Popen(cmd, shell=True)
        p.wait()

        write_provenance(self)


    def output(self):

        subject_dir= dirname(self.input().replace('rawdata', self.derivatives_dir))
        prefix= self.input().name
        
        if '_T1w' in prefix:
            return local.path(pjoin(subject_dir, prefix.split('_T1w.nii')[0]+ '_desc-Xc_T1w.nii.gz'))
        
        elif '_T2w' in prefix:
            return local.path(pjoin(subject_dir, prefix.split('_T2w.nii')[0]+ '_desc-Xc_T2w.nii.gz'))

        elif '_AXT2' in prefix:
            return local.path(pjoin(subject_dir, prefix.split('_AXT2.nii')[0]+ '_desc-Xc_AXT2.nii.gz'))
       

@requires(StructAlign)
class StructMask(Task):

    # switch between MABS and HD-BET
    mask_method= Parameter(default= 'MABS')

    # for atlas.py
    csvFile= Parameter(default= '')
    debug= BoolParameter(default= False)
    fusion= Parameter(default= '')
    mabs_mask_nproc= IntParameter(default= int(N_PROC))

    # for hd-bet
    hdbet_mode= Parameter(default= '')
    hdbet_device= Parameter(default= '')

    # for makeAlignedMask.py
    ref_img= Parameter(default= '')
    ref_mask= Parameter(default= '')
    reg_method= Parameter(default='rigid')


    def run(self):

        if self.mask_method.lower() in ['mabs','hd-bet']:

            if self.mask_method.lower()=='mabs':
                cmd = (' ').join(['atlas.py',
                                  '-t', self.input(),
                                  '--train', self.csvFile,
                                  '-o', self.output()['mask'].rsplit('_mask.nii.gz')[0],
                                  f'-n {self.mabs_mask_nproc}',
                                  '-d' if self.debug else '',
                                  f'--fusion {self.fusion}' if self.fusion else ''])

            elif self.mask_method.lower()=='hd-bet':
                cmd = (' ').join(['hd-bet',
                                  '-i', self.input(),
                                  '-o', self.output()['mask'].rsplit('_mask.nii.gz')[0],
                                  f'-mode {self.hdbet_mode}' if self.hdbet_mode else '',
                                  f'-device {self.hdbet_device}' if self.hdbet_device else '',
                                  '&& rm', self.output()['mask'].replace('_mask','')])
                                  # the trailing part removes hd-bet's masked image

            else:
                raise ValueError('Supported structural masking methods are MABS and HD-BET only')
                exit(1)

            p = Popen(cmd, shell=True)
            p.wait()

            # print instruction for quality checking
            _mask_name(self.output()['mask'], False)

        else:
            
            cmd = (' ').join(['makeAlignedMask.py',
                              '-t', self.input(),
                              '-o', self.output()['mask'],
                              '-i', glob(pjoin(self.input().dirname, self.ref_img))[0],
                              '-l', glob(pjoin(self.input().dirname, self.ref_mask))[0],
                              '--reg', self.reg_method])

            p = Popen(cmd, shell=True)
            p.wait()


        write_provenance(self, self.output()['mask'])


    def output(self):

        prefix= self.input().name
        
        if self.mask_method.lower() in ['mabs','hd-bet']:
            desc= 'T1wXcMabs' if '_T1w' in prefix else 'T2wXcMabs'
        
        elif self.ref_img:
            ref_mask_pattern= pjoin(self.input().dirname, self.ref_mask)
            try:
                ref_desc= glob(ref_mask_pattern)[0]
            except IndexError:
                print(f'''\n\nERROR
You provided *ref_img* and *ref_mask* values in:
{getenv("LUIGI_CONFIG_PATH")}
But no mask was found with the pattern:
{ref_mask_pattern}
If you are indeed trying to create a mask for {prefix} by warping
previously created mask of {self.ref_img}, make sure *ref_img* and *ref_mask*
contain valid suffix for existing files in:
{self.input().dirname}
Remember--you should have run StructMask task separately beforehand
with the following configuration:
```
[StructMask]
csvFile: /path/to/training/data.csv
ref_img:
ref_mask:
```
Once the mask is created, define *ref_img* and *ref_mask* correctly
and re-attempt your task. If you are trying to create a T1w mask,
*ref_img* and *ref_mask* attributes should correspond to T2w and vice-versa.\n''')

                if 'Qc_mask.nii.gz' in self.ref_mask:
                    print(f'''By the way, did you forget to quality check the previously created mask
or save it after quality checking with {self.ref_mask} suffix?\n\n''')
            
                exit(1)


            desc= re.search('_desc-(.+?)_mask.nii.gz', ref_desc).group(1)
            if '_T1w' in prefix:
                desc+= 'ToT1wXc'
            elif '_T2w' in prefix:
                desc+= 'ToT2wXc'
            elif '_AXT2' in prefix:
                desc+= 'ToAXT2Xc'
        
        
        mask_prefix= local.path(pjoin(self.input().dirname, prefix.split('_desc-')[0])+ '_desc-'+ desc)
        mask = local.path(mask_prefix+ '_mask.nii.gz')
        
        return dict(aligned= self.input(), mask=mask)


@requires(StructMask)
class N4BiasCorrect(Task):
    
    mask_qc= BoolParameter(default=True)
    
    def run(self):
        
        # ensure existence of quality checked MABS mask
        # aligned mask won't be quality checked
        if self.mask_method.lower() in ['mabs','hd-bet']:
            qc_mask= _mask_name(self.input()['mask'], self.mask_qc)
        else:
            qc_mask= self.input()['mask']
        
        cmd = (' ').join(['ImageMath', '3', self.output()['masked'], 'm', self.input()['aligned'], qc_mask])
        check_call(cmd, shell=True)
        
        cmd = (' ').join(['N4BiasFieldCorrection', '-d', '3', '-i', self.output()['masked'], '-o', self.output()['n4corr']])
        check_call(cmd, shell=True)
        
        write_provenance(self, self.output()['n4corr'])


    def output(self):
        prefix= self.input()['aligned'].basename
        
        if '_T1w' in prefix:
            outPrefix= pjoin(self.input()['aligned'].dirname, prefix.split('_T1w.nii')[0])
            return dict(masked= local.path(outPrefix+ 'Ma_T1w.nii.gz'), n4corr= local.path(outPrefix+ 'MaN4_T1w.nii.gz'))
        
        elif '_T2w' in prefix:
            outPrefix= pjoin(self.input()['aligned'].dirname, prefix.split('_T2w.nii')[0])
            return dict(masked= local.path(outPrefix+ 'Ma_T2w.nii.gz'), n4corr= local.path(outPrefix+ 'MaN4_T2w.nii.gz'))



@inherits(N4BiasCorrect)
class Freesurfer(Task):

    t1_template= Parameter()
    t1_mask_method= Parameter(default='')
    t1_csvFile = Parameter(default='')
    t1_ref_img= Parameter(default='')
    t1_ref_mask= Parameter(default='')

    t2_template= Parameter(default='')
    t2_mask_method= Parameter(default='')
    t2_csvFile = Parameter(default='')
    t2_ref_img= Parameter(default='')
    t2_ref_mask= Parameter(default='')

    freesurfer_nproc= IntParameter(default=1)
    expert_file= Parameter(default=pjoin(FILEDIR,'expert_file.txt'))
    no_hires= BoolParameter(default=False)
    no_skullstrip= BoolParameter(default=False)
    no_rand= BoolParameter(default=False)
    subfields= BoolParameter(default=False)
    
    # fsWithT2= BoolParameter(default=False)
    
    fs_dirname= Parameter(default='freesurfer')

    def requires(self):
    
        self.struct_template= self.t1_template
        self.mask_method= self.t1_mask_method
        self.csvFile= self.t1_csvFile
        self.ref_img= self.t1_ref_img
        self.ref_mask= self.t1_ref_mask

        t1_attr= self.clone(N4BiasCorrect)

        if self.t2_template:
            self.struct_template = self.t2_template
            self.mask_method= self.t2_mask_method
            self.csvFile = self.t2_csvFile
            self.ref_img = self.t2_ref_img
            self.ref_mask = self.t2_ref_mask
            
            t2_attr= self.clone(N4BiasCorrect)

            return (t1_attr,t2_attr)

        else:
            return (t1_attr,)



    def run(self):
        cmd = (' ').join(['fs.py',
                          '-i', self.input()[0]['n4corr'],
                          '-o', self.output(),
                          f'-n {self.freesurfer_nproc}',
                          f'--expert {self.expert_file}' if self.expert_file else '',
                          '--nohires' if self.no_hires else '',
                          '--noskullstrip',
                          '--norandomness' if self.no_rand else '',
                          '--subfields' if self.subfields else '',
                          '--t2 {}'.format(self.input()[1]['n4corr']) if self.t2_template else ''])

        
        # DONOT remove the trailing comment, used for pipeline_test.sh: --hack-fs
        p = Popen(cmd, shell=True) # fs-exec
        p.wait()
        
        check_call(f'recon-all --version > {self.output()}/version.txt', shell=True)

        write_provenance(self)
        

    def output(self):
        return local.path(pjoin(self.input()[0]['n4corr'].dirname, self.fs_dirname))


