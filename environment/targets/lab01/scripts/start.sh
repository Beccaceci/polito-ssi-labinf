httpd-foreground &
exim4 -bd -q15m &
python3 /usr/local/bin/not_ftp.py &
python3 /usr/local/bin/secret.py