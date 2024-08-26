#!/usr/bin/env bash
# Creates a tar.gz from a Git repo.

# Based on: https://gist.github.com/bojanpotocnik/e18c90f5993dca7ea495ce82bba1364f

DESTINATION=$2
cd $1
REPO_DIR="$(git rev-parse --show-toplevel)"
TOP_PREFIX=$(basename "$REPO_DIR")
TOP_FILE="$REPO_DIR/$TOP_PREFIX-$(git rev-parse --short HEAD).tar"

# Update all submodules
git submodule update --init --recursive

# Create module archive
git archive --prefix="$TOP_PREFIX/" --output="$TOP_FILE" HEAD

# Archive each submodule recursively:
# 1. Create .sub.tar file for each submodule using correct relative paths
# 2. Concatenate each .sub.tar file into a top-most .tar file
# 3. Remove each .sub.tar file afterwards
# Note:
# - $displaypath contains the relative path from the current working directory to the submodules root directory
# - $toplevel is the absolute path to the top-level of the immediate super-project
# - Use single instead of double quotes to expand $displaypath within the git submodule foreach command, not here
# - Export other variables so that they can be expanded within the git submodule foreach command
export TOP_PREFIX
export TOP_FILE
# shellcheck disable=SC2016
git submodule foreach --recursive '
    SUB_PREFIX="$TOP_PREFIX/$displaypath/" &&
    SUB_FILE="$(basename $(git rev-parse --show-toplevel))-$(git rev-parse --short HEAD).tar" &&
    git archive --prefix="$SUB_PREFIX" --output="$SUB_FILE" HEAD &&
    tar --concatenate --file="$TOP_FILE" "$SUB_FILE" &&
    echo "    Merged $SUB_FILE to $TOP_FILE" &&
    rm "$SUB_FILE"
'

# Compress the combined tar file
printf "\nCompressing...\n"
gzip --best --verbose "$TOP_FILE"

mv "${TOP_FILE}.gz" "$DESTINATION"
