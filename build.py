#!/usr/bin/env python3
# I choose python because Magisk already need python for it's
# build process, so I'm not adding extra dependencies for build
import os
import sys
import shutil
import subprocess
import requests
import json

ROOT = os.path.dirname(os.path.realpath(__file__))
MAGISK_DIR = os.path.join(ROOT, "Magisk")
MAGISK_CONFIG = os.path.join(MAGISK_DIR, "config.prop")
MAGISK_GRADLE_PROP = os.path.join(MAGISK_DIR, "gradle.properties")
MAGISK_NOPGISK = os.path.join(MAGISK_DIR, "Nopgisk")
PATCHES_DIR = os.path.join(ROOT, "patches")
PATCHES_STG_DIR = os.path.join(ROOT, "patches-stg")
OUTPUT_DIR = os.path.join(ROOT, "output")
OUTPUT_DIR_SRC = os.path.join(OUTPUT_DIR, "sources.zip")
OUTPUT_DIR_JSON = os.path.join(OUTPUT_DIR, "canary.json")
OUTPUT_DIR_NOTES = os.path.join(OUTPUT_DIR, "notes.md")
MAGISK_GIT_URL = "https://github.com/topjohnwu/Magisk.git"
MAGISK_API_PULLS_URL = "https://api.github.com/repos/topjohnwu/Magisk/pulls"
# User from where the PR are used by default for staging patches
MAGISK_PR_PROVIDERS = ["LSPosed", "canyie"]
# Whitelisted PR are allowed to be loaded even if it's not a patch from a provider or a draft
MAGISK_WHITELISTED_PR = [5804, 5803, 5802]
# Blacklisted PR are denied to be loaded even if it's a patch from a provider
MAGISK_BLACKLISTED_PR = []

NOTES = {}
NOTES["text"] = "### Nopgisk ${versionCode}\n\n"
NOTES["text"] = NOTES["text"] + "The bleeding edge Magisk fork!\n\n"
NOTES["text"] = NOTES["text"] + "If you have come here, it's for instability!\n\n"

# Try to find fallback ANDROID_SDK_ROOT if not defined
if ("ANDROID_SDK_ROOT" not in os.environ) or (len(os.environ["ANDROID_SDK_ROOT"]) == 0):
    sdk_root = ""
    if not ("ANDROID_HOME" not in os.environ or len(os.environ["ANDROID_HOME"]) == 0) \
            and os.path.exists(os.environ["ANDROID_HOME"]):
        sdk_root = os.environ["ANDROID_HOME"]
    elif sys.platform == "win32":
        sdk_root = os.path.join(os.environ["USERPROFILE"], "AppData", "Local", "Android", "Sdk")
    elif sys.platform == "darwin":
        sdk_root = os.path.join(os.environ["HOME"], "Library", "Android", "Sdk")
    else:
        sdk_root = os.path.join(os.environ["HOME"], "Android", "Sdk")
    if os.path.exists(sdk_root):
        os.environ["ANDROID_SDK_ROOT"] = sdk_root


# Delete the content of a folder without deleting the folder itself
def clear_folder(folder):
    if not os.path.exists(folder):
        return
    for root, dirs, files in os.walk(folder):
        for f in files:
            os.unlink(os.path.join(root, f))
        for d in dirs:
            shutil.rmtree(os.path.join(root, d))

def copy_folder(source, dest):
    if os.path.exists(dest):
        os.remove(dest)
    shutil.copytree(source, dest)

def read_props(prop_file):
    keys = {}
    with open(prop_file) as f:
        for line in f:
            if not line.startswith("#") and "=" in line:
                name, value = line.split("=", 1)
                keys[name.strip()] = value.strip()
    return keys


def exec_cmd(args, cwd=MAGISK_DIR):
    subprocess.run(args, check=True, cwd=cwd)


# Patch steps
def cleanup():
    if os.path.exists(MAGISK_NOPGISK):
        clear_folder(MAGISK_NOPGISK)
    pass


def update_staging_patches():
    pulls = json.loads(requests.get(MAGISK_API_PULLS_URL).text)
    hash2url = {}
    for pull in pulls:
        if pull["state"] == "open" and not (pull["number"] in MAGISK_BLACKLISTED_PR) and \
                ((pull["number"] in MAGISK_WHITELISTED_PR) or
                 (pull["head"]["repo"]["owner"]["login"] in MAGISK_PR_PROVIDERS and not pull["draft"])):
            hash2url[pull["merge_commit_sha"]] = pull["patch_url"]
            print("Using experimental patch \"" + pull["title"] + "\" by " + pull["user"]["login"])
            NOTES["text"] = NOTES["text"] + "- \"" + pull["title"] + "\" by [" + pull["user"]["login"] + "]"
            NOTES["text"] = NOTES["text"] + "(https://github.com/" + pull["user"]["login"] + ")\n"
    if not os.path.exists(PATCHES_STG_DIR):
        os.mkdir(PATCHES_STG_DIR)
    else:
        for patch in os.listdir(PATCHES_STG_DIR):
            if len(patch) < 6 or not (patch[:-6] in hash2url.keys()):
                os.unlink(os.path.join(PATCHES_STG_DIR, patch))
    for pr_hash, pr_url in hash2url.items():
        pr_patch = os.path.join(PATCHES_STG_DIR, pr_hash + ".patch")
        if not os.path.exists(pr_patch):
            print("Downloading: " + pr_url)
            pr_patch_content = requests.get(pr_url).text
            f = open(pr_patch, "w")
            f.write(pr_patch_content)
            f.close()


def update_magisk_repo():
    if not os.path.exists(MAGISK_DIR):
        exec_cmd(["git", "clone", MAGISK_GIT_URL], cwd=ROOT)
    else:
        exec_cmd(["git", "reset", "--hard", "HEAD~1"])
        exec_cmd(["git", "clean", "-df"])
        exec_cmd(["git", "pull", "--rebase", "--force"])
    exec_cmd(["git", "submodule", "update", "--force", "--init", "--recursive"])


def apply_patches(folder):
    for patch in os.listdir(folder):
        print("Applying " + patch)
        exec_cmd(["git", "apply", "-C2", "--ignore-whitespace", "--reject", os.path.join(folder, patch)])


def archive_source():
    if not os.path.exists(MAGISK_NOPGISK):
        os.mkdir(MAGISK_NOPGISK)
    copy_folder(os.path.join(ROOT, "patches"), os.path.join(MAGISK_NOPGISK, "patches"))
    copy_folder(os.path.join(ROOT, "patches-stg"), os.path.join(MAGISK_NOPGISK, "patches-stg"))
    exec_cmd(["git", "add", "--ignore-errors", "--no-warn-embedded-repo", "*"])
    exec_cmd(["git", "commit", "--no-verify", "--no-gpg-sign", "--no-status", "-a", "--author=Nopgisk <>", "-m", "Nopgisk changes"])
    exec_cmd(["git", "archive", "--format=zip", "-o", OUTPUT_DIR_SRC, "HEAD"])


def build_magisk():
    if not os.path.exists(OUTPUT_DIR):
        os.mkdir(OUTPUT_DIR)
    exec_cmd(["./build.py", "ndk"])
    props = read_props(MAGISK_GRADLE_PROP)
    f = open(MAGISK_CONFIG, "w")
    f.write("outdir=" + OUTPUT_DIR + "\n")
    f.write("version=nopgisk-" + props["magisk.versionCode"] + "\n")
    f.close()
    exec_cmd(["./build.py", "-v", "all"])
    f = open(OUTPUT_DIR_JSON, "w")
    f.write("{\n")
    f.write("  \"magisk\": {\n")
    f.write("    \"version\": \"nopgisk-" + props["magisk.versionCode"] + "\",\n")
    f.write("    \"versionCode\": \"" + props["magisk.versionCode"] + "\",\n")
    f.write("    \"link\": \"https://raw.githubusercontent.com/Fox2Code/nopgisk-files/main/app-debug.apk\",\n")
    f.write("    \"note\": \"https://raw.githubusercontent.com/Fox2Code/nopgisk-files/main/notes.md\"\n")
    f.write("  },\n")
    f.write("  \"stub\": {\n")
    f.write("    \"versionCode\": \"" + props["magisk.stubVersion"] + "\",\n")
    f.write("    \"link\": \"https://raw.githubusercontent.com/Fox2Code/nopgisk-files/main/stub-release.apk\"\n")
    f.write("  }\n")
    f.write("}\n")
    f.close()
    NOTES["text"] = NOTES["text"].replace("${versionCode}", props["magisk.versionCode"])
    NOTES["text"] = NOTES["text"] + "\nYou may join the telegram chat at: [https://t.me/Fox2Code_Chat](https://t.me/Fox2Code_Chat)"
    f = open(OUTPUT_DIR_NOTES, "w")
    f.write(NOTES["text"])
    f.write("\n")
    f.close()
    pass


if __name__ == "__main__":
    print("[Nopgisk] Cleaning up...")
    cleanup()
    print("[Nopgisk] Downloading...")
    NOTES["text"] = NOTES["text"] + "Using staging patches:\n"
    update_staging_patches()
    update_magisk_repo()
    print("[Nopgisk] Applying patches...")
    apply_patches(PATCHES_STG_DIR)
    apply_patches(PATCHES_DIR)
    print("[Nopgisk] Archiving source...")
    archive_source()
    print("[Nopgisk] Building...")
    build_magisk()
    print("[Nopgisk] Done!")

