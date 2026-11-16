# Machine-specific environment

Copy this template to `workspace/ENVIRONMENT.md` on each Windows machine.
Use paths relative to the workspace root where possible. Do not commit the completed file.
Keep passwords, tokens and SSH private keys in approved credential storage, not this template.

## Windows

| Resource | Location |
|---|---|
| Workspace | Directory containing AGENTS.md |
| Workflow repository | Windows directory containing `workspace`, `support_level` and `server` |
| Server deployment source | `..\server\support_level` (small tools and rules only; not a local build environment) |
| RM / schematics | `..\support_level\SoC_material` |
| BSP documents | `..\support_level\linux_document` |
| Image storage | `<actual Windows image root>` |
| BCU | `..\support_level\tools\bcu\bin\bcu.exe` |
| Serial console | `..\support_level\tools\serial-console\scripts\serial_console.py` |
| UUU | `..\support_level\tools\uuu\uuu.exe` |
| Python | `<selected Python executable>` |
| Complete cases | `..\support_level\work\<case>` |

## Ubuntu server

| Resource | Location |
|---|---|
| SSH alias | `myserver` |
| Resource root | `<absolute Linux support_level path>` |
| Execution root | `<absolute Linux resource/execution root; not an AI workspace>` |
| Source assets | `<server code_assets or existing source path>` |
| SDK / release packages | `<server path>` |
| Toolchains / fixed firmware | `<server paths>` |
| Zephyr SDK | `<verified server path and supported targets, or not confirmed>` |
| Compile tool | `<verified server path, or not deployed>` |
| Release validator | `<server support_level>/tools/build-customer-release/scripts/validate_release.py` |
| Case execution root | `<server work path>/<same-case-name>` |

AI and skills run only on Windows. The server does not need this workflow's Git
repository, an AI entrypoint, skills directories, or its own ENVIRONMENT.md.

## Observed hardware

Record only current observations with dates. Historical profiles are not proof of a connected board.
