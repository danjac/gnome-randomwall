import argparse
import contextlib
import glob
import json
import os
import pathlib
import random
import sys
from typing import Dict, List, Optional, Union
from urllib.parse import quote, urlparse

import requests

Path = Union[pathlib.Path, str]

config: Dict = {}

home = pathlib.Path().home()
wallpaper_dir = home / "Pictures" / "Wallpapers"
config_dir = home / ".config" / "randomwall"

config_file = config_dir / "config.json"
history_file = config_dir / "history"
blacklist_file = config_dir / "blacklist"
favorites_file = config_dir / "favorites"

extensions = (
    "jpeg",
    "jpg",
    "png",
    "svg",
)

extensions += tuple(s.upper() for s in extensions)

parser = argparse.ArgumentParser()
parser.add_argument(
    "-b",
    "--blacklist",
    help="Add current wallpaper to blacklist and choose another wallpaper",
    action="store_true",
)

parser.add_argument(
    "-d",
    "--delete",
    help="If used with the --blacklist option will delete that wallpaper. "
    "If used alone it will delete ALL wallpapers in the blacklist",
    action="store_true",
)

parser.add_argument(
    "-n",
    "--notify",
    help="Send notification of wallpaper change",
    action="store_true",
)

parser.add_argument(
    "-s",
    "--save",
    nargs="*",
    default=[],
    help="Save wallpaper URL to dir",
)


parser.add_argument(
    "-f",
    "--favorite",
    help="Add current wallpaper to favorites.",
    action="store_true",
)

parser.add_argument(
    "-r", "--reload", help="Clears history file", action="store_true"
)  # noqa

parser.add_argument(
    "-c", "--current", help="Prints current wallpaper", action="store_true"
)


def main() -> None:
    global config

    config_dir.mkdir(exist_ok=True)

    if config_file.exists():
        config = json.load(config_file.open("r"))

    args = parser.parse_args()

    if args.save:
        save_wallpaper(args.save)
        return

    if args.reload:
        delete_file(history_file)
        return

    if args.current:
        sys.stdout.write(
            (get_current_wallpaper() or "No wallpaper selected") + "\n"
        )  # noqa
        return

    if args.favorite:
        fave_current_wallpaper(args.notify)
        return

    if args.blacklist:
        blacklist_current_wallpaper(args.notify, args.delete)
        return

    if args.delete:
        delete_blacklist()
        return

    choose_wallpaper(args.notify)


def get_wallpaper_dir() -> pathlib.Path:
    if dirname := config.get("wallpaper_dir"):
        pathlib.Path(dirname)
    return wallpaper_dir


def get_wallpapers_from_file(filename: Path) -> List[str]:
    try:
        return [
            f
            for f in open(filename).read().splitlines()
            if os.path.exists(f) or is_url(f)
        ]

    except OSError:
        return []


def delete_file(filename: Path) -> None:
    with contextlib.suppress(OSError):
        os.remove(filename)


def add_wallpaper_to_file(wallpaper: str, filename: Path) -> None:
    with open(filename, "a") as fp:
        fp.write(wallpaper + "\n")


def get_wallpapers() -> List[str]:
    wallpapers = []

    for ext in extensions:
        wallpapers.extend(glob.glob(str(get_wallpaper_dir() / "*.%s") % ext))

    return wallpapers


def get_favorites() -> List[str]:
    return get_wallpapers_from_file(favorites_file)


def get_blacklist() -> List[str]:
    return get_wallpapers_from_file(blacklist_file)


def get_history() -> List[str]:
    return get_wallpapers_from_file(history_file)


def check_history(wallpapers: List[str]) -> List[str]:
    if not wallpapers:
        return []

    history = get_history()

    choices = [w for w in wallpapers if w not in history]

    if not choices:
        choices = wallpapers
        delete_file(history_file)

    # favorites can be picked even if in history
    choices += get_favorites()

    return list(set(choices))


def check_blacklist(wallpapers: List[str]) -> List[str]:
    return [w for w in wallpapers if w not in get_blacklist()]


def send_notify(title: str, msg: str) -> None:
    os.system(f"notify-send '{title}' '{msg}'")


def choose_wallpaper(notify: bool) -> None:
    wallpapers = check_history(check_blacklist(get_wallpapers()))

    if not wallpapers:
        sys.stderr.write("No available wallpapers found in directory")
        sys.exit(1)

    wallpaper = random.choice(wallpapers)

    if not os.path.exists(wallpaper):
        send_notify("Wallpaper not found", wallpaper)
        return

    add_wallpaper_to_file(wallpaper, history_file)

    set_gnome_background(f"file:///{quote(wallpaper)}")

    filename = os.path.basename(wallpaper)

    if notify:
        send_notify("Random wallpaper", filename)
    else:
        sys.stdout.write(filename + "\n")


def set_gnome_background(url: str) -> None:
    for setting in (
        "org.gnome.desktop.background picture-uri",
        "org.gnome.desktop.background picture-uri-dark",
        "org.gnome.desktop.screensaver picture-uri",
    ):
        os.system(f"gsettings set {setting} {url}")


def delete_blacklist() -> None:
    blacklist = get_blacklist()
    if not blacklist:
        return

    if (
        input(
            "This will PERMANENTLY delete %d image(s). Are you sure (Y/N)? "
            % len(blacklist)
        ).lower()
        != "y"
    ):
        return

    for wallpaper in blacklist:
        delete_file(wallpaper)

    delete_file(blacklist_file)


def get_current_wallpaper() -> Optional[str]:
    try:
        return get_history()[-1]
    except IndexError:
        return None


def fave_current_wallpaper(notify: bool) -> None:
    wallpaper = get_current_wallpaper()
    if not wallpaper:
        return

    if is_url(wallpaper):
        response = requests.get(wallpaper)
        wallpaper = str(
            get_wallpaper_dir() / pathlib.Path(urlparse(wallpaper).path).name
        )  # noqa
        with open(wallpaper, "wb") as fp:
            fp.write(response.content)

    add_wallpaper_to_file(wallpaper, favorites_file)

    if notify:
        send_notify(
            "Random wallpaper",
            f"{os.path.basename(wallpaper)} added to favorites",
        )


def is_url(wallpaper: Optional[str]) -> bool:
    return bool(wallpaper) and wallpaper.startswith("http")


def blacklist_current_wallpaper(notify: bool, delete: bool) -> None:
    """
    Find the LAST item in history, add that to blacklist, and
    choose again
    """
    wallpaper = get_current_wallpaper()
    if not wallpaper or wallpaper in get_favorites() or is_url(wallpaper):
        return

    if notify:
        send_notify(
            "Random wallpaper",
            f"{os.path.basename(wallpaper)} added to blacklist",
        )

    if (
        delete
        and input(
            f"Are you sure you want to PERMANENTLY delete the file {wallpaper} (Y/N)? "  # noqa
        ).lower()
        == "y"
    ):
        delete_file(wallpaper)
    else:
        add_wallpaper_to_file(wallpaper, blacklist_file)

    choose_wallpaper(notify)


def save_wallpaper(urls: List) -> None:
    for url in urls:
        parts = urlparse(url)
        filename = os.path.basename(parts.path)
        path = get_wallpaper_dir() / filename
        resp = requests.get(url)
        with open(path, "wb") as fp:
            fp.write(resp.content)
