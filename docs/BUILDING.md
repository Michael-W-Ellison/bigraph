# Building the Standalone Apps

The apps are built with PyInstaller from `packaging/bigraph.spec`. PyInstaller
builds only for the system it runs on, so each app is built on its own system.

## Automatic builds (GitHub Actions)

`.github/workflows/build-apps.yml` builds all three apps:

- **From the Actions tab:** choose **Build apps**, then **Run workflow**. The
  apps appear as downloadable artifacts of the run.
- **With a version tag:** pushing a tag such as `v1.0.0` builds the apps and
  attaches them to a GitHub release for that tag.

Each build runs the tests, builds the app, and runs the built app's self test.
The self test may report that there is no OS key store on Linux build servers;
that is expected and does not fail the build.

| Built on | File |
|---|---|
| Ubuntu 22.04 | `Bigraph-linux-x86_64.tar.gz` (runs on Linux systems with glibc 2.35 or newer) |
| Windows | `Bigraph-windows-x86_64.zip` |
| macOS (Apple Silicon) | `Bigraph-macos-arm64.zip` (Apple Silicon Macs only) |

## Building by hand

On the system you are building for, with Python 3.8 or newer and Tkinter:

```bash
pip install -r requirements-dev.txt
pyinstaller packaging/bigraph.spec --distpath dist --workpath build --noconfirm
```

This produces `dist/Bigraph` (Linux), `dist/Bigraph.exe` (Windows), or
`dist/Bigraph.app` (macOS). Check it with:

```bash
dist/Bigraph --self-test
```

The self test checks the GUI toolkit, encryption, the packaged key store
support, and whether an OS key store is available. It exits with 0 if
everything works, 2 if only the OS key store is missing, and 1 for any other
problem. Windowed apps on Windows print nothing, so use
`--self-test-report report.txt` there.

## Not covered

- **Code signing.** The apps are unsigned, so Windows and macOS warn the first
  time they are opened (see `QUICKSTART.md`). Signing needs a Windows code
  signing certificate and an Apple Developer ID, with macOS notarization.
- **Intel Macs.** The macOS build is for Apple Silicon. An Intel build needs an
  Intel macOS runner, or a universal2 Python to build a universal app.
- **ARM Linux and Windows on ARM.** Not built.
