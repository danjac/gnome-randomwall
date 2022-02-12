This script will change your wallpaper in a GNOME desktop environment. Requires Python 3.9+.

### INSTALL

> python setup.py install --user

### USAGE

> python -m randomwall

Local directory is assumed to be *$HOME/Pictures/Wallpapers*. If you want to change this you can create a config file under *$HOME/.config/randomwall/config.json*:

```json

{
  "wallpaper_dir": "/path/to/wallpapers"
}

```


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

