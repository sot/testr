SOT_REPO='git@github.com:/sot'
VERSION=`python -c "import kadi; print(kadi.__version__)"`
git clone ${SOT_REPO}/kadi
cd kadi
git checkout ${VERSION}
py.test kadi/tests -v
