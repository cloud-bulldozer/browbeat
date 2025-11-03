#!/bin/bash

set -eo pipefail

# Index Prow job metadata to Elasticsearch.

setup_prow() {
    if [[ -z ${PROW_JOB_ID:-} ]]; then
        echo "Not running in Prow (PROW_JOB_ID not set). Skipping."
        exit 0
    fi

    ci="PROW"
    prow_base_url="https://prow.ci.openshift.org/view/gs/origin-ci-test/logs"
    prow_pr_base_url="https://prow.ci.openshift.org/view/gs/test-platform-results/pr-logs/pull/openshift_release"

    job_type=${JOB_TYPE:-}
    get_prowjob_info

    # Normalize job_type similar to the reference script
    if [[ "${job_type}" == "presubmit" && "${JOB_NAME:-}" == *pull* ]]; then
        job_type="pull"
    fi
    if [[ "${job_type}" == "presubmit" && "${JOB_NAME:-}" == *rehearse* ]]; then
        job_type="rehearse"
    fi
    if [[ "${job_type}" == "periodic" ]]; then
        if [[ "${pull_number}" != "0" && -n "${pull_number}" ]]; then
            job_type="pull"
        fi
    fi
}

# Extract Prow job info, including PR metadata for non-presubmit jobs via prowjob.json
get_prowjob_info() {
    pull_number="0"
    organization=""
    repository=""

    if [[ "${JOB_TYPE:-}" == "presubmit" ]]; then
        pull_number=${PULL_NUMBER:-0}
        organization=${REPO_OWNER:-}
        repository=${REPO_NAME:-}
    else
        local prow_artifacts_base_url="https://gcsweb-ci.apps.ci.l2s4.p1.openshiftapps.com/gcs/test-platform-results/logs"
        local job_id=${JOB_NAME:-}
        local task_id=${BUILD_ID:-}
        local prowjobjson_file="${PWD}/prowjob.json"
        local prowjobjson_url="${prow_artifacts_base_url}/${job_id}/${task_id}/prowjob.json"

        curl -s "${prowjobjson_url}" -o "${prowjobjson_file}" || true
        if result=$(cat "${prowjobjson_file}" 2>/dev/null | jq . 2>/dev/null); then
            pull_number=$(jq -r '.metadata.labels."prow.k8s.io/refs.pull" // "0"' "${prowjobjson_file}")
            organization=$(jq -r '.metadata.labels."prow.k8s.io/refs.org" // ""' "${prowjobjson_file}")
            repository=$(jq -r '.metadata.labels."prow.k8s.io/refs.repo" // ""' "${prowjobjson_file}")
        fi
    fi
}

set_duration() {
    local start_date="$1"
    local end_date="$2"

    if [[ -z ${start_date} ]]; then
        start_date=${end_date}
    fi

    if [[ -z ${start_date} || -z ${end_date} ]]; then
        duration=0
    else
        # GNU date (Prow images are Linux). For macOS this may not work, but this
        # script runs in Prow.
        local end_ts
        local start_ts
        end_ts=$(date -u -d "${end_date}" +"%s")
        start_ts=$(date -u -d "${start_date}" +"%s")
        duration=$(( end_ts - start_ts ))
    fi
}

# Collect OCP/cluster details via oc (best-effort; tolerate failures)
collect_ocp_details() {
    masters=0
    workers=0
    master_type=""
    worker_type=""
    cluster_name=""
    cluster_version=""
    network_type=""

    # Cluster metadata
    cluster_name=$(oc get infrastructure cluster -o jsonpath='{.status.infrastructureName}' 2>/dev/null || true)
    cluster_version=$(oc version -o json 2>/dev/null | jq -r '.openshiftVersion' 2>/dev/null || true)
    network_type=$(oc get network.config/cluster -o jsonpath='{.status.networkType}' 2>/dev/null || true)

    # Node roles and instance types
    for node in $(oc get nodes --ignore-not-found --no-headers -o custom-columns=:.metadata.name 2>/dev/null || true); do
        labels=$(oc get node "$node" --no-headers -o jsonpath='{.metadata.labels}' 2>/dev/null || true)
        if [[ $labels == *"node-role.kubernetes.io/master"* || $labels == *"node-role.kubernetes.io/control-plane"* ]]; then
            masters=$((masters + 1))
            master_type=$(oc get node "$node" -o json 2>/dev/null | jq -r '.metadata.labels["node.kubernetes.io/instance-type"] // .metadata.labels["beta.kubernetes.io/instance-type"] // empty' 2>/dev/null || true)
            taints=$(oc get node "$node" -o jsonpath='{.spec.taints}' 2>/dev/null || true)
            if [[ $labels == *"node-role.kubernetes.io/worker"* && $taints == "" ]]; then
                workers=$((workers + 1))
            fi
        elif [[ $labels == *"node-role.kubernetes.io/worker"* ]]; then
            workers=$((workers + 1))
            worker_type=$(oc get node "$node" -o json 2>/dev/null | jq -r '.metadata.labels["node.kubernetes.io/instance-type"] // .metadata.labels["beta.kubernetes.io/instance-type"] // empty' 2>/dev/null || true)
        fi
    done
}

collect_openstack_details() {
    # RHOSO/OpenStack metadata from the OpenShift 'openstack' namespace
    rhoso_version=""
    openstack_compute_nodes=0

    # Preferred: get from OpenStackVersion CR deployed version
    if ver=$(oc get openstackversion -o json 2>/dev/null | jq -r '.items[0].status.deployedVersion // .items[0].status.deployed_version // empty'); then
        rhoso_version=${ver}
    fi

    # Count EDPM compute nodes by summing all OpenStackDataPlaneNodeSet .spec.nodes across NodeSets
    if oc -n openstack get openstackdataplanenodeset >/dev/null 2>&1; then
        openstack_compute_nodes=$(oc -n openstack get openstackdataplanenodeset -o json 2>/dev/null | jq '[
            .items[] | (if .spec.nodes then (.spec.nodes|keys|length) else 0 end)
        ] | (add // 0)' 2>/dev/null)
    fi
}

derive_report_status() {
    test_status=""
    local report_dir="${PWD}/results"

    if ls "${report_dir}"/*.report >/dev/null 2>&1; then
        local total_lines
        local non_pass_count
        total_lines=$(grep -h "Test Status:" "${report_dir}"/*.report 2>/dev/null | wc -l | xargs || true)
        if [[ -n ${total_lines} && ${total_lines} -gt 0 ]]; then
            non_pass_count=$(grep -h "Test Status:" "${report_dir}"/*.report 2>/dev/null | grep -v "Test Status: pass" | wc -l | xargs || true)
            if [[ -n ${non_pass_count} && ${non_pass_count} -gt 0 ]]; then
                test_status="fail"
            else
                test_status="pass"
            fi
        fi
    fi
}

extract_browbeat_uuid() {
    browbeat_uuid=""
    if [[ -n ${BROWBEAT_LOG:-} && -f ${BROWBEAT_LOG} ]]; then
        browbeat_uuid=$(grep -oE '[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}' "${BROWBEAT_LOG}" | head -n1 || true)
    fi
}

index_prow_run() {
    if [[ -z ${ES_SERVER:-} ]]; then
        echo "ES_SERVER is not set."
        exit 0
    fi

    local task_id="${BUILD_ID:-}"
    local job_id="${JOB_NAME:-}"
    local job_run_id="${PROW_JOB_ID:-}"
    local execution_date="${JOB_START:-}"
    local start_date="${JOB_START:-}"
    local end_date="${JOB_END:-}"

    set_duration "${start_date}" "${end_date}"

    local build_url
    if [[ "${JOB_TYPE:-}" == "presubmit" ]]; then
        build_url="${prow_pr_base_url}/${PULL_NUMBER:-0}/${job_id}/${task_id}"
    else
        build_url="${prow_base_url}/${job_id}/${task_id}"
    fi

    local current_timestamp
    current_timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

    # Derive overall test status from report files if present
    derive_report_status
    local state
    if [[ -n ${test_status:-} ]]; then
        state="${test_status}"
    fi

    # Base JSON with core Prow metadata
    base_json='{
        "ciSystem":"'"${ci}"'",
        "uuid":"'"${browbeat_uuid}"'",
        "benchmark":"'"${WORKLOAD:-}"'",
        "masterNodesCount":"'"${masters}"'",
        "workerNodesCount":"'"${workers}"'",
        "masterNodesType":"'"${master_type}"'",
        "workerNodesType":"'"${worker_type}"'",
        "clusterName":"'"${cluster_name}"'",
        "ocpVersion":"'"${cluster_version}"'",
        "networkType":"'"${network_type}"'",
        "openstackVersion":"'"${rhoso_version}"'",
        "openstackComputeNodes":"'"${openstack_compute_nodes}"'",
        "jobType":"'"${job_type}"'",
        "jobName":"'"${job_id}"'",
        "buildId":"'"${task_id}"'",
        "prowJobId":"'"${job_run_id}"'",
        "jobStatus":"'"${state}"'",
        "buildUrl":"'"${build_url}"'",
        "executionDate":"'"${execution_date}"'",
        "jobDuration":"'"${duration}"'",
        "startDate":"'"${start_date}"'",
        "endDate":"'"${end_date}"'",
        "timestamp":"'"${current_timestamp}"'",
        "pullNumber":"'"${pull_number}"'",
        "organization":"'"${organization}"'",
        "repository":"'"${repository}"'"
    }'

    # ADDITIONAL_PARAMS can extend/override fields; must be valid JSON
    if [[ -n ${ADDITIONAL_PARAMS:-} ]]; then
        if ! echo "${ADDITIONAL_PARAMS}" | jq . >/dev/null 2>&1; then
            echo "Error: ADDITIONAL_PARAMS is not valid JSON."
            exit 1
        fi
    else
        ADDITIONAL_PARAMS='{}'
    fi

    local merged_json
    merged_json=$(jq -n --argjson base "${base_json}" --argjson extra "${ADDITIONAL_PARAMS}" '$base + $extra')

    # Build document ID: jobName/PROW_JOB_ID/BUILD_ID[/UUID]
    local doc_id
    doc_id="${job_id}%2F${job_run_id}%2F${task_id}"
    if [[ -n ${browbeat_uuid:-} ]]; then
        doc_id+="%2F${browbeat_uuid}"
    fi

    echo "${merged_json}"
    curl -sS --insecure -X POST \
        -H "Content-Type:application/json" \
        -H "Cache-Control:no-cache" \
        -d "${merged_json}" \
        "${ES_SERVER}/${ES_INDEX}/_doc/${doc_id}"
}

# Main
ES_INDEX=perf_scale_rhoso_ci
setup_prow
collect_ocp_details
collect_openstack_details
extract_browbeat_uuid
index_prow_run
