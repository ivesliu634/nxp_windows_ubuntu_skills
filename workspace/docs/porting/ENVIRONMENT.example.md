# Machine-specific environment

Review the published configuration in `workspace\local\ENVIRONMENT.md` against this
template on each Windows machine. Copy this file there only when no configuration exists;
do not overwrite an existing configuration without reviewing or backing it up.
Windows relative paths are based on `workspace`, not `workspace\local`.
Use absolute Linux paths for server resources and expand placeholders before use.
Non-sensitive machine-specific values may be committed; keep concrete machine values
here rather than in abstract workflow rules.
An optional `workspace\local\ENVIRONMENT.private.md` may supplement private machine values;
it is ignored by Git. State its path base explicitly.
Keep passwords, tokens and SSH private keys in approved credential storage, not these files.

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
These fields are resource records, not automatic SSH, installation or build configuration.
Changing this file does not update project profiles or checklists.

## Verification scope

Mark missing resources as not installed or not confirmed. Record verification dates when known;
existing paths and historical checks are not proof of current availability.
Current board identity and state belong in case records and require fresh probes.
