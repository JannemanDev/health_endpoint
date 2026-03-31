# use --non-interactive so it can be run under a screen unattended
screen -d -m -S ip_change /volume1/homes/janoonk/health_endpoint/run.sh

# list all screens: screen -ls
# restore a screen: screen -r <screen-id/name>
