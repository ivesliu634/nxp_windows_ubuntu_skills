from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import io
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import yaml

from compile_tool import checklists, composition, profiles
from compile_tool.cli import main
from compile_tool.common import ToolError, hash_data
from compile_tool.common import hash_file
from compile_tool.state import load_state
from compile_tool.manifest import load_manifest


def write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def run_git(cwd: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    return result.stdout.strip()


class ChecklistFixture:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.support = root / "support_level"
        self.projects = self.support / "code_assets" / "projects"
        self.case_root = self.support / "work" / "checklist-case"
        self.case_root.mkdir(parents=True)
        self.compiler = self.support / "tools" / "arm-none-eabi-gcc"
        self.compiler.parent.mkdir(parents=True)
        self.compiler.write_text("#!/bin/sh\nprintf 'fixture compiler 1.0\\n'\n")
        self.compiler.chmod(0o755)
        self.fixed = self.case_root / "inputs" / "fixed.bin"
        self.fixed.parent.mkdir(parents=True)
        self.fixed.write_text("fixed-v1\n")
        self._create_oei_project()
        self._create_mkimage_project()

    def patches(self):
        return (
            patch.object(profiles, "PROJECTS_ROOT", self.projects),
            patch.object(checklists, "PROJECTS_ROOT", self.projects),
        )

    def _source_repo(self, project: str, makefile: str) -> Path:
        source = self.projects / project / "source"
        source.mkdir(parents=True)
        run_git(source, "init")
        run_git(source, "config", "user.email", "fixture@example.com")
        run_git(source, "config", "user.name", "Fixture")
        (source / "Makefile").write_text(makefile)
        run_git(source, "add", "Makefile")
        run_git(source, "commit", "-m", "initial")
        run_git(source, "tag", "release-v1")
        run_git(source, "remote", "add", "origin", f"https://fixture.invalid/{project}")
        return source

    @staticmethod
    def _profile(project: str, *, action: str, output_type: str, output_path: str) -> dict:
        return {
            "schema_version": 1,
            "id": project,
            "type": "project_compile",
            "target": project,
            "component": project,
            "action": action,
            "source": {
                "id": project,
                "path": "source",
                "case_path": f"sources/{project}",
                "ref_kind": "tag",
                "remote": "origin",
                "remote_url": f"https://fixture.invalid/{project}",
                "update": "if_missing",
            },
            "parameters": {},
            "configuration_parameters": [],
            "tools": [
                {
                    "name": "make",
                    "path": "/usr/bin/make",
                    "version_args": ["--version"],
                },
                {
                    "name": "compiler",
                    "path": "tools/arm-none-eabi-gcc",
                    "version_args": [],
                }
            ],
            "watched_inputs": [],
            "outputs": {
                "oei_ddr" if project == "imx-oei" else "flashbin": {
                    "type": output_type,
                    "path": output_path,
                    "identity_parameters": ["silicon_revision"],
                }
            },
            "artifact_inputs": {},
            "file_inputs": {},
        }

    def _create_oei_project(self) -> None:
        self._source_repo(
            "imx-oei",
            "all:\n\tmkdir -p build/$(board)/$(oei)\n"
            "\tprintf 'oei-%s-%s\\n' '$(REV)' '$(board)' > "
            "build/$(board)/$(oei)/oei-m33-ddr.bin\n",
        )
        profile = self._profile(
            "imx-oei",
            action="rebuild",
            output_type="nxp.oei.ddr-image",
            output_path="artifacts/imx-oei/oei-m33-ddr.bin",
        )
        profile["parameters"] = {
            "silicon_revision": {"source": "user", "required": True},
            "board": {"source": "user", "required": True},
            "oei_type": {"source": "project", "default": "ddr"},
        }
        profile["configuration_parameters"] = ["silicon_revision", "board", "oei_type"]
        profile["checklist_build"] = {
            "mode": "isolated_git",
            "env": {"OEI_CROSS_COMPILE": "${tool_prefix.compiler}"},
            "steps": [
                {
                    "name": "build-imx-oei",
                    "command": [
                        "${tools.make}",
                        "REV=${parameters.silicon_revision}",
                        "R=${parameters.silicon_revision}",
                        "board=${parameters.board}",
                        "oei=${parameters.oei_type}",
                    ],
                }
            ],
        }
        template = {
            "schema_version": 1,
            "kind": "project_compile_checklist",
            "project": "imx-oei",
            "case_root": "TBD",
            "source": {"ref": "TBD"},
            "parameters": {"silicon_revision": "TBD", "board": "TBD", "oei_type": "ddr"},
            "inputs": {"artifacts": [], "files": []},
            "toolchain": {"make": "/usr/bin/make", "compiler": "tools/arm-none-eabi-gcc"},
            "intent": {"action": "rebuild", "reason": "TBD"},
            "build": {"mode": "isolated_git"},
            "outputs": {
                "oei_ddr": {
                    "type": "nxp.oei.ddr-image",
                    "collect_from": "build/${parameters.board}/${parameters.oei_type}/oei-m33-ddr.bin",
                    "publish_to": "artifacts/imx-oei/oei-m33-ddr.bin",
                }
            },
        }
        write_yaml(self.projects / "imx-oei" / "COMPILE_PROFILE.yaml", profile)
        write_yaml(self.projects / "imx-oei" / "COMPILE_CHECKLIST.yaml", template)

    def _create_mkimage_project(self) -> None:
        self._source_repo(
            "imx-mkimage",
            "all:\n\tmkdir -p $(SOC)\n"
            "\tcat inputs/oei.bin inputs/fixed.bin > $(SOC)/flash.bin\n",
        )
        profile = self._profile(
            "imx-mkimage",
            action="repack",
            output_type="nxp.boot.flashbin",
            output_path="artifacts/imx-mkimage/flash.bin",
        )
        profile["parameters"] = {
            "silicon_revision": {"source": "user", "required": True},
            "soc": {"source": "user", "required": True},
            "recipe": {"source": "user", "required": True},
            "lpddr_type": {"source": "user", "required": True},
            "oei_enabled": {"source": "project", "default": "NO"},
        }
        profile["configuration_parameters"] = list(profile["parameters"])
        profile["artifact_inputs"] = {
            "oei": {
                "type": "nxp.oei.ddr-image",
                "multiple": False,
                "required_when": {"parameter": "oei_enabled", "equals": "YES"},
                "parameter_matches": {"silicon_revision": "silicon_revision"},
            }
        }
        profile["file_inputs"] = {
            "firmware": {"multiple": True},
            "m_payload": {"multiple": True},
        }
        profile["checklist_build"] = {
            "mode": "isolated_git",
            "env": {},
            "steps": [
                {
                    "name": "build-imx-mkimage",
                    "command": [
                        "${tools.make}",
                        "SOC=${parameters.soc}",
                        "REV=${parameters.silicon_revision}",
                        "OEI=${parameters.oei_enabled}",
                        "LPDDR_TYPE=${parameters.lpddr_type}",
                        "${parameters.recipe}",
                    ],
                }
            ],
        }
        template = {
            "schema_version": 1,
            "kind": "project_compile_checklist",
            "project": "imx-mkimage",
            "case_root": "TBD",
            "source": {"ref": "TBD"},
            "parameters": {
                "silicon_revision": "TBD",
                "soc": "TBD",
                "recipe": "TBD",
                "lpddr_type": "TBD",
                "oei_enabled": "TBD",
            },
            "inputs": {"artifacts": [], "files": []},
            "toolchain": {"make": "/usr/bin/make", "compiler": "tools/arm-none-eabi-gcc"},
            "intent": {"action": "repack", "reason": "TBD"},
            "build": {"mode": "isolated_git"},
            "outputs": {
                "flashbin": {
                    "type": "nxp.boot.flashbin",
                    "collect_from": "${parameters.soc}/flash.bin",
                    "publish_to": "artifacts/imx-mkimage/flash.bin",
                }
            },
        }
        write_yaml(self.projects / "imx-mkimage" / "COMPILE_PROFILE.yaml", profile)
        write_yaml(self.projects / "imx-mkimage" / "COMPILE_CHECKLIST.yaml", template)

    def oei_checklist(self, *, action: str = "rebuild") -> Path:
        data = yaml.safe_load((self.projects / "imx-oei" / "COMPILE_CHECKLIST.yaml").read_text())
        data["case_root"] = str(self.case_root)
        data["source"]["ref"] = "release-v1"
        data["parameters"].update({"silicon_revision": "B0", "board": "mx95lp5"})
        data["intent"] = {"action": action, "reason": "fixture OEI build"}
        path = self.case_root / "records" / "compile" / "imx-oei" / "compile.yaml"
        write_yaml(path, data)
        return path

    def mkimage_checklist(self, *, payload: Path | None = None) -> Path:
        data = yaml.safe_load((self.projects / "imx-mkimage" / "COMPILE_CHECKLIST.yaml").read_text())
        data["case_root"] = str(self.case_root)
        data["source"]["ref"] = "release-v1"
        data["parameters"].update(
            {
                "silicon_revision": "B0",
                "soc": "fixture-soc",
                "recipe": "all",
                "lpddr_type": "lpddr5",
                "oei_enabled": "YES",
            }
        )
        data["inputs"] = {
            "artifacts": [
                {
                    "name": "oei",
                    "slot": "oei",
                    "checklist": "records/compile/imx-oei/compile.yaml",
                    "artifact": "oei_ddr",
                    "stage_to": "inputs/oei.bin",
                }
            ],
            "files": [
                {
                    "name": "fixed",
                    "slot": "firmware",
                    "path": "inputs/fixed.bin",
                    "stage_to": "inputs/fixed.bin",
                }
            ],
        }
        if payload is not None:
            data["inputs"]["files"].append(
                {
                    "name": "m7",
                    "slot": "m_payload",
                    "path": str(payload.relative_to(self.case_root)),
                    "stage_to": "inputs/m7.bin",
                }
            )
        data["intent"] = {"action": "repack", "reason": "fixture mkimage pack"}
        path = self.case_root / "records" / "compile" / "imx-mkimage" / "compile.yaml"
        write_yaml(path, data)
        return path


class ChecklistWorkflowTests(unittest.TestCase):
    def test_source_defined_custom_recipe_runs_with_unlisted_release_inputs(self) -> None:
        profile = yaml.safe_load(
            (profiles.PROJECTS_ROOT / "imx-mkimage/COMPILE_PROFILE.yaml").read_text()
        )
        template = yaml.safe_load(
            (profiles.PROJECTS_ROOT / "imx-mkimage/COMPILE_CHECKLIST.yaml").read_text()
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = ChecklistFixture(Path(temp_dir))
            project = fixture.projects / "imx-mkimage"
            original_profile = yaml.safe_load((project / "COMPILE_PROFILE.yaml").read_text())
            profile["source"] = original_profile["source"]
            profile["tools"] = original_profile["tools"]
            write_yaml(project / "COMPILE_PROFILE.yaml", profile)
            template["toolchain"] = {
                tool["name"]: tool["path"] for tool in profile["tools"]
            }
            write_yaml(project / "COMPILE_CHECKLIST.yaml", template)
            source = project / "source"
            (source / "Makefile").write_text("include $(SOC)/soc.mak\n")
            soc_makefile = source / "fixture_soc/soc.mak"
            soc_makefile.parent.mkdir()
            soc_makefile.write_text(
                "custom_boot:\n\tmkdir -p $(SOC)\n"
                "\tcat inputs/firmware.bin > $(SOC)/flash.bin\n"
            )
            run_git(source, "add", ".")
            run_git(source, "commit", "-m", "custom source recipe")
            run_git(source, "tag", "release-custom")
            soc_makefile.write_text("different_target:\n\ttrue\n")
            run_git(source, "add", ".")
            run_git(source, "commit", "-m", "different current checkout")
            data = yaml.safe_load((project / "COMPILE_CHECKLIST.yaml").read_text())
            data["case_root"] = str(fixture.case_root)
            data["source"]["ref"] = "release-custom"
            data["parameters"].update({
                "silicon_revision": "C0", "soc": "fixture_soc",
                "recipe": "custom_boot", "lpddr_type": "new_ddr", "oei_enabled": "NO",
            })
            data["intent"]["reason"] = "use the selected source ref, not historical recipe lists"
            data["inputs"]["files"] = [{
                "name": "new_firmware", "slot": "firmware",
                "path": str(fixture.fixed.relative_to(fixture.case_root)),
                "stage_to": "inputs/firmware.bin",
                "provenance": "synthetic release-custom package; source recipe reviewed",
            }]
            path = fixture.case_root / "records/compile/imx-mkimage/compile.yaml"
            write_yaml(path, data)
            first_patch, second_patch = fixture.patches()
            with first_patch, second_patch:
                report = io.StringIO()
                with redirect_stdout(report):
                    self.assertEqual(main(["prepare", str(path)]), 0)
                    self.assertEqual(main(["run", str(path)]), 0)
                self.assertIn("synthetic release-custom package", report.getvalue())
                self.assertIn(hash_file(fixture.fixed), report.getvalue())
                output = fixture.case_root / "artifacts/imx-mkimage/flash.bin"
                self.assertEqual(output.read_bytes(), fixture.fixed.read_bytes())

    def test_oei_single_checklist_prepare_run_and_reuse(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = ChecklistFixture(Path(temp_dir))
            first_patch, second_patch = fixture.patches()
            with first_patch, second_patch:
                checklist = fixture.oei_checklist()
                prepared = io.StringIO()
                with redirect_stdout(prepared):
                    self.assertEqual(main(["prepare", str(checklist)]), 0)
                self.assertIn("ACQUIRE_REQUIRED", prepared.getvalue())
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(main(["run", str(checklist)]), 0)
                output = fixture.case_root / "artifacts" / "imx-oei" / "oei-m33-ddr.bin"
                self.assertEqual(output.read_text(), "oei-B0-mx95lp5\n")
                self.assertEqual(
                    main(["prepare", str(checklist.parent / ".compile-tool-request.yaml")]),
                    2,
                )

                checklist = fixture.oei_checklist(action="reuse")
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(main(["prepare", str(checklist)]), 0)
                    self.assertEqual(main(["run", str(checklist)]), 0)
                manifest = load_manifest(checklist.parent / "manifest.yaml")
                self.assertIn("imx-oei", load_state(manifest)["_root_state"]["targets"])

    def test_command_mismatch_and_mkimage_artifact_flow(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = ChecklistFixture(Path(temp_dir))
            first_patch, second_patch = fixture.patches()
            with first_patch, second_patch:
                bad = fixture.oei_checklist()
                data = yaml.safe_load(bad.read_text())
                data["build"]["command"] = "make REV=A0"
                write_yaml(bad, data)
                with self.assertRaisesRegex(ToolError, "build.*exactly match"):
                    checklists.normalize_checklist(bad)

                oei = fixture.oei_checklist()
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(main(["prepare", str(oei)]), 0)
                    self.assertEqual(main(["run", str(oei)]), 0)
                mkimage = fixture.mkimage_checklist()
                prepared = io.StringIO()
                with redirect_stdout(prepared):
                    self.assertEqual(main(["prepare", str(mkimage)]), 0)
                self.assertIn("stage-oei", prepared.getvalue())
                self.assertIn("stage-fixed", prepared.getvalue())
                fixed = fixture.case_root / "inputs/fixed.bin"
                fixed.write_text("changed after prepare\n")
                with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    self.assertEqual(main(["run", str(mkimage)]), 2)
                fixed.write_text("fixed-v1\n")
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(main(["prepare", str(mkimage)]), 0)
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(main(["run", str(mkimage)]), 0)
                flashbin = fixture.case_root / "artifacts" / "imx-mkimage" / "flash.bin"
                self.assertEqual(flashbin.read_text(), "oei-B0-mx95lp5\nfixed-v1\n")

                payload = fixture.case_root / "inputs" / "m7.bin"
                payload.write_text("m7-v1\n")
                mkimage = fixture.mkimage_checklist(payload=payload)
                payload_plan = io.StringIO()
                with redirect_stdout(payload_plan):
                    self.assertEqual(main(["prepare", str(mkimage)]), 0)
                self.assertIn("stage-m7", payload_plan.getvalue())
                self.assertIn("CHANGES_OBSERVED", payload_plan.getvalue())
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(main(["run", str(mkimage)]), 0)

                (fixture.case_root / "artifacts" / "imx-oei" / "oei-m33-ddr.bin").write_text("tampered\n")
                with self.assertRaisesRegex(ToolError, "differs from its producer"):
                    checklists.prepare_checklist(mkimage)


class ProjectContractFixture:
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.support = Path(temporary.name) / "support_level"
        self.projects = self.support / "code_assets/projects"
        original_support = profiles.SUPPORT_LEVEL
        for path in (original_support / "code_assets/projects").glob("*/*.yaml"):
            destination = self.support / path.relative_to(original_support)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, destination)
            if path.name == "COMPILE_PROFILE.yaml":
                profile = yaml.safe_load(path.read_text(encoding="utf-8"))
                (destination.parent / profile["source"]["path"]).mkdir(parents=True, exist_ok=True)
        for path in (original_support / "compile_targets").rglob("*.yaml"):
            destination = self.support / path.relative_to(original_support)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, destination)
        self.asset_paths = {}
        matrix_path = self.support / "compile_targets/flashbin/FIXED_ASSETS.yaml"
        matrix = yaml.safe_load(matrix_path.read_text(encoding="utf-8"))
        self.asset_selectors = matrix["selectors"]

        def materialize(node: dict, selection: tuple = ()) -> None:
            if "files" not in node:
                for name, child in node.items():
                    materialize(child, (*selection, str(name)))
                return
            for role, definition in node["files"].items():
                for recipe, variant in [(None, definition), *definition.get("by_recipe", {}).items()]:
                    filename = f"{recipe or 'default'}-{Path(definition['stage_to']).name}"
                    asset = self.support / "test-assets" / Path(*selection) / filename
                    asset.parent.mkdir(parents=True, exist_ok=True)
                    asset.write_bytes(f"synthetic asset {selection} {role} {recipe}\n".encode())
                    variant["sha256"] = hash_file(asset)
                    self.asset_paths[(*selection, recipe, role)] = asset

        materialize(matrix["assets"])
        write_yaml(matrix_path, matrix)
        sources = {
            "iMX94": "MCU_IMG = m33_image.bin\nM33S_IMG = m33s_image.bin\nM70_IMG = m70_image.bin\nM71_IMG = m71_image.bin\nflash_a55: $(MCU_IMG) u-boot-atf-container.img\nflash_all: $(MCU_IMG) $(M33S_IMG) $(M70_IMG) $(M71_IMG) u-boot-atf-container.img\nflash_all_no_m7: $(MCU_IMG) $(M33S_IMG) u-boot-atf-container.img\n",
            "iMX95": "MCU_IMG = m33_image.bin\nM7_IMG = m7_image.bin\nflash_a55: $(MCU_IMG) u-boot-atf-container.img\nflash_all: $(MCU_IMG) $(M7_IMG) u-boot-atf-container.img\n",
            "iMX8DXL": "flash_linux_m4: m4_image.bin\n",
            "iMX8QM": "flash_linux_m4: m4_1_image.bin m4_image.bin\n",
        }
        for soc, text in sources.items():
            path = self.projects / "imx-mkimage/imx-mkimage" / soc / "soc.mak"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        for module, name, value in [
            (profiles, "SUPPORT_LEVEL", self.support),
            (profiles, "PROJECTS_ROOT", self.projects),
            (checklists, "PROJECTS_ROOT", self.projects),
        ]:
            patcher = patch.object(module, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def _fixed_asset(self, parameters: dict[str, str], role: str) -> Path:
        selection = tuple(parameters[name] for name in self.asset_selectors)
        variant = (*selection, parameters.get("recipe"), role)
        return self.asset_paths.get(variant) or self.asset_paths[(*selection, None, role)]


class ProjectChecklistRuleTests(ProjectContractFixture, unittest.TestCase):
    def test_fixed_asset_recipe_variant_rejects_mixed_versions(self) -> None:
        import hashlib

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            asset = root / "ahab.img"
            old_content = b"old-pinned-ahab"
            new_content = b"rte35-pinned-ahab"
            matrix = {
                "schema_version": 1,
                "kind": "project_fixed_asset_matrix",
                "selectors": ["soc"],
                "assets": {"iMX94": {
                    "owned_slots": ["ahab"],
                    "files": {"ahab": {
                        "slot": "ahab", "stage_to": "iMX94/ahab.img",
                        "sha256": hashlib.sha256(old_content).hexdigest(),
                        "provenance": "old-package/ahab.img",
                        "by_recipe": {"flash_all_no_m7": {
                            "sha256": hashlib.sha256(new_content).hexdigest(),
                            "provenance": "rte35-package/ahab.img",
                        }},
                    }},
                }},
            }
            path = root / "fixed.yaml"
            write_yaml(path, matrix)
            reference = {"path": str(path), "hash": hash_data(matrix), "selectors": ["soc"]}
            inputs = {"files": [{"name": "ahab", "slot": "ahab", "path": str(asset), "stage_to": "iMX94/ahab.img"}]}
            for recipe, accepted, rejected in (
                ("flash_all", old_content, new_content),
                ("flash_all_no_m7", new_content, old_content),
            ):
                with self.subTest(recipe=recipe):
                    parameters = {"soc": "iMX94", "recipe": recipe}
                    asset.write_bytes(accepted)
                    composition.validate_fixed_asset_contract(reference, parameters, inputs)
                    asset.write_bytes(rejected)
                    with self.assertRaisesRegex(ToolError, "content hash does not match"):
                        composition.validate_fixed_asset_contract(reference, parameters, inputs)

    def test_imx94_no_m7_contract_preserves_boot_chain(self) -> None:
        matrix = yaml.safe_load(
            (profiles.SUPPORT_LEVEL / "compile_targets/flashbin/RECIPE_CONTRACTS.yaml").read_text(encoding="utf-8")
        )
        recipes = matrix["recipes"]["iMX94"]
        self.assertEqual(recipes["flash_all_no_m7"], recipes["flash_all"])
        makefile = """MCU_IMG = m33_image.bin
M33S_IMG = m33s_image.bin
M70_IMG = m70_image.bin
M71_IMG = m71_image.bin
flash_all_no_m7: $(MCU_IMG) $(M33S_IMG) u-boot-atf-container.img
"""
        self.assertEqual(
            composition.make_recipe_m_images(makefile, "flash_all_no_m7"),
            ["m33_image.bin", "m33s_image.bin"],
        )

    def test_soc_mak_parser_handles_synthetic_multi_soc_dependencies(self) -> None:
        source = profiles.PROJECTS_ROOT / "imx-mkimage" / "imx-mkimage"
        cases = {
            ("iMX94", "flash_all"): [
                "m33_image.bin",
                "m33s_image.bin",
                "m70_image.bin",
                "m71_image.bin",
            ],
            ("iMX95", "flash_all"): ["m33_image.bin", "m7_image.bin"],
            ("iMX94", "flash_all_no_m7"): ["m33_image.bin", "m33s_image.bin"],
            ("iMX8DXL", "flash_linux_m4"): ["m4_image.bin"],
            ("iMX8QM", "flash_linux_m4"): ["m4_1_image.bin", "m4_image.bin"],
        }
        for (soc, recipe), expected in cases.items():
            text = (source / soc / "soc.mak").read_text(encoding="utf-8")
            self.assertEqual(composition.make_recipe_m_images(text, recipe), expected)

    def _prepare(
        self,
        case_root: Path,
        project: str,
        parameters: dict[str, str],
    ) -> str:
        profile_path = profiles.PROJECTS_ROOT / project / "COMPILE_PROFILE.yaml"
        profile = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
        canonical = profile_path.parent / profile["source"]["path"]
        run_git(canonical, "init")
        run_git(canonical, "config", "user.email", "fixture@example.com")
        run_git(canonical, "config", "user.name", "Fixture")
        (canonical / "fixture.txt").write_text("synthetic command-generation source\n")
        run_git(canonical, "add", "fixture.txt")
        run_git(canonical, "commit", "-m", "fixture")
        run_git(canonical, "tag", "lf-6.18.2-1.0.0")
        run_git(canonical, "remote", "add", "origin", profile["source"]["remote_url"])
        template_path = profiles.PROJECTS_ROOT / project / "COMPILE_CHECKLIST.yaml"
        data = yaml.safe_load(template_path.read_text(encoding="utf-8"))
        data["case_root"] = str(case_root)
        data["source"]["ref"] = "lf-6.18.2-1.0.0"
        data["parameters"].update(parameters)
        data["intent"]["reason"] = f"verify {project} checklist contract"
        path = case_root / "records" / "compile" / project / "compile.yaml"
        write_yaml(path, data)
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(["prepare", str(path)]), 0)
        return output.getvalue()

    def test_atf_uboot_optee_and_smfw_commands_are_profile_generated(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            atf_case = root / "atf-case"
            atf_case.mkdir()
            atf = self._prepare(
                atf_case,
                "imx-atf",
                {"platform": "imx95", "spd": "opteed"},
            )
            self.assertIn("PLAT=imx95 SPD=opteed bl31", atf)
            self.assertIn("-u LDFLAGS -u AS", atf)

            uboot_case = root / "uboot-case"
            uboot_case.mkdir()
            uboot = self._prepare(
                uboot_case,
                "uboot-imx",
                {"defconfig": "imx95_19x19_evk_defconfig"},
            )
            self.assertIn("configure-uboot-imx", uboot)
            self.assertIn("O=build imx95_19x19_evk_defconfig", uboot)
            self.assertIn("build-uboot-imx", uboot)
            self.assertIn("-j8", uboot)

            optee_case = root / "optee-case"
            optee_case.mkdir()
            optee = self._prepare(
                optee_case,
                "imx-optee-os",
                {"platform_flavor": "mx95evk"},
            )
            self.assertIn("PLATFORM=imx PLATFORM_FLAVOR=mx95evk", optee)
            self.assertIn("CROSS_COMPILE64=", optee)

            smfw_case = root / "smfw-case"
            smfw_case.mkdir()
            smfw = self._prepare(
                smfw_case,
                "imx-sm",
                {"config": "other/mx95rte"},
            )
            self.assertIn("/usr/bin/rm -rf configs/other/mx95rte", smfw)
            self.assertLess(smfw.index("remove-generated-smfw-config"), smfw.index("really-clean-imx-sm"))
            self.assertLess(smfw.index("really-clean-imx-sm"), smfw.index("configure-imx-sm"))
            self.assertLess(smfw.index("configure-imx-sm"), smfw.index("build-imx-sm"))

    def test_profile_parameter_allowlist_blocks_invalid_platform(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            case_root = Path(temp_dir) / "bad-atf-case"
            case_root.mkdir()
            template_path = profiles.PROJECTS_ROOT / "imx-atf" / "COMPILE_CHECKLIST.yaml"
            data = yaml.safe_load(template_path.read_text(encoding="utf-8"))
            data["case_root"] = str(case_root)
            data["source"]["ref"] = "lf-6.18.2-1.0.0"
            data["parameters"].update({"platform": "imx93", "spd": "none"})
            data["intent"]["reason"] = "verify invalid platform is blocked"
            path = case_root / "records" / "compile" / "imx-atf" / "compile.yaml"
            write_yaml(path, data)
            with self.assertRaisesRegex(ToolError, "must be one of"):
                checklists.prepare_checklist(path)

    def _mkimage_draft(self, case_root: Path, *, parameters: dict[str, str]) -> Path:
        template = profiles.PROJECTS_ROOT / "imx-mkimage" / "COMPILE_CHECKLIST.yaml"
        data = yaml.safe_load(template.read_text(encoding="utf-8"))
        data["case_root"] = str(case_root)
        data["source"]["ref"] = "lf-6.18.2-1.0.0"
        data["parameters"].update(parameters)
        data["intent"]["reason"] = "verify recipe input contract"
        path = case_root / "records" / "compile" / "imx-mkimage" / "compile.yaml"
        write_yaml(path, data)
        return path

    def test_mkimage_checks_source_recipe_instead_of_historical_combinations(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            case_root = Path(temp_dir) / "mkimage-contract-case"
            case_root.mkdir()
            parameters = {"soc": "iMX95", "silicon_revision": "B0", "lpddr_type": "lpddr5", "oei_enabled": "NO", "recipe": "flash_a55"}
            path = self._mkimage_draft(case_root, parameters=parameters)
            with self.assertRaisesRegex(ToolError, "requires M payloads"):
                checklists.normalize_checklist(path)

            path = self._mkimage_draft(case_root, parameters={**parameters, "recipe": "flash_kernel"})
            with self.assertRaisesRegex(ToolError, "soc.mak does not define recipe target"):
                checklists.normalize_checklist(path)

            source = self.projects / "imx-mkimage/imx-mkimage/iMX8QM/soc.mak"
            with source.open("a", encoding="utf-8") as handle:
                handle.write("custom_boot:\n")
            path = self._mkimage_draft(case_root, parameters={
                **parameters, "soc": "iMX8QM", "recipe": "custom_boot",
                "silicon_revision": "C0", "lpddr_type": "ddr4",
            })
            firmware = case_root / "new-release.bin"
            firmware.write_bytes(b"synthetic new release")
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            data["inputs"]["files"] = [{
                "name": "new_release", "slot": "firmware", "path": firmware.name,
                "stage_to": "iMX8QM/new-release.bin",
                "provenance": "synthetic release C0; source reviewed for custom_boot",
            }]
            write_yaml(path, data)
            normalized = checklists.normalize_checklist(path)
            self.assertEqual(normalized["parameters"]["recipe"], "custom_boot")
            self.assertEqual(normalized["make_recipe"]["required_m_payloads"], {})
            self.assertIsNone(normalized["profile"]["fixed_asset_contract"])

    def _producer_stub(
        self,
        case_root: Path,
        project: str,
        parameters: dict[str, str],
    ) -> Path:
        path = case_root / "records" / "compile" / project / "compile.yaml"
        write_yaml(
            path,
            {
                "schema_version": 1,
                "kind": "project_compile_checklist",
                "project": project,
                "parameters": parameters,
            },
        )
        return path

    def test_mkimage_recipe_contract_accepts_complete_roles_and_binds_optee_to_atf(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            case_root = Path(temp_dir) / "mkimage-complete-contract-case"
            case_root.mkdir()
            parameters = {"soc": "iMX95", "silicon_revision": "B0", "lpddr_type": "lpddr5", "oei_enabled": "NO", "recipe": "flash_a55"}
            path = self._mkimage_draft(case_root, parameters=parameters)
            atf = self._producer_stub(
                case_root,
                "imx-atf",
                {"platform": "imx95", "spd": "none"},
            )
            uboot = self._producer_stub(
                case_root,
                "uboot-imx",
                {"defconfig": "imx95_19x19_evk_defconfig", "jobs": "8"},
            )
            smfw = self._producer_stub(
                case_root,
                "imx-sm",
                {"config": "other/mx95rte"},
            )
            ahab = case_root / "inputs" / "mx95b0-ahab-container.img"
            ahab.parent.mkdir()
            shutil.copyfile(
                self._fixed_asset(parameters, "ahab"),
                ahab,
            )
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            data["inputs"] = {
                "artifacts": [
                    {
                        "name": "atf",
                        "slot": "atf",
                        "checklist": str(atf.relative_to(case_root)),
                        "artifact": "bl31",
                        "stage_to": "iMX95/bl31.bin",
                    },
                    {
                        "name": "uboot_bin",
                        "slot": "uboot_bin",
                        "checklist": str(uboot.relative_to(case_root)),
                        "artifact": "uboot_bin",
                        "stage_to": "iMX95/u-boot.bin",
                    },
                    {
                        "name": "uboot_spl",
                        "slot": "uboot_spl",
                        "checklist": str(uboot.relative_to(case_root)),
                        "artifact": "uboot_spl",
                        "stage_to": "iMX95/u-boot-spl.bin",
                    },
                    {
                        "name": "smfw",
                        "slot": "smfw",
                        "checklist": str(smfw.relative_to(case_root)),
                        "artifact": "smfw",
                        "stage_to": "iMX95/m33_image.bin",
                    },
                ],
                "files": [
                    {
                        "name": "ahab",
                        "slot": "ahab",
                        "path": str(ahab.relative_to(case_root)),
                        "stage_to": "iMX95/mx95b0-ahab-container.img",
                        "provenance": "synthetic firmware release used by this test",
                    }
                ],
            }
            write_yaml(path, data)
            normalized = checklists.normalize_checklist(path)
            self.assertEqual(normalized["project"], "imx-mkimage")
            self.assertEqual(normalized["make_recipe"]["source"], "iMX95/soc.mak")
            self.assertEqual(
                list(normalized["make_recipe"]["required_m_payloads"].values()),
                [],
            )

            optee = self._producer_stub(
                case_root,
                "imx-optee-os",
                {"platform": "imx", "platform_flavor": "mx95evk"},
            )
            data["inputs"]["artifacts"].append(
                {
                    "name": "optee",
                    "slot": "optee",
                    "checklist": str(optee.relative_to(case_root)),
                    "artifact": "tee",
                    "stage_to": "iMX95/tee.bin",
                }
            )
            write_yaml(path, data)
            with self.assertRaisesRegex(ToolError, "requires atf producer parameter spd=opteed"):
                checklists.normalize_checklist(path)

            atf_data = yaml.safe_load(atf.read_text(encoding="utf-8"))
            atf_data["parameters"]["spd"] = "opteed"
            write_yaml(atf, atf_data)
            self.assertEqual(checklists.normalize_checklist(path)["project"], "imx-mkimage")

            ahab.write_bytes(b"wrong fixed asset\n")
            self.assertEqual(checklists.normalize_checklist(path)["project"], "imx-mkimage")
            del data["inputs"]["files"][0]["provenance"]
            write_yaml(path, data)
            with self.assertRaisesRegex(ToolError, "requires provenance"):
                checklists.normalize_checklist(path)

    def test_mkimage_flash_all_requires_mcore_bin_producer_roles(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            case_root = Path(temp_dir) / "mkimage-mcore-contract-case"
            case_root.mkdir()
            parameters = {"soc": "iMX95", "silicon_revision": "B0", "lpddr_type": "lpddr5", "oei_enabled": "NO", "recipe": "flash_all"}
            path = self._mkimage_draft(case_root, parameters=parameters)
            atf = self._producer_stub(
                case_root, "imx-atf", {"platform": "imx95", "spd": "none"}
            )
            uboot = self._producer_stub(
                case_root,
                "uboot-imx",
                {"defconfig": "imx95_19x19_evk_defconfig", "jobs": "8"},
            )
            smfw = self._producer_stub(
                case_root, "imx-sm", {"config": "other/mx95rte"}
            )
            m_sdk = case_root / "records/compile/m_freertos_sdk/compile.yaml"
            write_yaml(
                m_sdk,
                {
                    "schema_version": 1,
                    "kind": "m_freertos_sdk_compile_checklist",
                    "target": "m_freertos_sdk",
                    "jobs": {
                        "m7": {
                            "mode": "source_build",
                            "soc": "imx95",
                            "board": "imx95lpd5evk19",
                            "core": "cm7",
                            "core_role": "m7",
                            "application": "demo_apps/hello_world",
                            "build_configuration": "release",
                        }
                    },
                },
            )
            ahab = case_root / "inputs/mx95b0-ahab-container.img"
            ahab.parent.mkdir()
            shutil.copyfile(
                self._fixed_asset(parameters, "ahab"),
                ahab,
            )
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            data["inputs"] = {
                "artifacts": [
                    {"name": "atf", "slot": "atf", "checklist": str(atf.relative_to(case_root)), "artifact": "bl31", "stage_to": "iMX95/bl31.bin"},
                    {"name": "uboot_bin", "slot": "uboot_bin", "checklist": str(uboot.relative_to(case_root)), "artifact": "uboot_bin", "stage_to": "iMX95/u-boot.bin"},
                    {"name": "uboot_spl", "slot": "uboot_spl", "checklist": str(uboot.relative_to(case_root)), "artifact": "uboot_spl", "stage_to": "iMX95/u-boot-spl.bin"},
                    {"name": "smfw", "slot": "smfw", "checklist": str(smfw.relative_to(case_root)), "artifact": "smfw", "stage_to": "iMX95/m33_image.bin"},
                    {"name": "m7", "slot": "m_payload", "checklist": str(m_sdk.relative_to(case_root)), "artifact": "m7.bin", "stage_to": "iMX95/m7_image.bin"},
                ],
                "files": [
                    {"name": "ahab", "slot": "ahab", "path": str(ahab.relative_to(case_root)), "stage_to": "iMX95/mx95b0-ahab-container.img", "provenance": "synthetic firmware release"}
                ],
            }
            write_yaml(path, data)
            normalized = checklists.normalize_checklist(path)
            self.assertEqual(normalized["project"], "imx-mkimage")
            self.assertEqual(normalized["make_recipe"]["source"], "iMX95/soc.mak")
            self.assertEqual(
                list(normalized["make_recipe"]["required_m_payloads"].values()),
                ["m7_image.bin"],
            )

            without_m = yaml.safe_load(path.read_text(encoding="utf-8"))
            without_m["inputs"]["artifacts"] = [
                entry
                for entry in without_m["inputs"]["artifacts"]
                if entry["slot"] != "m_payload"
            ]
            write_yaml(path, without_m)
            with self.assertRaisesRegex(
                ToolError, "soc.mak recipe iMX95/flash_all requires M payloads"
            ):
                checklists.normalize_checklist(path)
            without_m["inputs"]["files"].append({
                "name": "disguised_m7", "slot": "firmware",
                "path": str(ahab.relative_to(case_root)),
                "stage_to": "iMX95/m7_image.bin",
                "provenance": "must not bypass the M producer contract",
            })
            write_yaml(path, without_m)
            with self.assertRaisesRegex(ToolError, "requires M payloads"):
                checklists.normalize_checklist(path)
            write_yaml(path, data)

            m_data = yaml.safe_load(m_sdk.read_text(encoding="utf-8"))
            m_data["jobs"]["m7"]["core_role"] = "m70"
            write_yaml(m_sdk, m_data)
            with self.assertRaisesRegex(ToolError, "requires producer parameter core_role=m7"):
                checklists.normalize_checklist(path)

            data["inputs"]["artifacts"] = [
                entry for entry in data["inputs"]["artifacts"] if entry["name"] != "m7"
            ]
            data["inputs"]["files"].append(
                {"name": "raw_m7", "slot": "m_payload", "path": str(ahab.relative_to(case_root)), "stage_to": "iMX95/m7_image.bin"}
            )
            write_yaml(path, data)
            with self.assertRaisesRegex(ToolError, "unknown slots: m_payload"):
                checklists.normalize_checklist(path)

    def test_mkimage_fixed_asset_catalog_requires_exact_oei_firmware_set(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            parameters = {
                "soc": "iMX95", "silicon_revision": "B0",
                "lpddr_type": "lpddr5", "oei_enabled": "YES",
            }
            sources = {role: self._fixed_asset(parameters, role) for role in (
                "ahab", "lpddr_imem", "lpddr_dmem", "lpddr_imem_qb", "lpddr_dmem_qb",
            )}
            files = []
            for name, source in sources.items():
                destination = root / source.name
                shutil.copyfile(source, destination)
                files.append(
                    {
                        "name": name,
                        "slot": "ahab" if name == "ahab" else "firmware",
                        "path": str(destination),
                        "stage_to": f"iMX95/{source.name.removeprefix('default-')}",
                    }
                )
            matrix_path = self.support / "compile_targets/flashbin/FIXED_ASSETS.yaml"
            matrix = yaml.safe_load(matrix_path.read_text(encoding="utf-8"))
            catalog_reference = {
                "path": str(matrix_path), "hash": hash_data(matrix),
                "selectors": matrix["selectors"],
            }
            parameters = {
                "soc": "iMX95",
                "silicon_revision": "B0",
                "lpddr_type": "lpddr5",
                "oei_enabled": "YES",
            }
            composition.validate_fixed_asset_contract(
                catalog_reference,
                parameters,
                {"artifacts": [], "files": files},
            )
            with self.assertRaisesRegex(ToolError, "requires roles: lpddr_dmem_qb"):
                composition.validate_fixed_asset_contract(
                    catalog_reference,
                    parameters,
                    {"artifacts": [], "files": files[:-1]},
                )


class Imx943ChecklistContractTests(ProjectContractFixture, unittest.TestCase):
    def test_a0_lpddr4_no_m7_accepts_m33s_and_rejects_mixed_inputs(self) -> None:
        case_root = self.support / "work/imx943-case"
        case_root.mkdir(parents=True)
        template = self.projects / "imx-mkimage/COMPILE_CHECKLIST.yaml"
        data = yaml.safe_load(template.read_text(encoding="utf-8"))
        data["case_root"] = str(case_root)
        data["source"]["ref"] = "lf-6.18.20-2.0.0"
        parameters = {
            "soc": "iMX94", "silicon_revision": "A0", "lpddr_type": "lpddr4",
            "oei_enabled": "YES", "recipe": "flash_all_no_m7",
        }
        data["parameters"].update(parameters)
        data["intent"]["reason"] = "synthetic imx943 A0 LPDDR4 input contract"
        producers = [
            ("oei", "imx-oei", "oei_ddr", "oei-m33-ddr.bin", {"silicon_revision": "A0", "board": "mx943lp4-15", "oei_type": "ddr"}),
            ("atf", "imx-atf", "bl31", "bl31.bin", {"platform": "imx94", "spd": "opteed"}),
            ("uboot_bin", "real-time-edge-uboot", "uboot_bin", "u-boot.bin", {"defconfig": "imx943_evk_defconfig", "jobs": "8"}),
            ("uboot_spl", "real-time-edge-uboot", "uboot_spl", "u-boot-spl.bin", {"defconfig": "imx943_evk_defconfig", "jobs": "8"}),
            ("smfw", "imx-sm", "smfw", "m33_image.bin", {"config": "other/mx94rtecm70netc"}),
            ("optee", "imx-optee-os", "tee", "tee.bin", {"platform": "imx", "platform_flavor": "mx943evk"}),
        ]
        artifacts = []
        for slot, project, artifact, filename, values in producers:
            relative = f"records/compile/{project}/compile.yaml"
            write_yaml(case_root / relative, {
                "schema_version": 1, "kind": "project_compile_checklist",
                "project": project, "parameters": values,
            })
            artifacts.append({"name": slot, "slot": slot, "checklist": relative,
                              "artifact": artifact, "stage_to": f"iMX94/{filename}"})
        m_path = case_root / "records/compile/m_freertos_sdk/compile.yaml"
        m_data = {"kind": "m_freertos_sdk_compile_checklist", "jobs": {
            "m33s": {"soc": "imx943", "core_role": "m33s"},
            "cm70": {"soc": "imx943", "core_role": "m70"},
        }}
        write_yaml(m_path, m_data)
        artifacts.append({"name": "m33s", "slot": "m_payload",
                          "checklist": str(m_path.relative_to(case_root)),
                          "artifact": "m33s.bin", "stage_to": "iMX94/m33s_image.bin"})
        matrix = yaml.safe_load((self.support / "compile_targets/flashbin/FIXED_ASSETS.yaml").read_text())
        definitions = matrix["assets"]["iMX94"]["A0"]["lpddr4"]["YES"]["files"]
        files = []
        for role, definition in definitions.items():
            destination = case_root / "inputs" / Path(definition["stage_to"]).name
            destination.parent.mkdir(exist_ok=True)
            shutil.copyfile(self._fixed_asset(parameters, role), destination)
            files.append({"name": role, "slot": definition["slot"],
                          "path": str(destination.relative_to(case_root)),
                          "stage_to": definition["stage_to"],
                          "provenance": "synthetic release described by this fixture"})
        data["inputs"] = {"artifacts": artifacts, "files": files}
        path = case_root / "records/compile/imx-mkimage/compile.yaml"
        write_yaml(path, data)
        normalized = checklists.normalize_checklist(path)
        self.assertEqual(normalized["parameters"], parameters)
        self.assertEqual(list(normalized["make_recipe"]["required_m_payloads"].values()), ["m33s_image.bin"])
        with self.subTest(rejected="extra CM70 payload"):
            data["inputs"]["artifacts"].append({
                "name": "cm70", "slot": "m_payload", "checklist": str(m_path.relative_to(case_root)),
                "artifact": "cm70.bin", "stage_to": "iMX94/m70_image.bin",
            })
            write_yaml(path, data)
            with self.assertRaisesRegex(ToolError, "does not consume M payloads"):
                checklists.normalize_checklist(path)
            data["inputs"]["artifacts"].pop()
            write_yaml(path, data)
        with self.subTest(rejected="missing fixed-input provenance"):
            ahab = next(entry for entry in files if entry["slot"] == "ahab")
            del ahab["provenance"]
            write_yaml(path, data)
            with self.assertRaisesRegex(ToolError, "requires provenance"):
                checklists.normalize_checklist(path)


if __name__ == "__main__":
    unittest.main()
