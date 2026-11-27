#!/usr/bin/env bash
# Install the wheel in dist/ into a fresh environment and render and check figures with it.
#
# Run after `uv build`: `bash scripts/check_package.sh`. The environment holds only the wheel and
# its dependencies, so the test sees what a project that installs the tag gets, not src/.
set -euo pipefail
shopt -s nullglob

root="$(cd "$(dirname "$0")/.." && pwd)"
wheels=("$root"/dist/figurekit-*.whl)
if [ "${#wheels[@]}" -ne 1 ]; then
  echo "expected one figurekit wheel in dist/, found ${#wheels[@]}; run uv build in a clean dist/" >&2
  exit 1
fi

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
uv venv --quiet --python 3.12 "$work/env"
uv pip install --quiet --python "$work/env" "${wheels[0]}"

# bin/ on Linux and macOS, Scripts/ on Windows.
export PATH="$work/env/bin:$work/env/Scripts:$PATH"
cd "$work"
python -I "$root/scripts/smoke.py" figures
figkit check figures figures/page
