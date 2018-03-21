#!/bin/sh

git submodule update --init --recursive
(cd crun; ./autogen.sh; ./configure CFLAGS='-fPIC' LDFLAGS='-fPIC' --enable-shared --disable-static --with-python-bindings; make -j $(nproc))

