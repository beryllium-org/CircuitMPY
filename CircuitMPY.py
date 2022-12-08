from os import system, mkdir, path, popen, environ
from platform import uname
from getpass import getuser
from urllib import request
from itertools import product


class UnsupportedMachineError(Exception):
    def __init__(self, machine_name):
        self.machine_name = machine_name

    def __str__(self):
        return f"The machine type {self.machine_name} is not supported"


def compile_mpy(source, dest, optim=3):
    pass


def clean_mpy():
    pass


def fetch_mpy(version=[8, 0, 0], special=None, force=False):
    url = "https://adafruit-circuit-python.s3.amazonaws.com/bin/mpy-cross/mpy-cross"
    sys = uname().system
    mac = uname().machine

    # Url creation based on machine
    if sys == "Linux":
        url += ".static-"
        if mac == "aarch64":
            url += mac
        elif mac == "x86_64":
            url += "amd64-linux"
        elif mac == "armv7l":
            url += "raspbian"
        else:
            raise UnsupportedMachineError(f"{sys}_{mac}")
        url += f"-{version[0]}.{version[1]}.{version[2]}"
        if special is not None:
            url += f"-{special}"
    elif sys == "Windows":
        url += f".static-x64-windows-{version[0]}.{version[1]}.{version[2]}"
        if special is not None:
            url += f"-{special}"
        url += ".exe"
    elif sys == "Darwin":
        url += f"-macos-11-{version[0]}.{version[1]}.{version[2]}"
        if special is not None:
            url += f"-{special}"
        if mac == "arm64":
            url += "-arm64"
        else:
            url += "-x64"
    else:
        raise UnsupportedMachineError(f"{sys}_{mac}")

    # Download
    target_name = f"mpy-cross-{version[0]}.{version[1]}.{version[2]}"
    if special is not None:
        target_name += f"-{special}"
    if sys == "Windows":
        target_name += ".exe"

    if path.exists(target_name) and not force:
        print("Same version mpy-cross exists, skipping download")
        return target_name
    else:
        print(f"Downloading:\n{url}\n\nTo: {target_name}")
        try:
            request.urlretrieve(url, target_name)
            return target_name
        except:
            print("Download Failed!")
            return None


def detect_board():
    ami = getuser()
    boardpath = None
    board = ""
    version = [8, 0, 0]  # assume 8.x on wifi boards

    try:
        board = environ["no_install"]
        boardpath = "build_" + board
        try:
            mkdir(boardpath)
        except:
            pass
    except KeyError:
        pass

    prefixes = [f"media/{ami}", "media", "Volumes", "Volumes"]
    directories = [
        "CIRCUITPY",
        "LJINUX",
    ]

    for prefix, directory in product(prefixes, directories):
        p = f"/{prefix}/{directory}"
        if path.exists(p):
            boardpath = p
            break

    if (boardpath is None) and (uname().system == "Windows"):
        print("WARNING: WINDOWS SUPPORT IS EXPERIMENTAL!!")
        drives = [chr(x) + ":" for x in range(65, 91) if path.exists(chr(x) + ":")]
        for _ in drives:
            vol = popen("vol " + _)
            if vol.readline()[:-1].split(" ")[-1].upper() in ["CIRCUITPY", "LJINUX"]:
                boardpath = f"%s" % _
            vol.close()
            if boardpath != "":
                break

    if (boardpath is not None) and (not boardpath.startswith("build_")):
        with open(f"{boardpath}/boot_out.txt", "r") as boot_out:
            magic = boot_out.readlines()
            board = magic[1][9:-1]
            version = magic[0][23 : magic[0].find(" on ")]
            del magic

    sp = version[6:]
    if sp == "":
        sp = None
    version = [int(version[0]), int(version[2]), int(version[4]), sp]
    return [boardpath, board, version]
