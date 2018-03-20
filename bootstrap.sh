#!/bin/sh

git submodule update --init --recursive
(cd crun; ./autogen.sh; ./configure CFLAGS='-fPIC' LDFLAGS='-fPIC' --with-python-bindings; make -j $(nproc))

