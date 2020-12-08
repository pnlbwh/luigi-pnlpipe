#!/usr/bin/env python

from luigi import Task, ExternalTask, Parameter, BoolParameter, IntParameter
from luigi.util import inherits, requires

from dwi_pipe import PnlEddy, FslEddy, EddyEpi, TopupEddy, PnlEddyUkf, Ukf
from struct_pipe import Freesurfer, StructMask

from plumbum import local
from subprocess import Popen

from scripts.util import N_PROC

from os.path import dirname, join as pjoin
from _glob import _glob
from glob import glob

class SelectFsDwiFiles(ExternalTask):
    id = Parameter()
    ses = Parameter(default='')
    bids_data_dir = Parameter()
    derivatives_dir = Parameter()
    fs_template = Parameter()
    dwi_template = Parameter()

    def output(self):

        derivatives_dir= self.bids_data_dir.replace('rawdata', self.derivatives_dir)
        fsdir = _glob(derivatives_dir, self.fs_template, self.id, self.ses)

        # select the latest dwi
        dwis = _glob(derivatives_dir, self.dwi_template, self.id, self.ses, multiple=True)
        dwis.reverse()
        found=False
        for suffix in ['XcUnEdEp_dwi', 'XcUnEd_dwi', 'XcUn_dwi', 'Xc_dwi']:

            for dwi in dwis:
                if suffix in dwi:
                    found=True
                    break

            if found:
                break


        bse_mask_dict= {
            'XcUnEdEp_dwi': ['XcUnCNNQcEdEp_mask', 'XcUnCNNEdEp_mask', 'XcUnEdEp_bse'],
            'XcUnEd_dwi': ['XcUnCNNQc_mask', 'XcUnCNN_mask', 'XcUn_bse'],
            'XcUn_dwi': ['XcUnCNNQc_mask', 'XcUnCNN_mask', 'XcUn_bse'],
            'Xc_dwi': ['XcCNNQc_mask', 'XcCNN_mask', 'Xc_bse']
        }


        try:
            mask= glob(pjoin(dirname(dwi), '*' + bse_mask_dict[suffix][0] + '.nii.gz'))[0]
        except IndexError:
            mask= glob(pjoin(dirname(dwi), '*' + bse_mask_dict[suffix][1] + '.nii.gz'))[0]

        bse= glob(pjoin(dirname(dwi), '*'+ bse_mask_dict[suffix][2]+'.nii.gz'))[0]

        print('')
        print(bse)
        print(mask)
        print('')

        return dict(fsdir=local.path(fsdir), bse=local.path(bse), mask=local.path(mask))


@requires(SelectFsDwiFiles,StructMask)
class Fs2Dwi(Task):

    debug= BoolParameter(default=False)
    mode= Parameter(default='direct')

    def run(self):
        cmd = (' ').join(['fs2dwi.py',
                          '-f', self.input()[0]['fsdir'],
                          '--bse', self.input()[0]['bse'],
                          '--dwimask', self.input()[0]['mask'],
                          '-o', self.output(),
                          '-d' if self.debug else '',
                          'direct' if self.mode=='direct'
                          else 'witht2 --t2 {} --t2mask {}'.format(self.input()[1]['aligned'], self.input()[1]['mask'])])
        p = Popen(cmd, shell=True)
        p.wait()

    def output(self):

        return local.path(self.input()[1]['bse'].dirname.replace('dwi','fs2dwi'))


@requires(Fs2Dwi,Ukf)
class Wmql(Task):

    # wmql_out= Parameter()
    query= Parameter(default='')
    wmql_nproc= IntParameter(default= int(N_PROC))

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

        return local.path(self.input()[0].replace('fs2dwi','wmql'))


@requires(Wmql)
class Wmqlqc(Task):

    # wmqlqc_out= Parameter()

    def run(self):
        cmd = (' ').join(['wmqlqc.py',
                          '-i', self.input(),
                          '-s', self.id,
                          '-o', self.wmqlqc_out])
        p = Popen(cmd, shell=True)
        p.wait()

    def output(self):
        return local.path(self.input()[0].replace('wmql','wmqlqc'))

