#!/bin/bash

share_dir=${1:-.}
bind_address=${2:-0.0.0.0}
bind_port=${3:-12783}

temp_dir=${XDG_RUNTIME_DIR:-/tmp}
rsyncd_conf_file=$temp_dir/rsyncd-here.conf



echo '-- rsyncd.conf copied for your reference:'
tee "$rsyncd_conf_file" <<RSYNCD_CONF
address = $bind_address
port = $bind_port
use chroot = false
pid file = $temp_dir/rsyncd-here.pid
reverse lookup = no

[T]
	path = $share_dir
	comment = Share target dir
	read only = false
RSYNCD_CONF



echo "\
--
-- Connect your clients like:
--     rsync /local/file rsync://$bind_address:$port/T/path/to/dest/
--     rsync rsync://$bind_address:$port/T/path/to/file /local/dest/
--
-- You can Ctrl+C to stop this script when you're done with transferring.
--
-- starting rsync daemon
"
exec rsync --daemon --config="$rsyncd_conf_file" --no-detach --log-file=/dev/stdout
