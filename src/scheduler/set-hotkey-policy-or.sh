#!/usr/bin/env bash
set -euo pipefail

export PATH=/usr/local/go/bin:/home/rd/fabric-exp/fabric-samples/bin:$PATH
export FABRIC_CFG_PATH=/home/rd/fabric-exp/fabric-samples/config

TEST_NETWORK_HOME="${TEST_NETWORK_HOME:-/home/rd/fabric-exp/fabric-samples/test-network}"
CHANNEL="${FABRIC_CHANNEL:-vllchannel}"
CC_NAME="${FABRIC_CHAINCODE:-hotkey}"
VERSION="${FABRIC_CHAINCODE_VERSION:-1.2-or}"
SEQUENCE="${FABRIC_CHAINCODE_SEQUENCE:-4}"
PACKAGE_ID="${FABRIC_CHAINCODE_PACKAGE_ID:-hotkey_1.2:4f3db01660894ecfa8f9d846fe34fc7b5503dd0403dcfdc18b127d970b4d9d2c}"
POLICY="${FABRIC_CHAINCODE_POLICY:-OR('Org1MSP.peer','Org2MSP.peer')}"

ORDERER_CA="${TEST_NETWORK_HOME}/organizations/ordererOrganizations/example.com/tlsca/tlsca.example.com-cert.pem"
ORG1_CA="${TEST_NETWORK_HOME}/organizations/peerOrganizations/org1.example.com/tlsca/tlsca.org1.example.com-cert.pem"
ORG2_CA="${TEST_NETWORK_HOME}/organizations/peerOrganizations/org2.example.com/tlsca/tlsca.org2.example.com-cert.pem"

set_org1() {
  export CORE_PEER_TLS_ENABLED=true
  export CORE_PEER_LOCALMSPID=Org1MSP
  export CORE_PEER_TLS_ROOTCERT_FILE="${ORG1_CA}"
  export CORE_PEER_MSPCONFIGPATH="${TEST_NETWORK_HOME}/organizations/peerOrganizations/org1.example.com/users/Admin@org1.example.com/msp"
  export CORE_PEER_ADDRESS=localhost:7051
}

set_org2() {
  export CORE_PEER_TLS_ENABLED=true
  export CORE_PEER_LOCALMSPID=Org2MSP
  export CORE_PEER_TLS_ROOTCERT_FILE="${ORG2_CA}"
  export CORE_PEER_MSPCONFIGPATH="${TEST_NETWORK_HOME}/organizations/peerOrganizations/org2.example.com/users/Admin@org2.example.com/msp"
  export CORE_PEER_ADDRESS=localhost:9051
}

approve_current_org() {
  peer lifecycle chaincode approveformyorg \
    -o localhost:7050 \
    --ordererTLSHostnameOverride orderer.example.com \
    --channelID "${CHANNEL}" \
    --name "${CC_NAME}" \
    --version "${VERSION}" \
    --package-id "${PACKAGE_ID}" \
    --sequence "${SEQUENCE}" \
    --signature-policy "${POLICY}" \
    --tls \
    --cafile "${ORDERER_CA}"
}

echo "Approving ${CC_NAME} sequence ${SEQUENCE} policy ${POLICY} for Org1MSP"
set_org1
approve_current_org

echo "Approving ${CC_NAME} sequence ${SEQUENCE} policy ${POLICY} for Org2MSP"
set_org2
approve_current_org

echo "Checking commit readiness"
set_org1
peer lifecycle chaincode checkcommitreadiness \
  --channelID "${CHANNEL}" \
  --name "${CC_NAME}" \
  --version "${VERSION}" \
  --sequence "${SEQUENCE}" \
  --signature-policy "${POLICY}" \
  --tls \
  --cafile "${ORDERER_CA}" \
  --output json

echo "Committing ${CC_NAME} sequence ${SEQUENCE}"
peer lifecycle chaincode commit \
  -o localhost:7050 \
  --ordererTLSHostnameOverride orderer.example.com \
  --channelID "${CHANNEL}" \
  --name "${CC_NAME}" \
  --version "${VERSION}" \
  --sequence "${SEQUENCE}" \
  --signature-policy "${POLICY}" \
  --tls \
  --cafile "${ORDERER_CA}" \
  --peerAddresses localhost:7051 \
  --tlsRootCertFiles "${ORG1_CA}" \
  --peerAddresses localhost:9051 \
  --tlsRootCertFiles "${ORG2_CA}"

echo "Committed definition:"
peer lifecycle chaincode querycommitted -C "${CHANNEL}" -n "${CC_NAME}" --output json
