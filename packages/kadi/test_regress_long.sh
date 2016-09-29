# Get three launcher scripts manage.py update_events and update_cmds
/usr/bin/git clone ${PACKAGES_REPO}/kadi
cd kadi
# For now just use master.  See https://github.com/sot/kadi/issues/84
#
# VERSION=`python -c "import kadi; print(kadi.__version__)"`
# git checkout $VERSION
#
cp manage.py update_events update_cmds ltt_bads.dat ../
cd ..
rm -rf kadi

export KADI=$PWD
./manage.py syncdb --noinput

START='2015:001'
STOP='2015:030'

./update_events --start=$START --stop=$STOP
./update_cmds --start=$START --stop=$STOP

# Write event and commands data using test database
./write_events_cmds.py --start=$START --stop=$START --data-root=events_cmds
