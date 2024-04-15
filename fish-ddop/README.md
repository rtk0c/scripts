# `ddop`: Jump into a temporary workspace for Fish Shell

Have you ever just wanted to have a clean folder as your cwd in the terminal, so you can use wildcard globs all you want and not have worry about picking up other, existing files? Perhaps you need to unzip something, which contains a few interesting files and a few unneeded? `ddop` is a set of commands for speeding up command sequences like `mkdir /tmp/temp; cd /tmp/temp; ...... cd; rm -rf /tmp/temp`. Especially to alleviate the annoyance of trying to find an unused directory name under `/tmp`.

- Run `ddop` to enter a tmp directory
    - A marker file `.workspace-marker` marks this dir as created by `ddop`. `ddone` below only works for dirs that contains this marker file.
    - A symlink `.there` will be created pointing back where you ran `ddop`, for easier grabbing files from there.
    - (Note "ddop" is just a sequence of letters that's easy to type. It has no specific meaning whatsoever.)
- Run `ddone` when you are done, putting tmp dir into a trash dir and cd's back into where you've ran `ddop`
- Run `dclean_all` to clear the trash dir.

These files are meant to be dropped in your `$XDG_CONFIG_HOME/fish/functions`. Fish will automatically load them.

# Example workflow

```sh
$ pwd
~/Downloads

$ ls
logs.zip
$ ddop # Now you're in a temp workspace dir
$ ls -a
.workspace-marker   @.there -> ~/Downloads

# Doing some sutff, make use of globs extensively!
$ unzip .there/logs.zip
$ ls
AppFoo-log-1.txt    AppFoo-log-2.txt    AppBar-log-1.txt    AppBar-log-2.txt
$ rm *-1.txt
$ 7z a logs-filtered.7z *
$ mv logs-filtered.7z .there

$ ddone # Now you're back to ~/Downloads
$ ls
logs.zip    logs-filtered.7z

# Optinoally run this to actually delete the temp workspace dir from the trash
$ dclean_all
This is going to delete everything in /tmp/$USER-wksp-trash
Do you want to continue? [y/N] y↵
```
