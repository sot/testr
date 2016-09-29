/usr/bin/git clone ${PACKAGES_REPO}/${PACKAGE}
cd ${PACKAGE}
git checkout master
python setup.py build_ext --inplace
py.test test.py -v
