#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
FABRIC_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

IMAGE="${CALIPER_IMAGE:-hyperledger/caliper:0.6.0}"
SUT_BINDING="${CALIPER_BIND_SUT:-fabric:2.2}"

cd "${FABRIC_DIR}"

mkdir -p caliper/reports

DISCOVERY_AS_LOCALHOST="${DISCOVERY_AS_LOCALHOST:-true}"

if [ "${DISCOVERY_AS_LOCALHOST}" = "false" ]; then
  NETWORK_CONFIG="caliper/networks/kataster-fabric-cloud.yaml"
else
  NETWORK_CONFIG="caliper/networks/kataster-fabric.yaml"
fi

exec docker run --rm --network host \
  -v "${FABRIC_DIR}":/hyperledger/caliper/workspace \
  -e "CALIPER_BIND_SUT=${SUT_BINDING}" \
  -e "DISCOVERY_AS_LOCALHOST=${DISCOVERY_AS_LOCALHOST}" \
  -e "CALIPER_FABRIC_GATEWAY_DISCOVERY_AS_LOCALHOST=${DISCOVERY_AS_LOCALHOST}" \
  "${IMAGE}" \
  launch manager \
  --caliper-workspace /hyperledger/caliper/workspace \
  --caliper-networkconfig "${NETWORK_CONFIG}" \
  --caliper-benchconfig caliper/benchmarks/parcels.yaml \
  --caliper-flow-only-test \
  --caliper-fabric-gateway-enabled \
  --caliper-fabric-gateway-discovery-as-localhost="${DISCOVERY_AS_LOCALHOST}" \
  --caliper-report-path caliper/reports/report.html
