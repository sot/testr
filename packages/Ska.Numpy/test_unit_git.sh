SOT_REPO='git@github.com:/sot'
git clone ${SOT_REPO}/Ska.Numpy
cd Ska.Numpy
git checkout master
python setup.py build_ext --inplace
py.test test.py -v
