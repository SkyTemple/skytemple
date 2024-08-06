#!/usr/bin/env python3
"""
File to generate the Flatpak manifest files and pip/cargo source files. See README.md.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import textwrap
import tomllib
from contextlib import contextmanager
from functools import partial
from io import StringIO
from shutil import which
from tempfile import TemporaryDirectory
from typing import Iterator, Literal, Required, TypedDict, cast
from urllib.request import urlretrieve

import requirements
import yaml
from jinja2 import DictLoader, Environment
from requirements.requirement import Requirement


def print_nice(prefix: str, text: str, ansi_code: str):
    print(f"{ansi_code}[{prefix}] {text}\x1b[0m")


def print_i(text: str) -> None:
    print_nice("i", text, "\x1b[1m")


def print_e(text: str) -> None:
    print_nice("X", text, "\x1b[31m")


def print_w(text: str) -> None:
    print_nice("!", text, "\x1b[33m")


def print_cmd(text: str) -> None:
    print_nice(".", text, "\x1b[36m")


def print_t(text: str) -> None:
    print_nice(" ", text, "\x1b[37m")


class FlatpakSourceRef(TypedDict, total=False):
    type: Required[Literal["git"] | Literal["dir"]]
    url: str
    path: str

    commit: str
    tag: str
    branch: str

    dest: str


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INTERPRETER = sys.executable
REQUIREMENTS_FILE_NIGHTLY = os.path.join(BASE_DIR, "..", "..", "requirements.txt")
REQUIREMENTS_FILE_STABLE = os.path.join(BASE_DIR, "..", "..", "requirements-frozen.txt")
SKYTEMPLE_PYPROJECT_FILE = os.path.join(BASE_DIR, "..", "..", "pyproject.toml")
EXTRA_PIP_DEPENDENCIES = os.path.join(BASE_DIR, "pip-add-extra-dependencies.toml")
PIP_GENERATOR_PATH = os.path.join(BASE_DIR, "flatpak-builder-tools", "pip", "flatpak-pip-generator")
CARGO_GENERATOR_PATH = os.path.join(BASE_DIR, "flatpak-builder-tools", "cargo", "flatpak-cargo-generator.py")
MANIFEST_TEMPLATE_FILE = "org.skytemple.SkyTemple.yml.jinja"
OUT_MANIFEST_FILE = "org.skytemple.SkyTemple.yml"
OUT_PIP_REQUIREMENTS_FILE = "requirements-skytemple.json"
OUT_SKYTEMPLE_RUST_CARGO_FILE = "cargo-sources.json"
OUT_SSB_EMULATOR_CARGO_FILE = "cargo-sources-ssb-emulator.json"
SKYTEMPLE_GIT_URL = "https://github.com/SkyTemple/skytemple.git"
SKYTEMPLE_SSB_DEBUGGER_GIT_URL = "https://github.com/SkyTemple/skytemple-ssb-debugger.git"
SKYTEMPLE_SSB_EMULATOR_GIT_URL = "https://github.com/SkyTemple/skytemple-ssb-emulator.git"
SKYTEMPLE_RUST_GIT_URL = "https://github.com/SkyTemple/skytemple-rust.git"
SKYTEMPLE_FILES_GIT_URL = "https://github.com/SkyTemple/skytemple-files.git"
EXPLORERSCRIPT_GIT_URL = "https://github.com/SkyTemple/explorerscript.git"
GIT = cast(str, which("git"))
assert GIT is not None, "git must be installed"


def run_git(*args: str) -> str:
    cmd = list(args)
    print_cmd("git " + " ".join(cmd))
    return subprocess.run([GIT] + cmd, check=True, capture_output=True).stdout.decode("utf8").strip()


def get_commit(path: str) -> str:
    commit = run_git("-C", path, "rev-parse", "HEAD")
    print_t(f"Commit at {path}: {commit}")
    return commit


def get_git_tag_for_req(req: Requirement) -> str | None:
    if len(req["specs"]) > 0:
        assert len(req["specs"]) == 1, f"Only one spec per requirement is supported: {req["specs"]}"
        assert req["specs"][0][0] == "==", f"Only '==' operator is supported for requirements: {req["specs"][0]}"
        print_t(f"tag: {req["specs"][0][1]}")
        return req["specs"][0][1]
    print_t("tag: no tag")
    return None


def run_pip_generator(requirements_path: str, out_path: str) -> None:
    out_path = out_path.removesuffix(".json")
    requirements_path = os.path.abspath(requirements_path)
    print_cmd("flatpak-pip-generator -r " + requirements_path + " -o " + out_path)
    try:
        subprocess.run(
            [
                INTERPRETER,
                "-u",
                PIP_GENERATOR_PATH,
                "-r",
                requirements_path,
                "-o",
                os.path.basename(out_path),
                "--build-isolation",
            ],
            check=True,
            capture_output=True,
            cwd=os.path.dirname(out_path),
            env=os.environ,
        )
    except subprocess.CalledProcessError as e:
        print_e(f"Failed to run: {' '.join(e.cmd)}")
        print_e(f"Command stdout:\n{e.stdout.decode('utf8', 'ignore')}")
        print_e(f"Command stderr:\n{e.stderr.decode('utf8', 'ignore')}")
        exit(1)


def run_cargo_generator(cargo_lock_path: str, out_path: str) -> None:
    print_cmd("flatpak-cargo-generator " + cargo_lock_path + " -o " + out_path)
    try:
        subprocess.run(
            [INTERPRETER, "-u", CARGO_GENERATOR_PATH, cargo_lock_path, "-o", out_path],
            check=True,
            capture_output=True,
            env=os.environ,
        )
    except subprocess.CalledProcessError as e:
        print_e(f"Failed to run: {' '.join(e.cmd)}")
        print_e(f"Command stdout:\n{e.stdout.decode('utf8', 'ignore')}")
        print_e(f"Command stderr:\n{e.stderr.decode('utf8', 'ignore')}")
        exit(1)


def print_and_return_ref(ref_name: str, ref: FlatpakSourceRef) -> FlatpakSourceRef:
    print_t(f"source ref for {ref_name}: {ref}")
    return ref


def source_ref_skytemple_rust(req: Requirement, commit: str) -> FlatpakSourceRef:
    tag = get_git_tag_for_req(req)
    ref: FlatpakSourceRef
    if tag:
        ref = {
            "type": "git",
            "url": SKYTEMPLE_RUST_GIT_URL,
            "tag": tag,
            "dest": "skytemple-rust",
        }
    else:
        ref = {
            "type": "git",
            "url": SKYTEMPLE_RUST_GIT_URL,
            "commit": commit,
            "dest": "skytemple-rust",
        }
    return print_and_return_ref("skytemple-rust", ref)


def source_ref_skytemple_ssb_emulator(req: Requirement, commit: str) -> FlatpakSourceRef:
    tag = get_git_tag_for_req(req)
    ref: FlatpakSourceRef
    if tag:
        ref = {
            "type": "git",
            "url": SKYTEMPLE_SSB_EMULATOR_GIT_URL,
            "tag": tag,
            "dest": "ssb-emulator",
        }
    else:
        ref = {
            "type": "git",
            "url": SKYTEMPLE_SSB_EMULATOR_GIT_URL,
            "commit": commit,
            "dest": "ssb-emulator",
        }
    return print_and_return_ref("skytemple-ssb-emulator", ref)


def source_ref_explorerscript(req: Requirement, commit: str) -> FlatpakSourceRef:
    tag = get_git_tag_for_req(req)
    ref: FlatpakSourceRef
    if tag:
        ref = {
            "type": "git",
            "url": EXPLORERSCRIPT_GIT_URL,
            "tag": tag,
            "dest": "explorerscript",
        }
    else:
        ref = {
            "type": "git",
            "url": EXPLORERSCRIPT_GIT_URL,
            "commit": commit,
            "dest": "explorerscript",
        }
    return print_and_return_ref("explorerscript", ref)


def source_ref_skytemple(git_tag: str | None) -> FlatpakSourceRef:
    ref: FlatpakSourceRef
    if git_tag is None:
        ref = {"type": "dir", "path": os.path.abspath(os.path.join(BASE_DIR, "..", ".."))}
    else:
        ref = {"type": "git", "url": SKYTEMPLE_GIT_URL, "tag": git_tag}
    return print_and_return_ref("skytemple", ref)


@contextmanager
def clone_repo_for_generator(req: Requirement, git_url: str) -> Iterator[str]:
    with TemporaryDirectory() as tmp_dir:
        print_t(f"Cloning repo for {req.name} for analysis to tmp dir {tmp_dir}")
        tag = get_git_tag_for_req(req)
        run_git("clone", git_url, tmp_dir)
        if tag is not None:
            run_git("-C", tmp_dir, "checkout", tag)
        elif req.revision is not None:
            run_git("-C", tmp_dir, "checkout", req.revision)
        yield tmp_dir


def get_pkgname_and_version_from_repo(req: Requirement, git_url: str) -> tuple[str, str]:
    with clone_repo_for_generator(req, git_url) as tmp_dir:
        return get_pkgname_and_version_from_pyproject_toml(os.path.join(tmp_dir, "pyproject.toml"))


def fixup_and_add_extra_pip_dependencies(out_json_path: str, extras: dict) -> None:
    print_t("Fixing up requirements JSON file and adding additional dependencies")
    with open(out_json_path, "r") as f:
        modules = json.load(f)

    def remove_dependency(url: str, deps: list[str]):
        return any(dep in url for dep in deps)

    def remove_module(name: str, mods: list[str]):
        return any(name == mod for mod in mods)

    modules["modules"] = [
        mod for mod in modules["modules"] if not remove_module(mod["name"], extras["_remove"]["modules"])
    ]

    version_cache = {}
    checksum_cache = {}
    names_cache = {}

    for module in modules["modules"]:
        module["sources"] += extras["_all"].get("modules", [])
        for group in extras["_all"].get("groups", []):
            module["sources"] += extras["_group"][group]
        if module["name"] in extras:
            module["sources"] += extras[module["name"]].get("modules", [])
            for group in extras[module["name"]].get("groups", []):
                module["sources"] += extras["_group"][group]
        module["sources"] = [
            s for s in module["sources"] if not remove_dependency(s["url"], extras["_remove"]["dependencies"])
        ]
        # The pip generator doesn't properly parse the @ part of VCS dependencies, always trying to attribute
        # it as a commit. Sigh.
        # Also installing Git repos only works for one single depedency, so use download tar.gz instead.
        for source in module["sources"]:
            if "commit" in source:
                if source["commit"] is None:
                    branch = "master"
                else:
                    branch = source["commit"]
                giturl = source["url"]
                if giturl not in version_cache or giturl not in names_cache:
                    names_cache[giturl], version_cache[giturl] = get_pkgname_and_version_from_repo(
                        Requirement.parse_line(f"{giturl} @ {giturl}@{branch}"), giturl
                    )
                # Make sure to install the requirement from the downloaded tar instead
                if f"python3-{names_cache[giturl]}" == module["name"]:
                    module["build-commands"][0] = (
                        module["build-commands"][0].removesuffix('"."') + f'"{names_cache[giturl]}"'
                    )
                source["type"] = "file"
                del source["commit"]
                source["url"] = source["url"] + f"/archive/refs/heads/{branch}.tar.gz"
                if source["url"] not in checksum_cache:
                    # download to get checksum
                    with TemporaryDirectory() as tmp_dir:
                        print_t(f"Fetching {source["url"]} for hashsum.")
                        fpath = os.path.join(tmp_dir, "file")
                        urlretrieve(source["url"], fpath)
                        with open(fpath, "rb", buffering=0) as f9:
                            checksum_cache[source["url"]] = hashlib.file_digest(f9, "sha256").hexdigest()  # type: ignore

                source["sha256"] = checksum_cache[source["url"]]
                source["dest-filename"] = f"{names_cache[giturl]}-{version_cache[giturl]}.tar.gz"
    with open(out_json_path, "w") as f3:
        json.dump(modules, f3, indent=4)


def pip_add_group(extras: dict, value: str, dest: str | None = None) -> str:
    group = [dict(x) for x in extras["_group"][value]]
    if dest is not None:
        for m in group:
            m["dest"] = dest
    stream = StringIO()
    yaml.safe_dump(group, stream)
    stream.seek(0)
    yml = textwrap.indent(stream.read(), " " * 6).lstrip(" ").rstrip("\n")
    return yml


def generate(out_dir: str, reqs_file: str, *, tag: str | None = None) -> None:
    reqs = parse_reqs_with_skytemple_files_reqs(reqs_file)
    print_t(f"Generating to {out_dir}. Tag info: {tag}")
    with open(os.path.join(BASE_DIR, MANIFEST_TEMPLATE_FILE), "r") as f:
        jinja_env = Environment(loader=DictLoader({"tmpl": f.read()}))

    with open(EXTRA_PIP_DEPENDENCIES, "rb") as f2:
        extras = tomllib.load(f2)

    jinja_env.filters["pip_add_group"] = partial(pip_add_group, extras)

    skytemple_rust_req = reqs["skytemple-rust"]
    skytemple_ssb_emulator_req = reqs["skytemple-ssb-emulator"]
    explorerscript_req = reqs["explorerscript"]

    with clone_repo_for_generator(skytemple_rust_req, SKYTEMPLE_RUST_GIT_URL) as path_skytemple_rust:
        with clone_repo_for_generator(skytemple_ssb_emulator_req, SKYTEMPLE_SSB_EMULATOR_GIT_URL) as path_ssb_emulator:
            with clone_repo_for_generator(explorerscript_req, EXPLORERSCRIPT_GIT_URL) as path_explorerscript:
                commit_skytemple_rust = get_commit(path_skytemple_rust)
                commit_ssb_emulator = get_commit(path_ssb_emulator)
                commit_explorerscript = get_commit(path_explorerscript)

                result = jinja_env.get_template("tmpl").render(
                    skytemple_ref=json.dumps(source_ref_skytemple(tag)),
                    skytemple_rust_ref=json.dumps(source_ref_skytemple_rust(skytemple_rust_req, commit_skytemple_rust)),
                    skytemple_ssb_emulator_ref=json.dumps(
                        source_ref_skytemple_ssb_emulator(skytemple_ssb_emulator_req, commit_ssb_emulator)
                    ),
                    explorerscript_ref=json.dumps(source_ref_explorerscript(explorerscript_req, commit_explorerscript)),
                )

                run_pip_generator(reqs_file, os.path.join(out_dir, "requirements-skytemple.json"))
                run_cargo_generator(
                    os.path.join(path_skytemple_rust, "Cargo.lock"),
                    os.path.join(out_dir, "cargo-sources-skytemple-rust.json"),
                )
                run_cargo_generator(
                    os.path.join(path_ssb_emulator, "Cargo.lock"),
                    os.path.join(out_dir, "cargo-sources-ssb-emulator.json"),
                )
                fixup_and_add_extra_pip_dependencies(os.path.join(out_dir, "requirements-skytemple.json"), extras)

    print_t("Writing manifest file...")
    with open(os.path.join(out_dir, OUT_MANIFEST_FILE), "w") as f:
        f.write(result)


def parse_reqs_with_skytemple_files_reqs(req_file_path_skytemple: str) -> dict[str, Requirement]:
    """Concat the requirement files of SkyTemple, SkyTemple Files and SkyTemple Ssb Debugger"""
    print_t("Collecting requirements of SkyTemple and its requested SkyTemple Files version")
    reqs = parse_reqs(req_file_path_skytemple)
    with clone_repo_for_generator(reqs["skytemple-files"], SKYTEMPLE_FILES_GIT_URL) as path:
        reqs_files = parse_reqs(os.path.join(path, "requirements.txt"))
    with clone_repo_for_generator(reqs["skytemple-ssb-debugger"], SKYTEMPLE_SSB_DEBUGGER_GIT_URL) as path:
        reqs_debugger = parse_reqs(os.path.join(path, "requirements.txt"))
    return {**reqs_files, **reqs_debugger, **reqs}


def parse_reqs(req_file_path: str) -> dict[str, Requirement]:
    req_file_path = os.path.abspath(req_file_path)
    print_t(f"Analyzing requirements in {req_file_path}")
    reqs: dict[str, Requirement] = {}
    with open(req_file_path, "r") as f:
        lines_list = []
        for line in f.readlines():
            # remove anything after --config-settings, this is not supported by requirements-parser
            lines_list.append(re.sub("--config-settings.*", "", line))
        lines = "\n".join(lines_list)
    for req in requirements.parse(lines):
        if req.name is not None:
            reqs[req.name] = req
    return reqs


def create_stable_dir() -> str:
    stable_dir = os.path.join(BASE_DIR, "stable")
    shutil.rmtree(stable_dir, ignore_errors=True)
    os.makedirs(stable_dir, exist_ok=True)
    print_t(f"Using directory for stable: {stable_dir}")
    shutil.copytree(os.path.join(BASE_DIR, "assets"), os.path.join(BASE_DIR, "stable", "assets"))
    shutil.copytree(os.path.join(BASE_DIR, "patches"), os.path.join(BASE_DIR, "stable", "patches"))
    return stable_dir


def get_pkgname_and_version_from_pyproject_toml(path: str) -> tuple[str, str]:
    with open(path, "rb") as f:
        pyproject = tomllib.load(f)
    return pyproject["project"]["name"], pyproject["project"]["version"]


def stable_tag() -> str:
    tag = get_pkgname_and_version_from_pyproject_toml(SKYTEMPLE_PYPROJECT_FILE)[1]
    print_i(f"SkyTemple Tag: {tag}")
    return tag


def main():
    if len(sys.argv) < 2:
        print_e("Usage: python3 generator.py <target> <if target stable: git tag>")
        sys.exit(-1)

    target = sys.argv[1]
    print_i(f"Generating for: {target}")
    if target == "nightly":
        generate(BASE_DIR, REQUIREMENTS_FILE_NIGHTLY)
    elif target == "stable":
        generate(create_stable_dir(), REQUIREMENTS_FILE_STABLE, tag=stable_tag())
    else:
        print_e(f"Unknown target {target}")
        sys.exit(-1)
    print_i("Done")


if __name__ == "__main__":
    main()
