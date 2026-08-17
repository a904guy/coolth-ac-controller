from importlib import metadata

try:
    __version__ = metadata.version("coolth")
except metadata.PackageNotFoundError:
    __version__ = "UNKNOWN"
