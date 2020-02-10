#!/usr/bin/env python

from luigi import Task, build, ExternalTask, Parameter, BoolParameter, IntParameter
from luigi.util import inherits, requires
from glob import glob
from os.path import join as pjoin, abspath, isdir

from plumbum import local
from shutil import rmtree

from _define_outputs import IO
from util import N_PROC, FILEDIR

from subprocess import Popen
import argparse
from conversion import read_cases

class SelectStructFiles(ExternalTask):
    id = Parameter()
    bids_data_dir = Parameter()
    struct_template = Parameter()

    def output(self):
        struct = glob(pjoin(abspath(self.bids_data_dir), self.struct_template.replace('id', self.id)))[0]

        return local.path(struct)


@requires(SelectStructFiles)
class StructAlign(Task):
    struct_align_prefix = Parameter()

    def run(self):
        self.struct_align_prefix.dirname.mkdir()

        cmd = (' ').join(['align.py',
                          '-i', self.input(),
                          '-o', self.struct_align_prefix])
        p = Popen(cmd, shell=True)
        p.wait()

    def output(self):
        return self.struct_align_prefix.with_suffix('.nii.gz')



@requires(StructAlign)
class StructMask(Task):

    mabs_mask_prefix= Parameter()

    # for atlas.py
    csvFile= Parameter(default= '')
    debug= BoolParameter(default= False)
    fusion= Parameter(default= '')
    mabs_mask_nproc= IntParameter(default= int(N_PROC))

    # for makeRigidMask.py
    model_img= Parameter(default= '')
    model_mask= Parameter(default= '')

    # for qc'ing the created mask
    slicer_exec= Parameter(default= '')


    def run(self):

        if not (self.model_img and self.model_mask):
            cmd = (' ').join(['atlas.py',
                              '-t', self.input(),
                              '--train', self.csvFile,
                              '-o', self.mabs_mask_prefix,
                              f'-n {self.mabs_mask_nproc}',
                              '-d' if self.debug else '',
                              f'--fusion {self.fusion}' if self.fusion else ''])

            p = Popen(cmd, shell=True)
            p.wait()

        else:
            cmd = (' ').join(['makeSynMask.py',
                              '-t', self.input(),
                              '-o', self.output()['mask'],
                              '-i', self.model_img,
                              '-l', self.model_mask])

            p = Popen(cmd, shell=True)
            p.wait()

        if self.slicer_exec:
            cmd= (' ').join([self.slicer_exec, '--python-code',
                            '\"slicer.util.loadVolume(\'{}\'); '
                            'slicer.util.loadLabelVolume(\'{}\')\"'
                            .format(self.input()['aligned'],self.output()['mabs_mask'])])

            p = Popen(cmd, shell= True)
            p.wait()


    def output(self):
        return dict(aligned= self.input(), mask=local.path(self.mabs_mask_prefix._path + '_mask.nii.gz'))



@inherits(StructMask)
class Freesurfer(Task):

    t1_template= Parameter(default='sub-id/anat/*_T1w.nii.gz')
    t1_align_prefix= Parameter()
    t1_mask_prefix= Parameter()
    t1_csvFile = Parameter(default='--t1')
    t1_model_img= Parameter(default='')
    t1_model_mask= Parameter(default='')

    t2_template= Parameter(default='sub-id/anat/*_T2w.nii.gz')
    t2_align_prefix= Parameter(default='')
    t2_mask_prefix= Parameter(default='')
    t2_csvFile = Parameter(default='--t2')
    t2_model_img= Parameter(default='')
    t2_model_mask= Parameter(default='')

    freesurfer_nproc= IntParameter(default=1)
    expert_file= Parameter(default=pjoin(FILEDIR,'expert_file.txt'))
    no_hires= BoolParameter(default=False)
    no_skullstrip= BoolParameter(default=False)
    fs_dir= Parameter()

    def requires(self):
        self.struct_template= self.t1_template
        self.struct_align_prefix= self.t1_align_prefix
        self.mabs_mask_prefix= self.t1_mask_prefix
        self.csvFile= self.t1_csvFile
        self.model_img= self.t1_model_img
        self.model_mask= self.t1_model_mask

        t1_attr= self.clone(StructMask)

        if self.t2_template:
            self.struct_template = self.t2_template
            self.struct_align_prefix = self.t2_align_prefix
            self.mabs_mask_prefix = self.t2_mask_prefix
            self.csvFile = self.t2_csvFile
            self.model_img = self.t2_model_img
            self.model_mask = self.t2_model_mask

            t2_attr= self.clone(StructMask)

            return (t1_attr,t2_attr)

        else:
            return (t1_attr)


    def run(self):
        cmd = (' ').join(['fs.py',
                          '-i', self.input()[0]['aligned'],
                          '-m', self.input()[0]['mask'],
                          '-o', self.fs_dir,
                          f'-n {self.freesurfer_nproc}',
                          f'--expert {self.expert_file}' if self.expert_file else '',
                          '--nohires' if self.no_hires else '',
                          '--noskullstrip' if self.no_skullstrip else '',
                          '--t2 {} --t2mask {}'.format(self.input()[1]['aligned'],self.input()[1]['mask'])
                                                if self.t2_template else ''])

        p = Popen(cmd, shell=True)
        p.wait()

    def output(self):
        return self.fs_dir

