# Changelog management

## Introduction

This repository contains some simple tools for managing changelogs for
moderate sized projects, or those that have multiple users submitting
changes.

The problem it intends to address is that of changelog differences in
branches becoming a burden to merge due to conflicts. With a single
changelog file, changes which interleave between users over time end
up having conflicts when the diverged branches are finally merged.
This is made worse when branches have existed for a long time - each
merge from master into those branches incurs a cost in conflicts.

## Changelog format

The changelogs managed here follow the intent of <http://keepachangelog.com>
in structuring the changelogs by the type of change being made, using
markdown as the structure format. The changelogs end up looking like
this:

```
## version (date)

### Added
- Feature 1
- Feature 2

### Changed
- Change 1
- Change 2

### Fixed
- Fix 1
- Fix 2
```

When a full changelog is generated, it applies the `header.md` to the
top of the file, and the `footer.md` to the bottom of the file.

Version numbers are expected to be in the form of a sequence of `.`
separated digits.

## Categories

For larger projects, where it helps a reader to see which part of the
system a change affects, entries can be prefixed with a category: a
short label naming the affected area (eg `Backend`, `Frontend`,
`Database`, `UI`, `PlugIns`), followed by a colon and the description:

```
### Fixed
- Backend: Corrected off-by-one error when paginating results.
- UI: Dialogue no longer clips its title on narrow windows.
```

A category is a single word starting with an uppercase letter. This is
purely a convention for how a bullet's text is written, and works
whether or not the rest of this tool is used.

Readers benefit from categories appearing in the same relative order
in every release (eg lower-level components always listed before the
higher-level ones that depend on them). `changelogs/category_report.py`
(run directly; it is not a `cli.py` subcommand) helps establish and
check that order:

- `category_report.py --check-releases` infers an ordering rule
  between every pair of categories from how they appear across all
  releases, then reports how consistently each release matches those
  rules, exiting non-zero if any release is inconsistent.
- `category_report.py --check-current` checks the in-progress
  `current/*.md` files against the ordering inferred from released
  changelogs.
- `category_report.py --use-recommendations` reads an explicit
  `changelogs/recommended.md` file (a bullet list, one category per
  line, in the intended order) and treats that order as authoritative
  rather than merely inferred.
- Run `category_report.py` with no `--check-*` flag to have it infer
  and print its best guess at a consistent ordering from the releases
  that already exist, as a starting point for a new `recommended.md`.

A typical pre-release check is:

    changelogs/category_report.py --use-recommendations --check-releases --check-current

## Changelog files

The files are stored in two location:

- The completed releases are stored in the `releases` directory. These
  files are not expected to be changed except for when the release is
  updated. Each release has its own file, named after the release
  version.
- The current release is stored in the `current` directory. These files
  are named after the branch (or feature) that is within the change.
  When the current changelog is generated, these will be collected into
  a single '[UNRELEASED]' section, ordered alphabetically (but with
  'master' placed first, as it contains the main changes).

## Integrating into a project

The recommended way to use this tool in another project is to copy
this `changelogs` directory into the root of the project being
managed, rather than adding it as a git submodule - a plain copy is
simpler for contributors to work with and avoids submodule friction.
Keep at least `cli.py`, `changelog.py`, `md.py`, `editor.py` and
`header.md`; add `category_report.py` and `recommended.md` too if
using categories. `footer.md` is optional, and the `releases` and
`current` directories are created automatically the first time
they're needed.

Interactive editing (`cli.py edit`) needs `EDITOR` or `VISUAL` set in
the environment.

Wrapping the commands in Makefile targets makes them short and
memorable for everyday use, for example:

```make
change:
	@if [ ! -t 1 ] ; then echo "Not in a tty - cannot edit change" >&2 ; false ; fi
	changelogs/cli.py edit

changelog:
	@changelogs/cli.py current

full-changelog:
	@changelogs/cli.py full-changelog

check-changelog:
	changelogs/category_report.py --use-recommendations --check-releases --check-current

release-update:
	@if [ "${VERSION}" = '' ] ; then echo "VERSION must be specified" >&2 ; false ; fi
	changelogs/cli.py collate "${VERSION}"

release-tag:
	@if [ "${VERSION}" = '' ] ; then echo "VERSION must be specified" >&2 ; false ; fi
	git tag -a "v${VERSION}" -m "Version ${VERSION}"
```

`release-update` is also a natural place to bump any project-specific
version strings (eg in a `project.config` or `__init__.py`) alongside
the `collate` call, so the version bump and the changelog collation
cannot drift out of sync with each other.

## Usage

For almost all the operations the workflow goes through the management
script `changelogs/cli.py`. This tool takes a command as a parameter
to perform on the changelogs. By default it expects the `changelogs`
directory to sit alongside `cli.py`; pass `--changelogs <dir>` before
the command to use a different location.

### Adding or edit a change

To add a new change to the changelog, use the command:

    changelogs/cli.py edit

This will create a new file based on your branch name, if one does not
already exist, and then launch your editor to edit that file. The file
will have `git add` applied to it if it was updated successfully.

When run under a recognised AI coding agent (detected via the `AGENT`,
`GEMINI_CLI`, `QWEN_CODE`, `CLAUDECODE` or `CODEX_HOME` environment
variables), `edit` does not launch an interactive editor. Instead it
creates the file (if necessary) and prints its path, so the agent can
edit it directly with its own file-editing tools. In this mode the
file is not automatically `git add`ed, since that only happens after a
successful interactive editor session - the agent needs to stage it
itself.

### View the current changelog

To view just the current collected changelog, use the command:

    changelogs/cli.py current

This just shows the collected logs from the `current` directory.

### Create a changelog from all the files

To see a full changelog including the current and released logs,
as well as the header and the footer, use the command:

    changelogs/cli.py full-changelog

This can be used by build or release generation to get a complete
changelog that can be viewed by users.

### Create a new release

To create a new release, you must collate all the current changelogs
together into a new release changelog. To do this, use the command:

    changelogs/cli.py collate <version>

It is necessary to supply the version number for the new release so
that the new release file is created correctly. This will also
`git add` the new release file, and `git rm` the changelogs in
current which have been collated.

### Statistics on releases

To create a HTML table showing the statistics about the number of
changes in each release, a simple command can be used:

    changelogs/cli.py statistics-table --output stats.html

This will report the number of changes in each group in the
changelogs by release number. The changes in the current release
can also be included by specifying `--current`.
