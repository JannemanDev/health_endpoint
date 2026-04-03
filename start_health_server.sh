# if run from TaskScheduler, cd to the correct folder which is the current folder of this script
cd $(dirname $0)

/usr/bin/python3 health_server.py
