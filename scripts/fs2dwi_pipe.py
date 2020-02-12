#!/usr/bin/env python

from luigi import Task, Parameter, BoolParameter, IntParameter
from luigi.util import inherits, requires

from dwi_pipe import PnlEddy, PnlEddyEpi, Ukf
from struct_pipe_t1_t2 import Freesurfer, StructMask

from subprocess import Popen

from util import N_PROC


@inherits(Freesurfer,PnlEddy,PnlEddyEpi,StructMask)
class Fs2Dwi(Task):

    fs_in_dwi= Parameter()
    debug= BoolParameter(default=False)
    mode= Parameter(default='direct')
    
    def requires(self):
        if self.mode=='direct':
            return dict(fs_dir= self.clone(Freesurfer), corrected= self.clone(PnlEddy))
            
        elif self.mode=='witht2':
            fs_dir= self.clone(Freesurfer)

            self.struct_template = self.t2_template
            self.struct_align_prefix = self.t2_align_prefix
            self.mabs_mask_prefix = self.t2_mask_prefix
            self.csvFile = self.t2_csvFile
            self.model_img = self.t2_model_img
            self.model_mask = self.t2_model_mask

            corrected= self.clone(PnlEddyEpi)
            t2_attr= self.clone(StructMask)

            return dict(fs_dir= fs_dir, corrected= corrected, t2_attr= t2_attr)
   
            
    def run(self):
        cmd = (' ').join(['fs2dwi.py',
                          '-f', self.input()['fs_dir'],
                          '--bse', self.input()['corrected']['bse'],
                          '--dwimask', self.input()['corrected']['mask'],
                          '-o', self.fs_in_dwi.dirname,
                          '-d' if self.debug else '',
                          self.mode,
                          '--t2 {} --t2mask {}'.format(self.input()['t2_attr']['aligned'],self.input()['t2_attr']['mask'])
                                                if self.mode=='witht2' else ''])
        p = Popen(cmd, shell=True)
        p.wait()

    def output(self):
        return self.fs_in_dwi



@inherits(Fs2Dwi,Ukf)
class Wmql(Task):

    wmql_out= Parameter()
    query= Parameter(default='')
    wmql_nproc= IntParameter(default= int(N_PROC))

    def requires(self):

        fs_in_dwi= self.clone(Fs2Dwi)

        if self.t2_template:
            self.struct_template = self.t2_template
            self.struct_align_prefix = self.t2_align_prefix
            self.mabs_mask_prefix = self.t2_mask_prefix
            self.csvFile = self.t2_csvFile
            self.model_img = self.t2_model_img
            self.model_mask = self.t2_model_mask

        tract= self.clone(Ukf)

        return (fs_in_dwi,tract)

    def run(self):
        cmd = (' ').join(['wmql.py',
                          '-f', self.input()[0],
                          '-i', self.input()[1],
                          '-o', self.wmql_out,
                          f'-q {self.query}' if self.query else '',
                          f'-n {self.wmql_nproc}' if self.wmql_nproc else ''])
        p = Popen(cmd, shell=True)
        p.wait()


    def output(self):
        return self.wmql_out


@requires(Wmql)
class Wmqlqc(Task):
    id= Parameter()
    wmqlqc_out= Parameter()

    def run(self):
        cmd = (' ').join(['wmqlqc.py',
                          '-i', self.input(),
                          '-s', self.id,
                          '-o', self.wmqlqc_out])
        p = Popen(cmd, shell=True)
        p.wait()

    def output(self):
        return self.wmqlqc_out

