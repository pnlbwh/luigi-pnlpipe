#!/usr/bin/env python
from __future__ import print_function
from util import logfmt, TemporaryDirectory, ANTSREG_THREADS, FILEDIR, pjoin
from plumbum import local, cli, FG
from plumbum.cmd import antsApplyTransforms
from subprocess import check_call

import logging
logger = logging.getLogger()
logging.basicConfig(level=logging.DEBUG, format=logfmt(__file__))


class App(cli.Application):
    """Rigidly align a given labelmap (usually a mask) to make another labelmap"""

    infile = cli.SwitchAttr(['-i','--input'],
                            cli.ExistingFile, help='structural (nrrd/nii)',mandatory=True)

    labelmap = cli.SwitchAttr(['-l','--labelmap'],
                              cli.ExistingFile, help='structural labelmap, usually a mask (nrrd/nii)',mandatory=True)

    target = cli.SwitchAttr(['-t','--target'],
                            cli.ExistingFile, help='target image (nrrd/nii)',mandatory=True)

    out = cli.SwitchAttr(['-o', '--output'], help='output labelmap (nrrd/nii)', mandatory=True)

    def main(self):
        with TemporaryDirectory() as tmpdir:
            tmpdir = local.path(tmpdir)
            pre = tmpdir / 'ants'

            warp = pre + '1Warp.nii.gz'
            affine = pre + '0GenericAffine.mat'

            check_call((' ').join([pjoin(FILEDIR,'antsRegistrationSyNMI.sh'),
                        '-f', self.target,
                        '-m', self.infile,
                        '-o', pre,
                        '-n', ANTSREG_THREADS
                        ]), shell= True)

            antsApplyTransforms['-d', '3'
                                ,'-i', self.labelmap
                                ,'-t', warp
                                ,'-t', affine
                                ,'-r', self.target
                                ,'-o', self.out
                                ,'--interpolation', 'NearestNeighbor'] & FG

if __name__ == '__main__':
    App.run()
