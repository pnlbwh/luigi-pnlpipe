import numpy as np

from conversion import read_bvals, read_bvecs
from nibabel import load
import json
import vtk
from vtk.util.numpy_support import vtk_to_numpy

REL_DIFF_THRESH = 10

def test_header(params):

    gt_data= load(params['gt_name'])
    out_data= load(params['out_name'])

    np.testing.assert_almost_equal(gt_data.affine, out_data.affine)


def test_data(params):

    gt_data= load(params['gt_name']).get_fdata()
    out_data= load(params['out_name']).get_fdata()

    # relative percentage difference
    rel_diff = 2 * abs(gt_data - out_data).sum() / (gt_data + out_data).sum() * 100
    np.testing.assert_array_less(rel_diff, REL_DIFF_THRESH)


def test_bvals(params):

    gt_data= np.array(read_bvals(params['gt_name']))
    out_data= np.array(read_bvals(params['out_name']))

    # relative percentage difference
    rel_diff = 2 * abs(gt_data - out_data).sum() / (gt_data + out_data).sum() * 100
    np.testing.assert_array_less(rel_diff, REL_DIFF_THRESH)


def test_bvecs(params):

    gt_data = np.array(read_bvecs(params['gt_name']))
    out_data = np.array(read_bvecs(params['out_name']))

    # relative percentage difference
    rel_diff = 2 * abs(gt_data - out_data).sum() / (gt_data + out_data).sum() * 100
    np.testing.assert_array_less(rel_diff, REL_DIFF_THRESH)


def test_json(params):

    with open(params['gt_name']) as f:
        gt_data = json.load(f)

    with open(params['out_name']) as f:
        out_data = json.load(f)

    np.testing.assert_equal(gt_data, out_data)


def test_html(params):

    with open(params['gt_name']) as f:
        gt_data = f.read()

    with open(params['out_name']) as f:
        out_data = f.read()

    np.testing.assert_equal(gt_data, out_data)



def read_tensor(filename, tenname):

    # Read vtk
    pdr = vtk.vtkPolyDataReader()
    pdr.SetFileName(filename)
    pdr.Update()
    out = pdr.GetOutput()
    pd = out.GetPointData()

    tensors = pd.GetArray(tenname)

    if tensors is not None:
        return vtk_to_numpy(tensors)
    else:
        return -1


def test_tracts(params):

    for t in ['tensor1', 'tensor2']:
        gt_data= read_tensor(params['gt_name'], t)
        out_data= read_tensor(params['out_name'], t)


        # relative percentage difference
        rel_diff = 2 * abs(gt_data - out_data).sum() / (gt_data + out_data).sum() * 100
        np.testing.assert_array_less(rel_diff, REL_DIFF_THRESH)

