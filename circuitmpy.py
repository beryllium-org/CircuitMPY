from os import system, mkdir, path, popen, environ, chmod
from platform import uname
from getpass import getuser
from urllib import request
from itertools import product

autompy = None
failover_version = [9, 0, 0, None]


class UnsupportedMachineError(Exception):
    def __init__(self, machine_name):
        self.machine_name = machine_name

    def __str__(self):
        return f"The machine type {self.machine_name} is not supported"


def compile_mpy(source, dest, name=None, optim=3):
    """
    Compile a .py to an .mpy

    optim is the level of optimisation, set to 0 in order to debug
    """
    global autompy
    autompy = fetch_mpy()
    if autompy is None:
        raise OSError("Compilation failed")
    if uname().system in ["Linux", "Darwin"]:
        slash = "/"
        copy = "rsync -h"
    else:
        slash = "\\"
        copy = "copy"
    if name is None:
        name = source[source.rfind(slash) + 1 : -3]
    a = system(
        f"./{autompy} {source} -s {name} -v -O{optim} -o {dest}".replace("/", slash)
    )
    if a != 0:
        raise OSError("Compilation failed")


def detect_board():
    ami = getuser()
    boardpath = None
    board = None
    version = failover_version.copy()

    try:
        board = environ["BOARD"]
        boardpath = "build_" + board
        try:
            mkdir(boardpath)
        except:
            pass
    except KeyError:
        pass

    if (board is None) and (uname().system != "Windows"):
        prefixes = [f"run/media/{ami}", f"media/{ami}", "media", "Volumes", "Volumes"]
        try:
            with open("/tmp/CUSTOMBOARDPATH") as f:
                prefixes.append(f.read())
        except:
            pass
        directories = ["CIRCUITPY"]
        try:
            directories.append(environ["FSNAME"])
        except KeyError:
            pass

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
            if boardpath is not None:
                break

    if (boardpath is not None) and (not boardpath.startswith("build_")):
        with open(f"{boardpath}/boot_out.txt", "r") as boot_out:
            magic = boot_out.readlines()
            board = magic[1][9:-1]
            version = magic[0][23 : magic[0].find(" on ")]
            del magic

    try:
        version = environ["MPYVER"]
    except KeyError:
        pass

    return [boardpath, board, version]


def fetch_mpy(version=None, special=None, force=False, verbose=False, retry=False):
    if version is None and not retry:
        detection = detect_board()[2]
        if isinstance(detection, str):
            if detection.find("-") != -1:
                special = detection[detection.find("-") + 1 :]
                detection = detection[: detection.find("-")]
            version = detection.split(".")
        else:
            version = detection
    elif retry:
        version = failover_version[:3]
        special = failover_version[3]
    if special is not None and "dirty" in special:
        print("trimming version identifier as it's dirty.")
        try:
            for i in range(3):
                special = special[: special.rfind("-")]
        except IndexError:
            pass
    url = "https://adafruit-circuit-python.s3.amazonaws.com/bin/mpy-cross/"
    sys = uname().system
    mac = uname().machine

    # Url creation based on machine
    if sys == "Linux":
        url += "linux-"
        appen = ".static"
        if mac == "aarch64":
            url += f"{mac}/mpy-cross-linux-aarch64-"
            appen += f"-{mac}"
        elif mac == "x86_64":
            url += "amd64/mpy-cross-linux-amd64-"
        elif mac == "armv7l":
            url += "raspbian/mpy-cross-linux-raspbian-"
            appen += f"-raspbian"
        else:
            raise UnsupportedMachineError(f"{sys}_{mac}")
        url += f"{version[0]}.{version[1]}.{version[2]}"
        if special is not None:
            url += f"-{special}"
        url += appen
        del appen
    elif sys == "Windows":
        url += f"windows/mpy-cross-windows-{version[0]}.{version[1]}.{version[2]}"
        if special is not None:
            url += f"-{special}"
        url += ".static.exe"
    elif sys == "Darwin":
        url += f"macos-11/mpy-cross-macos-11-{version[0]}.{version[1]}.{version[2]}"
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
        if verbose:
            print("Same version mpy-cross exists, skipping download")
        return target_name
    else:
        if verbose:
            print(f"Downloading {target_name} from:\n{url}")
        try:
            request.urlretrieve(url, target_name)
            chmod(target_name, 0o755)
            return target_name
        except:
            if not retry:
                print(
                    "Download failed, retrying with known good mpy-cross url instead."
                )
                res = fetch_mpy(retry=True, verbose=verbose)
                return res
            else:
                print("Download failed!")
                return None
