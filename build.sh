#!/bin/sh
PYTHON_BIN="$(which python3.7 2> /dev/null)"
if [ -z $PYTHON_BIN ]; then
  PYTHON_BIN="$(which python3.8 2> /dev/null)"
  if [ -z $PYTHON_BIN ]; then
    PYTHON_BIN="$(which python3 2> /dev/null)"
    if [ -z $PYTHON_BIN ]; then
      echo "Python 3 not found!"
      exit 1
    fi
  fi
fi
$PYTHON_BIN ./build.py

