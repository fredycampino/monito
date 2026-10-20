# Skiller server startup in Box

## Status: done

Closed by scope decision: the container entrypoint starts the Skiller HTTP
server on each container start and restart before executing the main command.
Startup failures exit nonzero so Docker can apply its restart policy.

Implemented in `docker/monito-entrypoint.sh` and covered by
`packages/monito/tests/test_deployment.py`.

## Out of scope

Continuous supervision and graceful shutdown of the background server are not
implemented and are outside this task's scope. Docker's restart policy does not
restart an individual background process while the main process remains alive.
Persisted waiting listeners do not imply HTTP health.
