# nbagent

`nbagent` is a [Nullboard](https://github.com/apankrat/nullboard) backup agent for Unix systems.

It works in the same way that the official [Nullboard Backup Agent](https://github.com/apankrat/nullboard-agent) for Windows.

> Note: I also created [https://github.com/luismedel/docker-nullboard](https://github.com/luismedel/docker-nullboard) in case you want to have a full self-contained Nullboard installation (Nullboard app + nbagent)

## Installation

```sh
$ pip install nbagent
```

## Usage

Invoke `nbagent`:

```sh
$ nbagent
```

Immediately you'll see an output similar to this:

```sh
 * [i] Using data directory /Users/luis/.local/share/nbagent
 * [i] Config saved to /Users/luis/.local/share/nbagent/app-config.json
 * [!] Nullboard token: d6606ecaaae54612906cc56a75583b61
 * [i] Server listening 0.0.0.0:10001...
 ```

Note the line:

```
 * [!] Nullboard token: d6606ecaaae54612906cc56a75583b61
```

Just copy the auth token (in this example `d6606ecaaae54612906cc56a75583b61`) into Nullboard, [as per the instructions](https://nullboard.io/backups) and you're **ready to go**.

If for any reason you need to reset the auth token use:

 ```sh
$ nbagent --reset-token
```

You can also set a custom token if you want:

 ```sh
$ nbagent --override-token "123-456-789"
```

### Overriding defaults

`nbagent` allows you to specify several settings if you're not comfortable with the defaults.

> Note that `nbagent` don't use hardcoded paths for the data. It tries to use the standard directory `$XDG_DATA_HOME`. If not defined, it defaults to `$HOME/.local/share`.`

 ```sh
 $ nbagent --help

Usage: nbagent [OPTIONS]

  Start listening for Nullboard requests.

Options:
  --addr TEXT            Bind to address  [default: 0.0.0.0]
  --port INTEGER         Use custom port  [default: 10001]
  --data TEXT            Directory for data  [default: ~/.local/share/nbagent]
  --reset-token          Generate a new random auth token
  --override-token TEXT  Use a custom auth token
  --help                 Show this message and exit.
```
