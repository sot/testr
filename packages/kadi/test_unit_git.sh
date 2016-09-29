VERSION=`python -c "import kadi; print(kadi.__version__)"`
/usr/bin/git clone ${PACKAGES_REPO}/${PACKAGE}
cd ${PACKAGE}
git checkout ${VERSION}
py.test kadi/tests -v
