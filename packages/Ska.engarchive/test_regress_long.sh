# Test creating new engineering archive database and compare to flight data

git clone ${PACKAGES_REPO}/eng_archive
cd eng_archive
git checkout create-faster
cp update_archive.py archfiles_def.sql ../
cd ../
mkdir data

CONTENTS="--content=acis2eng --content=acis3eng --content=acisdeahk --content=simcoor"
START="2016:100"
STOP="2016:105"

# TODO: fix : CONTENTS="--content=orbitephem0"

export ENG_ARCHIVE=$PWD
export PYTHONPATH=/home/aldcroft/git/eng_archive/local/lib/python2.7/site-packages

echo "Creating archive..."
./update_archive.py --date-start $START --date-now $STOP --max-lookback-time=2 \
   --create --data-root=$PWD $CONTENTS

# TODO: add derive parameter --content=dp_acispow128

echo "Creating archive stats..."
./update_archive.py --no-full $CONTENTS --max-lookback-time 1e20

./compare_values.py --start=$START --stop=$STOP $CONTENTS
