#!/bin/sh
set -eu
TARGET_DIR=${1:?}
cat > "$TARGET_DIR/etc/os-release" <<'EOF'
NAME="Znlite Linux"
PRETTY_NAME="Znlite Linux 0.1"
ID=znlite
VERSION_ID=0.1
VERSION_CODENAME=prototype
EOF
printf '%s\n' 'Znlite Linux 0.1 live system' > "$TARGET_DIR/etc/issue"
