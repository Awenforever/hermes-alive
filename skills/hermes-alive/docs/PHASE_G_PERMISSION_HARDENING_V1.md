# Phase G lifecycle permission hardening V1

Marker: `HERMES_ALIVE_LIFECYCLE_PERMISSION_HARDENING_V1`

Lifecycle-owned metadata directories are created with explicit permissions,
independent of the container umask:

- shared runtime root: `0755`;
- install metadata and backup roots: `0700`;
- managed configuration directory: `0700`;
- rollback source/hook container directories: `0700`;
- JSON configuration and manifest files: `0600`.

Existing learning/runtime subtrees are not recursively chmodded.
