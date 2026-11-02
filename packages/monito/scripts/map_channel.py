"""Label local tasks while preserving Telegram channel envelopes."""

import os
import sys


def map_channel(task: str) -> str:
    if task.startswith("[Channel][Telegram]\n"):
        return task
    return "[Channel][input]\n" + task


if __name__ == "__main__":
    sys.stdout.write(map_channel(os.environ["TASK"]))
