# Command states scripts and module already installed in skadev
git clone ${PACKAGES_REPO}/${PACKAGE}
cd ${PACKAGE}
git checkout master
nosetests timelines_test.py
