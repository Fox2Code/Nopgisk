#!/bin/sh
if [ ! -d ./output ] || [ ! -d ../nopgisk-files/.git ]; then
  echo "Are you a fox?"
  exit 1
fi
for file in app-debug.apk canary.json notes.md sources.zip stub-release.apk; do
  cd -f ./output/$file ../nopgisk-files/$file
done
local ctx="$PWD"
cd ../nopgisk-files
git gui
cd "$ctx"

