/usr/bin/git clone ${PACKAGES_REPO}/${PACKAGE}
cd ${PACKAGE}
git checkout master
py.test -v
