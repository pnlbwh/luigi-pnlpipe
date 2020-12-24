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

        _, fsdir = _glob(derivatives_dir, self.fs_template, self.id, self.ses)

        _, dwi = _glob(derivatives_dir, self.dwi_template, self.id, self.ses)

        for suffix in ['XcUnEdEp_dwi', 'XcUnEd_dwi', 'XcUn_dwi', 'Xc_dwi']:
            if suffix in dwi:
                break


        # look for Qc'ed mask first
        # if not present, return the automated mask
        bse_mask_dict= {
            'XcUnEdEp_dwi': ['XcUnCNNQcEdEp_mask', 'XcUnCNNEdEp_mask', 'XcUnEdEp_bse'],
            'XcUnEd_dwi': ['XcUnCNNQc_mask', 'XcUnCNN_mask', 'XcUn_bse'],
            'XcUn_dwi': ['XcUnCNNQc_mask', 'XcUnCNN_mask', 'XcUn_bse'],
            'Xc_dwi': ['XcCNNQc_mask', 'XcCNN_mask', 'Xc_bse']
        }

        dwidir= dirname(dwi)
        try:
            t= pjoin(dwidir, '*' + bse_mask_dict[suffix][0] + '.nii.gz')
            mask= glob(t)[0]
        except IndexError:
            t= pjoin(dwidir, '*' + bse_mask_dict[suffix][1] + '.nii.gz')

            try:
                mask= glob(t)[0]
            except:
                raise FileNotFoundError('Neither *{}.nii.gz nor *{}.nii.gz could be found in {}'
                                        .format(bse_mask_dict[suffix][0], bse_mask_dict[suffix][1], dwidir))

        bse= glob(pjoin(dwidir, '*'+ bse_mask_dict[suffix][2]+'.nii.gz'))[0]

        return dict(fsdir=local.path(fsdir), dwi=local.path(dwi), bse=local.path(bse), mask=local.path(mask))


@inherits(SelectFsDwiFiles,StructMask)
class Fs2Dwi(Task):

    debug= BoolParameter(default=False)
    mode= Parameter(default='direct')

    def requires(self):
        if self.struct_template:
            return self.clone(SelectFsDwiFiles),self.clone(StructMask)
        else:
            return self.clone(SelectFsDwiFiles),


    def run(self):
        cmd = (' ').join(['fs2dwi.py',
                          '-f', self.input()[0]['fsdir'],
                          '--bse', self.input()[0]['bse'],
                          '--dwimask', self.input()[0]['mask'],
                          '-o', self.output()[0].dirname,
                          '-d' if self.debug else '',
                          'direct' if self.mode=='direct'
                          else 'witht2 --t2 {} --t2mask {}'.format(self.input()[1]['aligned'], self.input()[1]['mask'])])
        p = Popen(cmd, shell=True)
        p.wait()

    def output(self):

        wmparc= local.path(self.input()[0]['dwi'].dirname.join('wmparcInDwi.nii.gz').replace('dwi', 'fs2dwi'))
        return wmparc,self.input()[0]['dwi']


@requires(Fs2Dwi)
class Wmql(Task):

    query= Parameter(default='')
    wmql_nproc= IntParameter(default= int(N_PROC))

    def run(self):
        # obtain the tract from dwi prefix
        tract= self.input()[1].replace('/dwi/', '/tracts/').replace('_dwi.nii.gz', '.vtk')

        cmd = (' ').join(['wmql.py',
                          '-f', self.input()[0],
                          '-i', tract,
                          '-o', self.output(),
                          f'-q {self.query}' if self.query else '',
                          f'-n {self.wmql_nproc}' if self.wmql_nproc else ''])
        p = Popen(cmd, shell=True)
        p.wait()


    def output(self):

        return local.path(self.input()[0].dirname.replace('fs2dwi','wmql'))


@requires(Wmql)
class Wmqlqc(Task):

    id = Parameter()
    ses = Parameter(default='')

    def run(self):
        cmd = (' ').join(['wmqlqc.py',
                          '-i', self.input(),
                          '-s', self.id,
                          '-o', self.output()])
        p = Popen(cmd, shell=True)
        p.wait()

    def output(self):

        return local.path(self.input().replace('wmql','wmqlqc'))

