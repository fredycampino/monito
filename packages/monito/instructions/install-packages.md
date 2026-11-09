## Install Python Packages in Box

You may install Python packages in your own virtual environments under
`/data/workspace`. These environments are persistent. Respect tool permissions
and any explicit approval requirements; do not modify the system Python or
Skiller's environment.

Example:
```bash
python -m venv /data/workspace/.venv-ddgs
/data/workspace/.venv-ddgs/bin/python -m pip install ddgs
```
