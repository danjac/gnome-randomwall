This script will change your desktop wallpaper in a GNOME environment.

### INSTALL

> python setup.py install --user

### USAGE

> python -m randomwall

Local directory is assumed to be *$HOME/Pictures/Wallpapers*.


### TIMER

Default is set to every 5 minutes; edit *randomwall.timer* accordingly.

**Note**: local systemd directory may vary per distro

```bash

cp systemd/* ~/.local/share/systemd/user

systemctl --user enable randomwall.service

systemctl --user enable --now randomwall.timer

systemctl --user status randomwall.service

systemctl --user status randomwall.timer

```

