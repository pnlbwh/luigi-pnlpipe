#!/usr/bin/env python

from luigi import Task, ExternalTask, Parameter, BoolParameter, IntParameter
from luigi.util import inherits, requires
from glob import glob
from os.path import join as pjoin, abspath, isfile, basename, dirname
import re

from plumbum import local
from subprocess import Popen, check_call
from time import sleep

from scripts.util import N_PROC, FILEDIR, QC_POLL, _mask_name

class SelectStructFiles(ExternalTask):
    id = Parameter()
    bids_data_dir = Parameter()
    struct_template = Parameter(default='')

    def output(self):
        struct = glob(pjoin(abspath(self.bids_data_dir), self.struct_template.replace('$', self.id)))[0]

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

    def output(self):

        subject_dir= dirname(self.input().replace('rawdata', self.derivatives_dir))
        prefix= self.input().basename
        
        if '_T1w' in prefix:
            return local.path(pjoin(subject_dir, prefix.split('_T1w.nii')[0]+ '_desc-Xc_T1w.nii.gz'))
        
        elif '_T2w' in prefix:
            return local.path(pjoin(subject_dir, prefix.split('_T2w.nii')[0]+ '_desc-Xc_T2w.nii.gz'))

        elif '_AXT2' in prefix:
            return local.path(pjoin(subject_dir, prefix.split('_AXT2.nii')[0]+ '_desc-Xc_AXT2.nii.gz'))
       

@requires(StructAlign)
class StructMask(Task):

    # for atlas.py
    csvFile= Parameter(default= '')
    debug= BoolParameter(default= False)
    fusion= Parameter(default= '')
    mabs_mask_nproc= IntParameter(default= int(N_PROC))

    # for makeAlignedMask.py
    ref_img= Parameter(default= '')
    ref_mask= Parameter(default= '')
    reg_method= Parameter(default='rigid')

    # for qc'ing the created mask
    slicer_exec= Parameter(default= '')
    mask_qc= BoolParameter(default=False)


    def run(self):

        auto_mask = self.output()['mask'].replace('Qc','')

        if not isfile(auto_mask):
            if self.csvFile:
                cmd = (' ').join(['atlas.py',
                                  '-t', self.input(),
                                  '--train', self.csvFile,
                                  '-o', self.output()['mask'].rsplit('_mask.nii.gz')[0],
                                  f'-n {self.mabs_mask_nproc}',
                                  '-d' if self.debug else '',
                                  f'--fusion {self.fusion}' if self.fusion else ''])

                p = Popen(cmd, shell=True)
                p.wait()

            else:
                
                cmd = (' ').join(['makeAlignedMask.py',
                                  '-t', self.input(),
                                  '-o', self.output()['mask'],
                                  '-i', glob(pjoin(self.input().dirname, self.ref_img))[0],
                                  '-l', glob(pjoin(self.input().dirname, self.ref_mask))[0],
                                  '--reg', self.reg_method])

                p = Popen(cmd, shell=True)
                p.wait()

            if p.returncode:
                return


        if self.slicer_exec or self.mask_qc:
            print('\n\n** Check quality of created mask {} . Once you are done, save the (edited) mask as {} **\n\n'
                  .format(auto_mask,self.output()['mask']))


        if self.slicer_exec:
            cmd= (' ').join([self.slicer_exec, '--python-code',
                            '\"slicer.util.loadVolume(\'{}\'); '
                            'slicer.util.loadLabelVolume(\'{}\')\"'
                            .format(self.input()['aligned'],auto_mask)])

            p = Popen(cmd, shell= True)
            p.wait()


        elif self.mask_qc:
            while 1:
                sleep(QC_POLL)
                if isfile(self.output()['mask']):
                    break



    def output(self):

        prefix= self.input().basename
        
        if self.csvFile:
            desc= 'T1wXcMabs' if '_T1w' in prefix else 'T2wXcMabs'
        
        elif self.ref_img:
            ref_desc= glob(pjoin(self.input().dirname, self.ref_mask))[0]
            desc= re.search('_desc-(.+?)_mask.nii.gz', ref_desc).group(1)
            if '_T1w' in prefix:
                desc+= 'ToT1wXc'
            elif '_T2w' in prefix:
                desc+= 'ToT2wXc'
            elif '_AXT2' in prefix:
                desc+= 'ToAXT2Xc'
        
        
        mask_prefix= local.path(pjoin(self.input().dirname, prefix.split('_desc-')[0])+ '_desc-'+ desc)
        mask = _mask_name(mask_prefix, self.slicer_exec, self.mask_qc)
        
        return dict(aligned= self.input(), mask=mask)


@requires(StructMask)
class N4BiasCorrect(Task):

    def run(self):
        cmd = (' ').join(['ImageMath', '3', self.output()['masked'], 'm', self.input()['aligned'], self.input()['mask']])
        check_call(cmd, shell=True)
        
        cmd = (' ').join(['N4BiasFieldCorrection', '-d', '3', '-i', self.output()['masked'], '-o', self.output()['n4corr']])
        check_call(cmd, shell=True)
       

    def output(self):
        prefix= self.input()['aligned'].basename
        
        if '_T1w' in prefix:
            outPrefix= pjoin(self.input()['aligned'].dirname, prefix.split('_T1w.nii')[0])
            return dict(masked= local.path(outPrefix+ 'Ma_T1w.nii.gz'), n4corr= local.path(outPrefix+ 'MaN4_T1w.nii.gz'))
        
        elif '_T2w' in prefix:
            outPrefix= pjoin(self.input()['aligned'].dirname, prefix.split('_T2w.nii')[0])
            return dict(masked= local.path(outPrefix+ 'Ma_T2w.nii.gz'), n4corr= local.path(outPrefix+ 'MaN4_T2w.nii.gz'))


@inherits(StructMask)
class FreesurferUnCorrect(Task):

    t1_template= Parameter()
    t1_csvFile = Parameter(default='')
    t1_ref_img= Parameter(default='')
    t1_ref_mask= Parameter(default='')
    t1_mask_qc= BoolParameter(default=False)

    t2_template= Parameter(default='')
    t2_csvFile = Parameter(default='')
    t2_ref_img= Parameter(default='')
    t2_ref_mask= Parameter(default='')
    t2_mask_qc= BoolParameter(default=False)

    freesurfer_nproc= IntParameter(default=1)
    expert_file= Parameter(default=pjoin(FILEDIR,'expert_file.txt'))
    no_hires= BoolParameter(default=False)
    no_skullstrip= BoolParameter(default=False)
    subfields= BoolParameter(default=False)
    
    # fsWithT2= BoolParameter(default=False)
    
    fs_dirname= Parameter(default='freesurfer')

    def requires(self):
    
        self.struct_template= self.t1_template
        self.csvFile= self.t1_csvFile
        self.ref_img= self.t1_ref_img
        self.ref_mask= self.t1_ref_mask
        self.mask_qc= self.t1_mask_qc

        t1_attr= self.clone(StructMask)

        if self.t2_template:
            self.struct_template = self.t2_template
            self.csvFile = self.t2_csvFile
            self.ref_img = self.t2_ref_img
            self.ref_mask = self.t2_ref_mask
            self.mask_qc = self.t2_mask_qc
            
            t2_attr= self.clone(StructMask)

            return (t1_attr,t2_attr)

        else:
            return (t1_attr,)


    def run(self):
        cmd = (' ').join(['fs.py',
                          '-i', self.input()[0]['aligned'],
                          '-m', self.input()[0]['mask'],
                          '-o', self.output(),
                          f'-n {self.freesurfer_nproc}',
                          f'--expert {self.expert_file}' if self.expert_file else '',
                          '--nohires' if self.no_hires else '',
                          '--noskullstrip' if self.no_skullstrip else '',
                          '--subfields' if self.subfields else '',
                          '--t2 {} --t2mask {}'.format(self.input()[1]['aligned'],self.input()[1]['mask'])
                                                if self.t2_template else ''])

        p = Popen(cmd, shell=True)
        p.wait()

        check_call(f'recon-all --version > {self.output()}/version.txt', shell=True)


    def output(self):
        return local.path(pjoin(self.input()[0]['aligned'].dirname, self.fs_dirname))
        
@inherits(N4BiasCorrect)
class Freesurfer(Task):

    t1_template= Parameter()
    t1_csvFile = Parameter(default='')
    t1_ref_img= Parameter(default='')
    t1_ref_mask= Parameter(default='')
    t1_mask_qc= BoolParameter(default=False)

    t2_template= Parameter(default='')
    t2_csvFile = Parameter(default='')
    t2_ref_img= Parameter(default='')
    t2_ref_mask= Parameter(default='')
    t2_mask_qc= BoolParameter(default=False)

    freesurfer_nproc= IntParameter(default=1)
    expert_file= Parameter(default=pjoin(FILEDIR,'expert_file.txt'))
    no_hires= BoolParameter(default=False)
    no_skullstrip= BoolParameter(default=False)
    subfields= BoolParameter(default=False)
    
    # fsWithT2= BoolParameter(default=False)
    
    fs_dirname= Parameter(default='freesurfer')

    def requires(self):
    
        self.struct_template= self.t1_template
        self.csvFile= self.t1_csvFile
        self.ref_img= self.t1_ref_img
        self.ref_mask= self.t1_ref_mask
        self.mask_qc= self.t1_mask_qc

        t1_attr= self.clone(N4BiasCorrect)

        if self.t2_template:
            self.struct_template = self.t2_template
            self.csvFile = self.t2_csvFile
            self.ref_img = self.t2_ref_img
            self.ref_mask = self.t2_ref_mask
            self.mask_qc = self.t2_mask_qc
            
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
                          '--subfields' if self.subfields else '',
                          '--t2 {}'.format(self.input()[1]['n4corr']) if self.t2_template else ''])

        p = Popen(cmd, shell=True)
        p.wait()
        
        check_call(f'recon-all --version > {self.output()}/version.txt', shell=True)
        

    def output(self):
        return local.path(pjoin(self.input()[0]['n4corr'].dirname, self.fs_dirname))

