from importlib.metadata import entry_points

from callbot.cli import app


def main() -> None:
    for plugin in entry_points(group="callbot.cli"):
        plugin.load()
    app()


if __name__ == "__main__":
    main()
