"""Each agent's private runtime environment: its own Docker container, without network access."""

import asyncio
import os
from pathlib import Path


class DockerSandbox:
    def __init__(self, container: str, workspace: Path, cfg: dict, experiment: str):
        self.container = container
        self.workspace = workspace  # host directory mounted as /workspace
        self.cfg = cfg
        self.experiment = experiment

    async def start(self) -> None:
        # Create the workspace ourselves: a directory created by docker would be owned by root.
        self.workspace.mkdir(parents=True, exist_ok=True)
        code, output = await run_command([
            "docker", "run", "-d", "--rm",
            "--name", self.container,
            "--label", f"teamboard.exp={self.experiment}",
            "--user", f"{os.getuid()}:{os.getgid()}",
            "-e", "HOME=/workspace",
            "-v", f"{self.workspace.resolve()}:/workspace",
            "-w", "/workspace",
            *self.cfg["docker_args"],
            self.cfg["image"], "sleep", "infinity",
        ])
        if code != 0:
            raise RuntimeError(f"docker run failed for {self.container}: {output}")

    async def run(self, command: str) -> str:
        timeout = self.cfg["command_timeout"]
        # `timeout` runs inside the container, so a runaway command is really killed there.
        code, output = await run_command(
            ["docker", "exec", self.container, "timeout", "-s", "KILL", str(timeout), "bash", "-lc", command]
        )
        limit = self.cfg["max_output_chars"]
        if len(output) > limit:
            output = output[:limit] + f"\n[... {len(output) - limit} more characters truncated]"
        if code == 137:
            output += f"\n[killed: the command ran longer than {timeout}s]"
        return f"{output}\n[exit code {code}]"

    async def stop(self) -> None:
        await run_command(["docker", "rm", "-f", self.container])


async def run_command(argv: list[str]) -> tuple[int, str]:
    process = await asyncio.create_subprocess_exec(
        *argv, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
    )
    output, _ = await process.communicate()
    return process.returncode, output.decode(errors="replace")
