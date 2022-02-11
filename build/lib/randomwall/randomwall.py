#!/usr/bin/python3

import argparse
import glob
import os
import pathlib
import random
import sys
from typing import List, Optional, Union
from urllib.parse import quote, urlparse

import requests

Path = Union[pathlib.Path, str]

home = pathlib.Path().home()
wallpaper_dir = home / "Pictures" / "Wallpapers"
# wallpaper_dir = home / "Pictures" / "Favorites"
config_dir = home / ".randomwall"

history_file = config_dir / "history"
blacklist_file = config_dir / "blacklist"
favorites_file = config_dir / "favorites"

extensions = (
    "JPEG",
    "JPG",
    "PNG",
    "SVG",
    # "WEBP",
    "jpeg",
    "jpg",
    "png",
    "svg",
    # "webp",
)

api_choices = ("desktoppr", "bing")

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
    help="Add current wallpaper to favorites. If from API will download image "
    "to wallpaper directory before adding to favorites",
    action="store_true",
)

parser.add_argument(
    "-r", "--reload", help="Clears history file", action="store_true"
)  # noqa

parser.add_argument(
    "-c", "--current", help="Prints current wallpaper", action="store_true"
)
parser.add_argument(
    "-a", "--api", help="Select wallpaper from API", choices=api_choices
)


def main() -> None:
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)

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

    if args.api:
        choose_api_wallpaper(args.api, args.notify)
        return

    choose_wallpaper(args.notify)


def choose_api_wallpaper(api: str, notify: bool) -> None:

    actions = {"desktoppr": desktoppr, "bing": bing}

    try:
        url = actions[api](notify)
    except requests.RequestException as e:
        sys.stderr.write(str(e))
        sys.exit(1)

    add_wallpaper_to_file(url, history_file)
    set_gnome_background(url)

    if notify:
        send_notify("Random wallpaper", url)
    else:
        sys.stdout.write(url + "\n")


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
    try:
        os.remove(filename)
    except OSError:
        pass


def add_wallpaper_to_file(wallpaper: str, filename: Path) -> None:
    with open(filename, "a") as fp:
        fp.write(wallpaper + "\n")


def get_wallpapers() -> List[str]:
    wallpapers = []

    for ext in extensions:
        wallpapers.extend(glob.glob(str(wallpaper_dir / "*.%s") % ext))

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

    choices += get_favorites()

    return list(set(choices))


def check_blacklist(wallpapers: List[str]) -> List[str]:
    return [w for w in wallpapers if w not in get_blacklist()]


def send_notify(title: str, msg: str) -> None:
    os.system("notify-send '%s' '%s' " % (title, msg))


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

    set_gnome_background("file:///%s" % quote(wallpaper))

    filename = os.path.basename(wallpaper)

    if notify:
        send_notify("Random wallpaper", filename)
    else:
        sys.stdout.write(filename + "\n")


def bing(notify: bool) -> str:

    response = requests.get(
        "http://www.bing.com/HPImageArchive.aspx?format=js&idx=0&n=1&mkt=en-US"
    )
    response.raise_for_status()
    basename = response.json()["images"][0]["urlbase"]
    return f"https://www.bing.com{basename}_1920x1080.jpg"


def desktoppr(notify: bool) -> str:

    response = requests.get(
        "https://api.desktoppr.co/1/wallpapers/random?safe=all"
    )  # noqa
    response.raise_for_status()
    return response.json()["response"]["image"]["url"]


def set_gnome_background(url: str) -> None:

    # DESKTOP
    os.system("gsettings set org.gnome.desktop.background picture-uri %s" % url)  # noqa

    # LOCK SCREEN
    os.system(
        "gsettings set org.gnome.desktop.screensaver picture-uri %s" % url
    )  # noqa


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
            wallpaper_dir / pathlib.Path(urlparse(wallpaper).path).name
        )  # noqa
        with open(wallpaper, "wb") as fp:
            fp.write(response.content)

    add_wallpaper_to_file(wallpaper, favorites_file)

    if notify:
        send_notify(
            "Random wallpaper",
            "%s added to favorites" % os.path.basename(wallpaper),
        )


def is_url(wallpaper: Optional[str]) -> bool:
    return wallpaper and wallpaper.startswith("http")


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
            "%s added to blacklist" % os.path.basename(wallpaper),
        )

    if (
        delete
        and input(
            "Are you sure you want to PERMANENTLY delete the file %s (Y/N)? "
            % wallpaper
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
        path = wallpaper_dir / filename
        resp = requests.get(url)
        with open(path, "wb") as fp:
            fp.write(resp.content)


if __name__ == "__main__":
    main()
