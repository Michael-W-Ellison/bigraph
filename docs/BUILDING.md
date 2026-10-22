# Building the Apps and Installers

The apps are built with PyInstaller from `packaging/bigraph.spec`, and the
installers are built from the app. PyInstaller builds only for the system it
runs on, so each system's files are built on that system.

## Automatic builds (GitHub Actions)

`.github/workflows/build-apps.yml` builds everything:

- **From the Actions tab:** choose **Build apps**, then **Run workflow**. The
  files appear as downloadable artifacts of the run.
- **With a version tag:** push a tag such as `v1.0.0` to also attach the files
  to a GitHub release for that tag. The tag must match `__version__` in
  `src/bigraph/__init__.py`, or the build stops.
- **To test the release step:** run it from the Actions tab with **Also test
  the release step** checked. The files are attached to a draft release named
  "Test release <run number>", which only people with write access can see.
  No tag is created. Delete the draft on the Releases page afterwards.

Each build runs the tests, builds the app, and runs the built app's self test.
It then builds the installers, installs each one, runs the self test on the
installed app, and uninstalls it again. The self test may report that there
is no OS key store on Linux build servers; that is expected and does not fail
the build.

| Built on | Files |
|---|---|
| Windows | `Bigraph-Setup-<version>-windows-x86_64.exe` (installer), `Bigraph-windows-x86_64-portable.zip` |
| Ubuntu 22.04 | `bigraph_<version>_amd64.deb`, `Bigraph-<version>-x86_64.AppImage`, `Bigraph-linux-x86_64-portable.tar.gz` (for Linux systems with glibc 2.35 or newer) |
| macOS (Apple Silicon) | `Bigraph-macos-arm64.zip` (no installer yet) |

## Building by hand

On the system you are building for, with Python 3.8 or newer and Tkinter:

```bash
pip install -r requirements-dev.txt
pyinstaller packaging/bigraph.spec --distpath dist --workpath build --noconfirm
```

This produces the folder `dist/Bigraph` (with `Bigraph.exe` on Windows and
`Bigraph` on Linux), or `dist/Bigraph.app` on macOS. Check it with:

```bash
packaging/check_self_test.sh dist/Bigraph/Bigraph
```

The self test checks the GUI toolkit, encryption, the packaged key store
support, and whether an OS key store is available. It exits with 0 if
everything works, 2 if only the OS key store is missing, and 1 for any other
problem; `check_self_test.sh` accepts 0 and 2.

### Windows installer

With [Inno Setup 6](https://jrsoftware.org/isinfo.php) installed:

```
"%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" /DAppVersion=1.0.0 /Oout packaging\windows\bigraph.iss
```

The installer installs for the current user by default and offers installing
for all users. Keep the `AppId` in `bigraph.iss` the same in every release, so
new versions upgrade old ones.

### Linux packages

With `dpkg-deb` (Debian or Ubuntu), `desktop-file-utils`, and
[appimagetool](https://github.com/AppImage/appimagetool) 1.9.0:

```bash
packaging/linux/build_packages.sh 1.0.0 dist/Bigraph out path/to/appimagetool
```

The `.deb` installs the app in `/opt/bigraph`, a `bigraph` command, and a menu
entry. Set `MAINTAINER` to put a name and email address in the package.

## Icon

`packaging/icons/bigraph.png` and `bigraph.ico` are drawn by
`packaging/make_icon.py` (needs Pillow): one symbol in the program's own style.
Run it again after changing the design.

## Not covered yet

- **Code signing.** Nothing is signed, so Windows and macOS warn the first
  time an app or installer is run (see `QUICKSTART.md`). With a Windows code
  signing certificate, sign `Bigraph.exe` before building the installer and
  sign the installer afterwards (Inno Setup's `SignTool` setting can do both).
  On macOS, sign with an Apple Developer ID and notarize. Keep certificates in
  repository secrets.
- **macOS installer.** The macOS build is a zipped app; a `.dmg` is not built
  yet. It is for Apple Silicon only.
- **Other formats and architectures.** No `.rpm`, Flatpak or Snap, and no ARM
  builds.
