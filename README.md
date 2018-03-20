oci-auto-capabilities
=====================

automatically detect the minimum set of process capabilities required
to run a container.  It uses the Python bindings of the crun OCI
runtime for running the containers.

The program uses a script that is bind mounted inside the container
and launched from there.  The script should cover all the possible use
cases for the container (e.g. try to run the service, serving a
request and then stopping the service).  The script must fail if
something cannot be accomplished with the current set of capabilities.

This is a very simple approach to solve this problem, other approaches
might require a profiling of the container process to see what
actions are performed and must have a full understanding of the
capabilities required for each action.

Example
=====

```bash
# cat my_script.sh
#!/bin/sh
exec ping -c gnu.org

# ./wrapper.sh --test my_script.sh BUNDLE
   [...]
{'bounding': ['CAP_NET_RAW'], 'inheritable': [], 'permitted': [], 'effective': [], 'ambient': []}
Written /tmp/test/config.json.new
```

In the provided example, `my_script.sh` is a script that will be
launched inside the container and BUNDLE is the path to the OCI
container.
Once it completes `oci-auto-capabilities.py` writes a new file
`config.json.new` with the minimum set of capabilities required to run
the container.

