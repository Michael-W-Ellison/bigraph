#!/bin/bash
# Build the Linux installers from the PyInstaller folder build:
#   bigraph_<version>_amd64.deb             for Debian and Ubuntu
#   Bigraph-<version>-x86_64.AppImage       one portable file for most distributions
#
# Usage:
#   packaging/linux/build_packages.sh VERSION APP_DIR OUT_DIR APPIMAGETOOL
#     VERSION       for example 1.0.0
#     APP_DIR       the PyInstaller output folder (dist/Bigraph)
#     OUT_DIR       where to write the packages
#     APPIMAGETOOL  path to appimagetool (https://github.com/AppImage/appimagetool)
#
# MAINTAINER (environment) sets the .deb maintainer field.
set -euo pipefail

VERSION="$1"
APP_DIR="$(cd "$2" && pwd)"
OUT_DIR="$(mkdir -p "$3" && cd "$3" && pwd)"
APPIMAGETOOL="$4"
MAINTAINER="${MAINTAINER:-Bigraph project <https://github.com/Michael-W-Ellison/bigraph>}"

HERE="$(cd "$(dirname "$0")" && pwd)"
ICON="$HERE/../icons/bigraph.png"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

desktop_file() {
    # $1: the command the menu entry runs
    cat <<EOF
[Desktop Entry]
Type=Application
Name=Bigraph
Comment=Write and read messages in the Bigraph symbol language
Exec=$1
Icon=bigraph
Terminal=false
Categories=Utility;
EOF
}

# --- .deb ------------------------------------------------------------------
PKG="$WORK/deb"
mkdir -p "$PKG/DEBIAN" "$PKG/opt" "$PKG/usr/bin" "$PKG/usr/share/applications" \
         "$PKG/usr/share/icons/hicolor/256x256/apps"
cp -a "$APP_DIR" "$PKG/opt/bigraph"
ln -s /opt/bigraph/Bigraph "$PKG/usr/bin/bigraph"
desktop_file /opt/bigraph/Bigraph > "$PKG/usr/share/applications/bigraph.desktop"
cp "$ICON" "$PKG/usr/share/icons/hicolor/256x256/apps/bigraph.png"
chmod -R u=rwX,go=rX "$PKG"

cat > "$PKG/DEBIAN/control" <<EOF
Package: bigraph
Version: $VERSION
Section: utils
Priority: optional
Architecture: amd64
Depends: libc6 (>= 2.35)
Suggests: gnome-keyring, kwalletmanager
Installed-Size: $(du -sk "$PKG/opt" | cut -f1)
Maintainer: $MAINTAINER
Description: Bigraph symbol language messaging
 Writes and reads messages in the Bigraph symbol language. Keys and messages
 are kept in encrypted files, with secrets in the desktop key store (GNOME
 Keyring or KWallet), which must be running to save keys and messages.
EOF

dpkg-deb --root-owner-group --build "$PKG" "$OUT_DIR/bigraph_${VERSION}_amd64.deb"

# --- AppImage --------------------------------------------------------------
APPDIR="$WORK/Bigraph.AppDir"
mkdir -p "$APPDIR/usr/lib"
cp -a "$APP_DIR" "$APPDIR/usr/lib/bigraph"
cat > "$APPDIR/AppRun" <<'EOF'
#!/bin/sh
HERE="$(dirname "$(readlink -f "$0")")"
exec "$HERE/usr/lib/bigraph/Bigraph" "$@"
EOF
chmod +x "$APPDIR/AppRun"
desktop_file bigraph > "$APPDIR/bigraph.desktop"
cp "$ICON" "$APPDIR/bigraph.png"

# APPIMAGE_EXTRACT_AND_RUN lets appimagetool run without FUSE (as on build servers)
ARCH=x86_64 APPIMAGE_EXTRACT_AND_RUN=1 "$APPIMAGETOOL" --no-appstream "$APPDIR" \
    "$OUT_DIR/Bigraph-${VERSION}-x86_64.AppImage"

ls -la "$OUT_DIR"
