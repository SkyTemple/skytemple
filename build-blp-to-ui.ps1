$ErrorActionPreference = "Stop"
# Convert the Blueprint UI files to XML.
# This requires the blueprint-compiler submodule to be checked out.
.\blueprint-compiler\blueprint-compiler.py batch-compile skytemple\data\widget skytemple\data\widget (Resolve-Path skytemple\data\widget\*.blp)
if ($LASTEXITCODE) { exit $LASTEXITCODE }
.\blueprint-compiler\blueprint-compiler.py batch-compile skytemple\data\widget skytemple\data\widget (Resolve-Path skytemple\data\widget\**\*.blp)
if ($LASTEXITCODE) { exit $LASTEXITCODE }
