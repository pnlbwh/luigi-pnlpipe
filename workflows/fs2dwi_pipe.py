#!/usr/bin/env python

from luigi import Task, Parameter, BoolParameter, IntParameter
from luigi.util import inherits, requires

from dwi_pipe import PnlEddy, PnlEddyEpi, Ukf, TopupEddy
from struct_pipe import Freesurfer, StructMask

from plumbum import local
from subprocess import Popen

from scripts.util import N_PROC



@requires(Freesurfer,TopupEddy)
class Fs2Dwi(Task):

    debug= BoolParameter(default=False)
    mode= Parameter(default='direct')

    def run(self):
        cmd = (' ').join(['fs2dwi.py',
                          '-f', self.input()[0],
                          '--bse', self.input()[1]['bse'],
                          '--dwimask', self.input()[1]['mask'],
                          '-o', self.output(),
                          '-d' if self.debug else '',
                          self.mode])
        p = Popen(cmd, shell=True)
        p.wait()

    def output(self):

        return local.path(self.input()[1]['dwi'].dirname.replace('dwi','fs2dwi'))


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

