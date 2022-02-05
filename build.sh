#!/bin/sh
PYTHON_BIN="$(which python3.7 2> /dev/null)"
if [ -z $PYTHON_BIN ]
  PYTHON_BIN="$(which python3.8 2> /dev/null)"
  if [ -z $PYTHON_BIN ]
    PYTHON_BIN="$(which python3 2> /dev/null)"
    if [ -z $PYTHON_BIN ]
      echo "Python 3 not found!"
      exit 1
    then
  then
then
$PYTHON_BIN ./build.py

