import pytest
from os.path import splitext, abspath, basename, dirname, join as pjoin
from nibabel import load

REF_DIR = pjoin(abspath(dirname(__file__)), 'Reference')


def pytest_addoption(parser):

    parser.addoption(
        "--filename",
        help="image filename",
    )

    parser.addoption(
        "--outroot",
        help="root directory container CTE/ and HCP/ folders",
    )


@pytest.fixture
def params(request):

    filename= abspath(request.config.getoption('filename'))
    outroot = abspath(request.config.getoption('outroot'))

    gt_img = load(filename.replace(outroot, REF_DIR))
    out_img = load(filename)

    print('Testing', splitext(basename(filename))[0])

    return (gt_img, out_img)

