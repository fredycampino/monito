# Configurable image tools

Make the utilities installed in each container image explicit and easy to configure.

For Monito's HTTP checks, install `curl` in the image and make the instructions prefer it. Keep Python as a fallback only when `curl` is unavailable.
