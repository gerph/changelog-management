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

## Usage

For almost all the operations the workflow goes through the management
script `changelogs/cli.py`. This tool takes a command as a parameter
to perform on the changelogs.

### Adding or edit a change

To add a new change to the changelog, use the command:

    changelogs/cli.py edit

This will create a new file based on your branch name, if one does not
already exist, and then launch your editor to edit that file. The file
will have `git add` applied to it if it was updated successfully.

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
