import os
import json
import click
import logging
import typing as t

from uuid import uuid4

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

DATA_HOME: str = os.environ.get("XDG_DATA_HOME") or os.path.join(
    os.environ.get("HOME", "~"), ".local/share"
)
DATA_HOME = os.path.join(DATA_HOME, PROG_NAME)
CONFIG: t.Dict[str, t.Any] = {}

# To be assigned during initialization
BOARDS_HOME: str = ""
DELETED_BOARDS_HOME: str = ""


def message_printer(level_char: str, **kwargs: t.Any) -> t.Callable[[str], None]:
    def f(message: str) -> None:
        click.secho(f" * [{level_char}] {message}", **kwargs)

    return f


msg_debug = message_printer("d")
msg_info = message_printer("i", fg="white")
msg_important = message_printer("!", fg="yellow")
msg_err = message_printer("e", fg="red", err=True)


def load_json(path: str, handle_errors: bool = True) -> t.Dict[str, t.Any]:
    try:
        with open(path, "r") as f:
            return json.loads(f.read())
    except Exception as ex:
        if handle_errors:
            msg_err(f"Error reading from {path}: {ex}")
            return {}
        raise


def write_json(path: str, data: t.Dict[str, t.Any]) -> None:
    try:
        with open(path, "w") as f:
            f.write(json.dumps(data, indent=2))
    except Exception as ex:
        msg_err(f"Error writing to {path}: {ex}")


def load_config() -> t.Dict[str, t.Any]:
    conf_path: str = os.path.join(DATA_HOME, CONFIG_FILE)
    try:
        result = load_json(conf_path, handle_errors=False)
        msg_info(f"Config loaded from {conf_path}")
        return result
    except:
        return {}


def write_config() -> None:
    conf_path: str = os.path.join(DATA_HOME, CONFIG_FILE)
    write_json(conf_path, CONFIG)
    msg_info(f"Config saved to {conf_path}")


def ensure_path(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path


app = Flask(__name__)
CORS(app)


@app.before_request
def check_token() -> None:
    if request.method == "OPTIONS":
        return

    token: t.Optional[str] = request.headers.get("X-Access-Token")
    if not token or token != CONFIG.get("auth"):
        msg_important(f"Unauthorized request from {request.remote_addr} rejected")
        abort(401)


@app.route("/board/<board_id>", methods=["PUT"])
def save_board(board_id: str) -> str:
    try:
        board_path: str = ensure_path(os.path.join(BOARDS_HOME, board_id))

        data = json.loads(request.form.get("data", "{}"))
        meta = json.loads(request.form.get("meta", "{}"))

        rev: int = int(data.get("revision", "0"))
        data_path = os.path.join(board_path, REV_FILE_PATTERN.format(rev))
        write_json(data_path, data)

        meta_path = os.path.join(board_path, META_FILE)
        write_json(meta_path, meta)

        msg_info(f"Saved board '{data['title']}' ({board_id}), rev {rev}...")
        return "true"
    except Exception as ex:
        msg_err(f"Error saving board {board_id}: {ex}")
        return "false"


@app.route("/board/<board_id>", methods=["DELETE"])
def nuke_board(board_id: str) -> str:
    old_path: str = os.path.join(BOARDS_HOME, board_id)
    new_path: str = os.path.join(DELETED_BOARDS_HOME, board_id)

    try:
        os.rename(old_path, new_path)
        return "true"
    except Exception as ex:
        msg_err(f"Error renaming {old_path} to {new_path}: {ex}")
        return "false"


@app.route("/config", methods=["PUT", "OPTIONS"])
def save_config() -> str:
    conf: t.Optional[str] = request.form.get("conf")
    if conf:
        CONFIG["conf"] = conf
        write_config()
    return "true"


def init(
    data: t.Optional[str], reset_token: bool, override_token: t.Optional[str]
) -> None:
    global DATA_HOME
    global CONFIG
    global BOARDS_HOME
    global DELETED_BOARDS_HOME

    DATA_HOME = ensure_path(data or DATA_HOME)
    msg_info(f"Using data directory {DATA_HOME}")

    BOARDS_HOME = ensure_path(os.path.join(DATA_HOME, BOARDS_SUBDIR))
    DELETED_BOARDS_HOME = ensure_path(os.path.join(DATA_HOME, DELETED_BOARDS_SUBDIR))
    CONFIG = load_config()

    save: bool = False

    if override_token:
        # Override any internal token with the passed one
        CONFIG["auth"] = override_token
        save = True

    # Use an autogenerated one if needed and save it
    if reset_token or ("auth" not in CONFIG):
        CONFIG["auth"] = str(uuid4()).replace("-", "")  # What can I say? I'm lazy...
        save = True

    if save:
        write_config()


def start_server(
    addr: str,
    port: int,
    data: t.Optional[str],
    reset_token: bool,
    override_token: t.Optional[str],
) -> None:
    init(data, reset_token, override_token)

    msg_important(f"Nullboard token: {CONFIG['auth']}")

    msg_info(f"Server listening {addr}:{port}...")
    try:
        app.run(host=addr, port=port, debug=False)
    except Exception as ex:
        msg_err(f"Error starting server: {ex}")


@click.command()
@click.option(
    "--addr",
    required=False,
    type=str,
    default=DFAULT_ADDR,
    show_default=True,
    help="Bind to address",
)
@click.option(
    "--port",
    required=False,
    type=int,
    default=DEFAULT_PORT,
    show_default=True,
    help="Use custom port",
)
@click.option(
    "--data",
    required=False,
    type=str,
    default=DATA_HOME,
    show_default=True,
    help="Directory for data",
)
@click.option(
    "--reset-token",
    required=False,
    is_flag=True,
    help="Generate a new random auth token",
)
@click.option(
    "--override-token", required=False, type=str, help="Use a custom auth token"
)
def cli(
    addr: str,
    port: int,
    data: t.Optional[str],
    reset_token: bool,
    override_token: t.Optional[str],
) -> None:
    """A Nullboard backup agent"""
    try:
        # Let's reduce Flask logging a bit
        logging.getLogger("werkzeug").setLevel(logging.ERROR)
    except:
        pass

    start_server(
        addr=addr,
        port=port,
        data=data,
        reset_token=reset_token,
        override_token=override_token,
    )


if __name__ == "__main__":
    cli()
