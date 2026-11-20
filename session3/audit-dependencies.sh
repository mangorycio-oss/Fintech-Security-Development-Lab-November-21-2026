#!/usr/bin/env bash
set -euo pipefail

report=$(mktemp)
trap 'rm -- "$report"' EXIT

for requirements in session1/requirements-api.txt session1/frontend/requirements.txt \
                    session2/requirements-api.txt session2/frontend/requirements.txt; do
    echo "Auditing $requirements"
    : > "$report"
    status=0
    pip-audit -r "$requirements" --format json --desc off --output "$report" || status=$?
    if [[ "$status" == 1 ]] && jq -e 'any(.dependencies[]; .vulns | length > 0)' "$report" >/dev/null; then
        jq . "$report"
        echo "::warning::Known vulnerabilities in $requirements. Review the report above."
    elif [[ "$status" != 0 ]]; then
        exit "$status"
    else
        jq . "$report"
    fi
done
