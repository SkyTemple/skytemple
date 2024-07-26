# SkyTemple Flatpak

This is built for the nightly & stable of SkyTemple using Flatpak.
Note that the Flatpak Build environment does not have internet access and builds everything from source
to conform to Flathub's build processes.

On new releases a GitHub Action will update the files in the Flathub GitHub repo and open a PR there,
Flathub is used to distribute the stable app.

Versioned are only things which are not auto-generated. Auto generated are the source JSON files with
Pip and Cargo dependencies. Use `./generator.py nightly` to build it. Use `./generator.py stable` to generate a new
stable manifest (which can be used for the Flathub repo).
Versions are pulled from `requirements-frozen.txt` in the root of the repo for stable and from `requirements.txt` for
nightly.

To run the Makefile you need to be in a Python (3.12+) environment with the requirements from the `requirements.txt` in
this directory installed.

- App ID: `org.skytemple.SkyTemple`
- Flathub Repo: https://github.com/flathub/org.skytemple.SkyTemple
