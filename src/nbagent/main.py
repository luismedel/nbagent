
import os
import json
import click
import logging
import typing as t

from uuid import uuid4
from io import TextIOWrapper

from flask import Flask, request, abort
from flask_cors import CORS


PROG_NAME: str = "nbagent"

CONFIG_FILE: str = "app-config.json"
REV_FILE_PATTERN: str = "rev-{0:08}.json"
META_FILE: str = "meta.json"
BOARDS_SUBDIR: str = "boards"
DELETED_BOARDS_SUBDIR: str = "deleted"

DFAULT_ADDR: str = "0.0.0.0"
DEFAULT_PORT: int = 10001


def msg_info(message: str) -> str:
    click.secho(f" * {message}", fg="white")


def msg_important(message: str) -> str:
    click.secho(f" * {message}", fg="yellow")


def msg_err(message: str) -> str:
    click.secho(f" * {message}", fg="red", err=True)


def get_path(root: str | None, relative: str) -> str | None:
    if not root:
        return None
    return os.path.join(root, relative)


def load_file(path: str) -> TextIOWrapper:
    with open(path, "r") as f:
        return f.read()


def write_file(path: str, data: str | bytes) -> None:
    with open(path, "w") as f:
        return f.write(data)


def load_json(path: str) -> t.Dict[str, t.Any]:
    try:
        return json.loads(load_file(path))
    except Exception as ex:
        msg_err(f"Error reading from {path}: {ex}")
        return {}


def write_json(path: str, data: t.Dict[str, t.Any]) -> None:
    try:
        write_file(path, json.dumps(data, indent=2))
    except Exception as ex:
        msg_err(f"Error writing to {path}: {ex}")
        return {}

def ensure_path(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path


DATA_HOME: str = os.environ.get("XDG_DATA_HOME") or get_path(os.environ.get("HOME"), ".local/share")
DATA_HOME = get_path(DATA_HOME, PROG_NAME)
CONFIG: t.Dict[str, t.Any] = {}

# To be assigned during initialization
BOARDS_HOME: str = ""
DELETED_BOARDS_HOME: str = ""


app = Flask(__name__)
CORS(app)


@app.before_request
def check_token() -> None:
    if request.method == "OPTIONS":
        return

    token: t.Optional[str] = request.headers.get("X-Access-Token")
    if not token or token != CONFIG.get("auth"):
        abort(401)


@app.route('/board/<board_id>', methods=["PUT"])
def save_board(board_id):
    try:
        board_path: str = ensure_path(get_path(BOARDS_HOME, board_id))

        data = json.loads(request.form.get("data"))
        meta = json.loads(request.form.get("meta"))

        rev: int = int(data.get("revision", "0"))
        data_path = get_path(board_path, REV_FILE_PATTERN.format(rev))
        write_json(data_path, data)

        meta_path = get_path(board_path, META_FILE)
        write_json(meta_path, meta)

        msg_info(f"Saved board {board_id}, rev {rev}...")
        return "true"
    except Exception as ex:
        msg_err(f"Error saving board {board_id}: {ex}")
        raise


@app.route('/board/<board_id>', methods=["DELETE"])
def nuke_board(board_id):
    old_path: str = get_path(BOARDS_HOME, board_id)
    new_path: str = get_path(DELETED_BOARDS_HOME, board_id)

    try:
        os.rename(old_path, new_path)
        return "true"
    except Exception as ex:
        msg_err(f"Error renaming {old_path} to {new_path}: {ex}")
        raise


@app.route('/config', methods=["PUT", "OPTIONS"])
def save_config():
    conf: str | None = request.form.get("conf")
    if conf:
        CONFIG["conf"] = conf
        write_json(get_path(DATA_HOME, CONFIG_FILE), CONFIG)
    return "true"


def init(data: str | None, override_token: str | None) -> None:
    global DATA_HOME
    global CONFIG
    global BOARDS_HOME
    global DELETED_BOARDS_HOME

    DATA_HOME = ensure_path(data or DATA_HOME)
    BOARDS_HOME = ensure_path(get_path(DATA_HOME, BOARDS_SUBDIR))
    DELETED_BOARDS_HOME = ensure_path(get_path(DATA_HOME, DELETED_BOARDS_SUBDIR))
    CONFIG = load_json(get_path(DATA_HOME, CONFIG_FILE))

    if override_token:
        # Override any internal token with the passed one
        CONFIG["auth"] = override_token
    else:
        # If not overriden, use an autogenerated one if needed and save it
        if "auth" not in CONFIG:
            CONFIG["auth"] = str(uuid4()).replace("-", "")  # What can I say? I'm lazy...
            write_json(get_path(DATA_HOME, CONFIG_FILE), CONFIG)


def start_server(addr: str, port: int, data: str | None, override_token: str | None) -> None:
    init(data, override_token)

    # Show the auto generated token only
    if not override_token:
        msg_important(f"Nullboard token: {CONFIG['auth']}")

    try:
        # Let's reduce Flask logging a bit
        logging.getLogger('werkzeug').disabled = True
    except:
        pass

    msg_info(f"Server listening {addr}:{port}...")
    try:
        app.run(host=addr, port=port, debug=False)
    except Exception as ex:
        msg_err(f"Error starting server: {ex}")


@click.group()
def cli() -> None:
    pass

@cli.command("start")
@click.option('--addr', required=False, type=str, default=DFAULT_ADDR, show_default=True,
              help="Bind to this address")
@click.option('--port', required=False, type=int, default=DEFAULT_PORT, show_default=True,
              help="Bind to this address")
@click.option('--data', required=False, type=str, default=DATA_HOME, show_default=True,
              help="Directory for data")
@click.option('--token', 'override_token', required=False, type=str,
              help="Use a custom auth token insted of the autogenerated one")
def cli_start(addr: str, port: int, data: str | None, override_token: str | None) -> None:
    """Start listening for Nullboard requests.
    """
    start_server(addr=addr, port=port, data=data, override_token=override_token)


def start_default_server() -> None:
    """Debugging helper.
    """
    start_server(addr=DFAULT_ADDR, port=DEFAULT_PORT, data=None, override_token=None)


if __name__ == "__main__":
    cli()
    #start_default_server()
