# rsync here

Transfer files using rsync between two machines that have network connectivity, but maybe not SSH configured.

Suppose you have machine A and B that's on a _trusted_ LAN, but either you don't have permissions to setup SSH, or (more likely) you simply need this one-off file transfer that you can't be bothered to setup SSH. Normally, you'd have to shell out for something stupid like telnet or much more heavyweight like [LocalSend](https://localsend.org/) and [croc](https://github.com/schollz/croc).



This script runs rsync in daemon mode, _without encryption or authentication_, on a local directory on machine A. Then you can simply point rsync on machine B to A's IP to transfer files.

It's works much closer to a WebDAV server than conventional SSH-based rsync. All file operations are localized within the served folder on A.

## Usage

```sh
# on machine A, 10.0.1.12
# suppose I want to transfer folder ./foo/bar
$ rsync_here.sh . 10.0.1.12 12345
... output omitted — which prints instructions as well ...

# on machine B, 10.0.1.15
$ rsync -arP rsync://10.0.1.12:12345/T/foo/bar ./
```

All usual flags should work.

The "T" in `rsync://10.0.1.12/T/...` is hardcoded by the script because rsync daemon demands a name for this share. For the uninitiated, it's basically like a SMB share name, so I simply picked one that's short. "T" stands for "target".
