# godot-starter-template

A Godot 4.7 project template: type-safety warnings promoted to build errors,
gdformat and gdlint, gdUnit4 tests, a one-command check pipeline, GitHub
Actions CI, a pre-commit hook and a logging autoload.

## Quickstart

```bash
git clone https://github.com/rznn7/godot-starter-template.git my-game
cd my-game
rm -rf .git && git init
uv run scripts/dev.py hooks
git add -A && git commit -m "Initial commit"
```

GitHub's "Use this template" button does the same without the `rm -rf`.

Then make it your project:

- **`project.godot`** — set `config/name` to your game's name (or Project Settings → Application → Config → Name in the editor).
- **`README.md`** and **`LICENSE`** — replace both with your own.

Then point at a Godot 4.7 binary and run the checks:

```bash
export GODOT=/path/to/Godot_v4.7.2-stable_linux.x86_64   # or have `godot` on PATH
uv run scripts/dev.py
```

`scripts/dev.py` declares `gdtoolkit==4.5.0` in a PEP 723 header, so `uv`
handles the dependency. Without `uv`:

```bash
pip install gdtoolkit==4.5.0 && python scripts/dev.py
```

## Commands

```bash
uv run scripts/dev.py               # everything
uv run scripts/dev.py import        # build the Godot import cache
uv run scripts/dev.py typecheck     # compile every script in the running project
uv run scripts/dev.py lint          # gdlint
uv run scripts/dev.py format        # reformat every script in place
uv run scripts/dev.py format-check  # report unformatted scripts, change nothing
uv run scripts/dev.py test          # the gdUnit4 suites
uv run scripts/dev.py hooks         # install the git pre-commit hook

uv run scripts/dev.py lint --staged # only the .gd files staged for commit
```

`lint`, `format` and `format-check` are pure gdtoolkit and don't need Godot
installed; each accepts `--staged`. The rest resolve the binary via `GODOT` or
`PATH`. `--help` lists the same commands.

## GDScript rules

An opinionated subset of Godot's GDScript warnings is promoted to compile
errors, so unsound code fails the build instead of surfacing at runtime:
untyped declarations, unsafe casts and calls, implicit narrowing, integer
division into a float, and enum and `await` mistakes. Style and hygiene
warnings stay warnings.

All 46 warnings are assigned explicitly in `project.godot`'s `[debug]`
section.

Prefer restructuring over `@warning_ignore`:

```gdscript
var progress: float = current_hp / max_hp          # error: integer_division
var progress: float = current_hp / float(max_hp)   # fix
```

## Check pipeline

`check` runs five stages, all of them even if an earlier one fails, so one
invocation reports everything at once.

1. **Import** — builds the Godot import cache.
2. **Typecheck** — compiles every `.gd` file *inside the running project*, so
   autoloads, `class_name` globals and UID references resolve as they do at
   runtime. This is what enforces the error-level rules, and each failure
   names its own file.
3. **Format** — `gdformat --check`.
4. **Lint** — `gdlint`.
5. **Tests** — headless gdUnit4 over `tests/`.

## Hooks

There is no format-on-save: Godot's built-in editor has no formatter hook, and
`.editorconfig` only covers whitespace, not gdformat's rules. The portable
equivalent is a pre-commit hook.

```bash
uv run scripts/dev.py hooks
```

That points git at `.githooks/`, whose `pre-commit` runs `format-check` and
`lint` over **only the `.gd` files staged for that commit**, and blocks the
commit if either fails, naming the files and the command to fix them. It never
rewrites your code, so you always review what you commit. Each clone runs the
install once. `git commit --no-verify` skips it.

`--staged` works outside the hook too, on any of `lint`, `format` and
`format-check` — `uv run scripts/dev.py lint --staged` checks what you are
about to commit and nothing else.

## Lint

`.gdlintrc`: naming conventions, class member ordering, 100-column lines,

## Format

`gdformat`, with `.editorconfig` covering everything else — tabs for `.gd`,
spaces for `.py`/`.yml`/`.md`, LF, final newline.

## CI

`.github/workflows/ci.yml` runs on push to `main` and on every PR, in the
`barichello/godot-ci:4.7.2` container, invoking the same `uv run scripts/dev.py`.

## Tests

gdUnit4 suites in `tests/unit/`, extending `GdUnitTestSuite`:

```gdscript
extends GdUnitTestSuite


func test_something_behaves_correctly() -> void:
	var result: int = 2 + 2
	assert_int(result).is_equal(4)
```

## Log

`autoload/log.gd` defines `AppLog`, registered as the `Log` autoload: four
levels, `min_level` filtering, `push_warning` at `WARN` and above.

```gdscript
func _ready() -> void:
	Log.info("Template ready.")
```

## License

The template is [0BSD](LICENSE) — use it for anything, no attribution, no
obligations. Delete this `LICENSE` and drop in your project's own; that's the
intended path, not an oversight.

`addons/gdUnit4/` is vendored [gdUnit4](https://github.com/MikeSchulze/gdUnit4)
by Mike Schulze, MIT-licensed. Keep `addons/gdUnit4/LICENSE` in place — MIT
requires that notice to travel with the code. It's a dev dependency, so exclude
`addons/gdUnit4/*` from your export presets and it stays out of your build.
