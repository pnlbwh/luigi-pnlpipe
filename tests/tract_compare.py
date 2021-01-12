#!/usr/bin/env python
import numpy
import vtk
import nibabel
from nibabel.affines import apply_affine

def read_polydata(filename):
    reader = vtk.vtkPolyDataReader()
    reader.SetFileName(filename)
    reader.Update()
    outpd = reader.GetOutput()
    del reader

    return outpd


def convert_cluster_to_volume(inpd, volume):

    volume_shape = volume.get_data().shape
    new_voxel_data = numpy.zeros(volume_shape)

    inpoints = inpd.GetPoints()

    inpd.GetLines().InitTraversal()
    for lidx in range(0, inpd.GetNumberOfLines()):

        ptids = vtk.vtkIdList()
        inpd.GetLines().GetNextCell(ptids)

        for pidx in range(0, ptids.GetNumberOfIds()):
            point = inpoints.GetPoint(ptids.GetId(pidx))

            point_ijk = apply_affine(numpy.linalg.inv(volume.affine), point)
            point_ijk = numpy.rint(point_ijk).astype(numpy.int32)

            new_voxel_data[(point_ijk[0], point_ijk[1], point_ijk[2])] += 1

    return new_voxel_data


def calc_dice(voxel_data_l, voxel_data_2):

    voxel_data_1[numpy.isnan(voxel_data_1)] = 0
    voxel_data_2[numpy.isnan(voxel_data_2)] = 0

    mask_data_1 = numpy.sign(voxel_data_1)
    mask_data_2 = numpy.sign(voxel_data_2)

    n_1 = numpy.sum(mask_data_1)
    n_2 = numpy.sum(mask_data_2)

    w_1 = numpy.sum(voxel_data_1)
    w_2 = numpy.sum(voxel_data_2)

    mask_intersection = numpy.logical_and(mask_data_1, mask_data_2)

    n_ = numpy.sum(mask_intersection)

    w_1_ = numpy.sum(voxel_data_1[mask_intersection])
    w_2_ = numpy.sum(voxel_data_2[mask_intersection])

    dice_standard = 2 * n_ / (n_1 + n_2)
    dice_weighted = (w_1_ + w_2_) / (w_1 + w_2)


    return dice_standard, dice_weighted


def tract2vol(tract_name, volume_name):
    inpd= read_polydata(tract_name)
    volume = nibabel.load(bse_name)
    voxel_data= convert_cluster_to_volume(inpd, volume)

    return voxel_data


