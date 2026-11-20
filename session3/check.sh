#!/usr/bin/env bash
set -euo pipefail

session_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repo_dir=$(dirname "$session_dir")
session2_dir="$repo_dir/session2"
report_dir=${RUNNER_TEMP:-"$session_dir/reports"}/zap
export COMPOSE_PROJECT_NAME=${COMPOSE_PROJECT_NAME:-session3}
export WEB_GATEWAY_PORT=${WEB_GATEWAY_PORT:-18000}
export BANK_HOST_PORT=${BANK_HOST_PORT:-18001}
export FRONTEND_HOST_PORT=${FRONTEND_HOST_PORT:-18501}
export WEBAUTHN_ORIGIN="http://localhost:$WEB_GATEWAY_PORT"
export OAUTH_REDIRECT_URI="$WEBAUTHN_ORIGIN/section-2/bank/callback"
export BANK_BROWSER_URL="http://localhost:$BANK_HOST_PORT"
export FRONTEND_BROWSER_URL="http://localhost:$FRONTEND_HOST_PORT"

compose() {
    docker compose --project-directory "$session2_dir" "$@"
}

audit_dependencies() {
    for requirements in session1/requirements-api.txt session1/frontend/requirements.txt \
                        session2/requirements-api.txt session2/frontend/requirements.txt; do
        echo "Auditing $requirements"
        report=$(mktemp)
        status=0
        pip-audit -r "$repo_dir/$requirements" --format json --desc off --output "$report" || status=$?
        if [[ "$status" == 1 ]] && jq -e 'any(.dependencies[]; .vulns | length > 0)' "$report" >/dev/null; then
            jq . "$report"
            echo "::warning::Known vulnerabilities in $requirements. Review the report above."
        elif [[ "$status" != 0 ]]; then
            rm -- "$report"
            return "$status"
        else
            jq . "$report"
        fi
        rm -- "$report"
    done
}

scan_images() (
    scan_dir=$(mktemp -d)
    trap 'find "$scan_dir" -depth -delete' EXIT
    images=$(compose config --images)
    findings=0
    for image in $images; do
        echo "Scanning $image"
        docker save -o "$scan_dir/image.tar" "$image"
        status=0
        docker run --rm --user "$(id -u):$(id -g)" \
            --mount "type=bind,source=$scan_dir,target=/scan" \
            ghcr.io/aquasecurity/trivy:0.74.0@sha256:62b1e65e8869bc4b4c6aa4fa2b21595256c7c2f6018a9d9ad61caf87187c1969 \
            image --cache-dir /scan/cache --scanners vuln --no-progress \
            --severity HIGH,CRITICAL --exit-code 2 --input /scan/image.tar || status=$?
        case "$status" in
            0) ;;
            2)
                printf '::error::HIGH or CRITICAL image vulnerabilities found in %s\n' "$image"
                findings=2
                ;;
            *) exit "$status" ;;
        esac
    done
    exit "$findings"
)

passive_scan() {
    mkdir -p "$report_dir"
    chmod a+w "$report_dir"
    docker run --rm --network "${COMPOSE_PROJECT_NAME}_default" \
        -v "$repo_dir/.github/zap-passive.yml:/zap/plan.yml:ro" \
        -v "$report_dir:/zap/reports" \
        ghcr.io/zaproxy/zaproxy:stable@sha256:9624669db72f54d86c4b46a7064518bd9bf79d8c61a4c31befa9923489f328af \
        zap.sh -cmd -autorun /zap/plan.yml
    test -s "$report_dir/zap-passive.html"
}

case "${1:-}" in
    source) cd "$repo_dir"; bandit -r session1/main.py session1/routers session1/frontend \
        session2/web session2/bank session2/shared session2/frontend --exit-zero ;;
    source-high) cd "$session2_dir"; bandit -r web bank shared frontend --severity-level high ;;
    dependencies) audit_dependencies ;;
    build) compose build; compose pull gateway ;;
    images) scan_images ;;
    start) compose up --no-build -d --wait --wait-timeout 120 ;;
    passive) passive_scan ;;
    test) compose run --rm --no-deps \
        -e PYTHONDONTWRITEBYTECODE=1 -e TEST_GATEWAY_URL=http://gateway:8000 \
        -v "$session2_dir:/workspace:ro" api python -m unittest discover -v ;;
    logs) compose logs --no-color ;;
    stop) compose down --volumes --remove-orphans ;;
    *) echo "Usage: $0 {source|source-high|dependencies|build|images|start|passive|test|logs|stop}" >&2; exit 2 ;;
esac
