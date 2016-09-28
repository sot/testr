# Get three launcher scripts manage.py update_events and update_cmds
git clone ${PACKAGES_REPO}/kadi
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

START=`python -c 'from Chandra.Time import DateTime; print((DateTime() - 60).date)'`
STOP=`python -c 'from Chandra.Time import DateTime; print((DateTime() - 30).date)'`

./update_events --start=$START --stop=$STOP
./update_cmds --start=$START --stop=$STOP

# Write event and commands data using test database
./write_events_cmds.py --start=$START --stop=$START --data-root=test

# Write event and commands data using flight database
unset KADI
./write_events_cmds.py --start=$START --stop=$START --data-root=flight

echo "Diffing files from test and flight databases"
diff -r test flight



