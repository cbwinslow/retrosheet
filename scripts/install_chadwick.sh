#!/usr/bin/env bash
set -euo pipefail

version="${CHADWICK_VERSION:-master}"
prefix="${CHADWICK_PREFIX:-$HOME/.local}"
workdir="${TMPDIR:-/tmp}/chadwick-build"

mkdir -p "$workdir"
rm -rf "$workdir/chadwick"

for bin in git autoreconf automake libtoolize make gcc; do
  if ! command -v "$bin" >/dev/null 2>&1; then
    cat <<EOF
Missing required build tool: $bin

On Debian/Ubuntu, install Chadwick build dependencies with:
  sudo apt-get update
  sudo apt-get install -y autoconf automake libtool make gcc g++
EOF
    exit 1
  fi
done

git clone --depth 1 --branch "$version" https://github.com/chadwickbureau/chadwick "$workdir/chadwick"
cd "$workdir/chadwick"

autoreconf --install
./configure --prefix="$prefix"
make
make install

cat <<EOF
Chadwick installed under: $prefix
Add this to PATH if needed:
  export PATH="$prefix/bin:\$PATH"
EOF
