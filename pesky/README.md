# Timed Minecraft Server Start/Stop

- ~~Discipline your players to have a better sleep schedule~~
- Minecraft server running inside a tmux session named `Minecraft`, with exactly 1 tab, and 1 pane in the tab
  - cwd in the shell should have a `./run.sh` file which starts the minecraft server
  - server shouldn't restart on its own after the JVM process exits
    - so like ATM or GTNH's included scripts that calls `java` in a loop won't work
- Configure hours of start/stop using cron
  - see `my_autolifecycle.crontab`
  - Remember to add notices "Server shutting down in 30 minutes" so your players won't be shocked
  - script is basically a glorified wrapper around `tmux send-keys` so I don't have to have a bunch of cruft inside my crontab
