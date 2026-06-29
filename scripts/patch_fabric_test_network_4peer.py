from pathlib import Path


BASE = Path("/home/rd/fabric-exp/fabric-samples/test-network")


def backup(path: Path) -> None:
    bak = path.with_suffix(path.suffix + ".bak4peer")
    if not bak.exists():
        bak.write_text(path.read_text(), encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    if old not in text:
        raise RuntimeError(f"Could not find expected block: {label}")
    return text.replace(old, new, 1)


def patch_cryptogen() -> None:
    for rel in [
        "organizations/cryptogen/crypto-config-org1.yaml",
        "organizations/cryptogen/crypto-config-org2.yaml",
    ]:
        path = BASE / rel
        backup(path)
        text = path.read_text(encoding="utf-8")
        text = text.replace("Template:\n      Count: 1", "Template:\n      Count: 2")
        path.write_text(text, encoding="utf-8")


def patch_compose() -> None:
    path = BASE / "compose/compose-test-net.yaml"
    backup(path)
    bak = path.with_suffix(path.suffix + ".bak4peer")
    if bak.exists():
        text = bak.read_text(encoding="utf-8")
    else:
        text = path.read_text(encoding="utf-8")
    text = replace_once(
        text,
        "volumes:\n  orderer.example.com:\n  peer0.org1.example.com:\n  peer0.org2.example.com:\n",
        "volumes:\n"
        "  orderer.example.com:\n"
        "  peer0.org1.example.com:\n"
        "  peer1.org1.example.com:\n"
        "  peer0.org2.example.com:\n"
        "  peer1.org2.example.com:\n",
        "volumes",
    )

    peer1_org1 = """
  peer1.org1.example.com:
    container_name: peer1.org1.example.com
    image: hyperledger/fabric-peer:latest
    labels:
      service: hyperledger-fabric
    environment:
      - FABRIC_CFG_PATH=/etc/hyperledger/peercfg
      - FABRIC_LOGGING_SPEC=INFO
      - CORE_PEER_TLS_ENABLED=true
      - CORE_PEER_PROFILE_ENABLED=false
      - CORE_PEER_TLS_CERT_FILE=/etc/hyperledger/fabric/tls/server.crt
      - CORE_PEER_TLS_KEY_FILE=/etc/hyperledger/fabric/tls/server.key
      - CORE_PEER_TLS_ROOTCERT_FILE=/etc/hyperledger/fabric/tls/ca.crt
      - CORE_PEER_ID=peer1.org1.example.com
      - CORE_PEER_ADDRESS=peer1.org1.example.com:8051
      - CORE_PEER_LISTENADDRESS=0.0.0.0:8051
      - CORE_PEER_CHAINCODEADDRESS=peer1.org1.example.com:8052
      - CORE_PEER_CHAINCODELISTENADDRESS=0.0.0.0:8052
      - CORE_PEER_GOSSIP_BOOTSTRAP=peer0.org1.example.com:7051
      - CORE_PEER_GOSSIP_EXTERNALENDPOINT=peer1.org1.example.com:8051
      - CORE_PEER_LOCALMSPID=Org1MSP
      - CORE_PEER_MSPCONFIGPATH=/etc/hyperledger/fabric/msp
      - CORE_OPERATIONS_LISTENADDRESS=peer1.org1.example.com:9446
      - CORE_METRICS_PROVIDER=prometheus
      - CHAINCODE_AS_A_SERVICE_BUILDER_CONFIG={\"peername\":\"peer1org1\"}
      - CORE_CHAINCODE_EXECUTETIMEOUT=300s
    volumes:
      - ../organizations/peerOrganizations/org1.example.com/peers/peer1.org1.example.com:/etc/hyperledger/fabric
      - peer1.org1.example.com:/var/hyperledger/production
    working_dir: /root
    command: peer node start
    ports:
      - 8051:8051
      - 9446:9446
    networks:
      - test
"""

    peer1_org2 = """
  peer1.org2.example.com:
    container_name: peer1.org2.example.com
    image: hyperledger/fabric-peer:latest
    labels:
      service: hyperledger-fabric
    environment:
      - FABRIC_CFG_PATH=/etc/hyperledger/peercfg
      - FABRIC_LOGGING_SPEC=INFO
      - CORE_PEER_TLS_ENABLED=true
      - CORE_PEER_PROFILE_ENABLED=false
      - CORE_PEER_TLS_CERT_FILE=/etc/hyperledger/fabric/tls/server.crt
      - CORE_PEER_TLS_KEY_FILE=/etc/hyperledger/fabric/tls/server.key
      - CORE_PEER_TLS_ROOTCERT_FILE=/etc/hyperledger/fabric/tls/ca.crt
      - CORE_PEER_ID=peer1.org2.example.com
      - CORE_PEER_ADDRESS=peer1.org2.example.com:10051
      - CORE_PEER_LISTENADDRESS=0.0.0.0:10051
      - CORE_PEER_CHAINCODEADDRESS=peer1.org2.example.com:10052
      - CORE_PEER_CHAINCODELISTENADDRESS=0.0.0.0:10052
      - CORE_PEER_GOSSIP_BOOTSTRAP=peer0.org2.example.com:9051
      - CORE_PEER_GOSSIP_EXTERNALENDPOINT=peer1.org2.example.com:10051
      - CORE_PEER_LOCALMSPID=Org2MSP
      - CORE_PEER_MSPCONFIGPATH=/etc/hyperledger/fabric/msp
      - CORE_OPERATIONS_LISTENADDRESS=peer1.org2.example.com:9447
      - CORE_METRICS_PROVIDER=prometheus
      - CHAINCODE_AS_A_SERVICE_BUILDER_CONFIG={\"peername\":\"peer1org2\"}
      - CORE_CHAINCODE_EXECUTETIMEOUT=300s
    volumes:
      - ../organizations/peerOrganizations/org2.example.com/peers/peer1.org2.example.com:/etc/hyperledger/fabric
      - peer1.org2.example.com:/var/hyperledger/production
    working_dir: /root
    command: peer node start
    ports:
      - 10051:10051
      - 9447:9447
    networks:
      - test
"""

    if "container_name: peer1.org1.example.com" not in text:
        text = text.replace(
            "\n  peer0.org2.example.com:\n    container_name: peer0.org2.example.com\n",
            peer1_org1 + "\n  peer0.org2.example.com:\n    container_name: peer0.org2.example.com\n",
            1,
        )
    if "container_name: peer1.org2.example.com" not in text:
        text = text.rstrip() + "\n" + peer1_org2 + "\n"
    path.write_text(text, encoding="utf-8")

    path = BASE / "compose/docker/docker-compose-test-net.yaml"
    backup(path)
    bak = path.with_suffix(path.suffix + ".bak4peer")
    if bak.exists():
        text = bak.read_text(encoding="utf-8")
    else:
        text = path.read_text(encoding="utf-8")
    docker_peer1_org1 = """
  peer1.org1.example.com:
    container_name: peer1.org1.example.com
    image: hyperledger/fabric-peer:latest
    labels:
      service: hyperledger-fabric
    environment:
      #Generic peer variables
      - CORE_VM_ENDPOINT=unix:///host/var/run/docker.sock
      - CORE_VM_DOCKER_HOSTCONFIG_NETWORKMODE=fabric_test
    volumes:
      - ./docker/peercfg:/etc/hyperledger/peercfg
      - ${DOCKER_SOCK}:/host/var/run/docker.sock
"""
    docker_peer1_org2 = """
  peer1.org2.example.com:
    container_name: peer1.org2.example.com
    image: hyperledger/fabric-peer:latest
    labels:
      service: hyperledger-fabric
    environment:
      #Generic peer variables
      - CORE_VM_ENDPOINT=unix:///host/var/run/docker.sock
      - CORE_VM_DOCKER_HOSTCONFIG_NETWORKMODE=fabric_test
    volumes:
      - ./docker/peercfg:/etc/hyperledger/peercfg
      - ${DOCKER_SOCK}:/host/var/run/docker.sock
"""
    if "container_name: peer1.org1.example.com" not in text:
        text = text.replace(
            "\n  peer0.org2.example.com:\n    container_name: peer0.org2.example.com\n",
            docker_peer1_org1 + "\n  peer0.org2.example.com:\n    container_name: peer0.org2.example.com\n",
            1,
        )
    if "container_name: peer1.org2.example.com" not in text:
        text = text.rstrip() + "\n" + docker_peer1_org2 + "\n"
    path.write_text(text, encoding="utf-8")


def patch_env_var() -> None:
    path = BASE / "scripts/envVar.sh"
    backup(path)
    text = path.read_text(encoding="utf-8")
    if "USING_ORG -eq 11" not in text:
        old = """  elif [ $USING_ORG -eq 2 ]; then
    export CORE_PEER_LOCALMSPID=Org2MSP
    export CORE_PEER_TLS_ROOTCERT_FILE=$PEER0_ORG2_CA
    export CORE_PEER_MSPCONFIGPATH=${TEST_NETWORK_HOME}/organizations/peerOrganizations/org2.example.com/users/Admin@org2.example.com/msp
    export CORE_PEER_ADDRESS=localhost:9051
  elif [ $USING_ORG -eq 3 ]; then"""
        new = """  elif [ $USING_ORG -eq 2 ]; then
    export CORE_PEER_LOCALMSPID=Org2MSP
    export CORE_PEER_TLS_ROOTCERT_FILE=$PEER0_ORG2_CA
    export CORE_PEER_MSPCONFIGPATH=${TEST_NETWORK_HOME}/organizations/peerOrganizations/org2.example.com/users/Admin@org2.example.com/msp
    export CORE_PEER_ADDRESS=localhost:9051
  elif [ $USING_ORG -eq 11 ]; then
    export CORE_PEER_LOCALMSPID=Org1MSP
    export CORE_PEER_TLS_ROOTCERT_FILE=$PEER0_ORG1_CA
    export CORE_PEER_MSPCONFIGPATH=${TEST_NETWORK_HOME}/organizations/peerOrganizations/org1.example.com/users/Admin@org1.example.com/msp
    export CORE_PEER_ADDRESS=localhost:8051
  elif [ $USING_ORG -eq 12 ]; then
    export CORE_PEER_LOCALMSPID=Org2MSP
    export CORE_PEER_TLS_ROOTCERT_FILE=$PEER0_ORG2_CA
    export CORE_PEER_MSPCONFIGPATH=${TEST_NETWORK_HOME}/organizations/peerOrganizations/org2.example.com/users/Admin@org2.example.com/msp
    export CORE_PEER_ADDRESS=localhost:10051
  elif [ $USING_ORG -eq 3 ]; then"""
        text = replace_once(text, old, new, "setGlobals peer1 mappings")
    path.write_text(text, encoding="utf-8")


def patch_create_channel() -> None:
    path = BASE / "scripts/createChannel.sh"
    backup(path)
    text = path.read_text(encoding="utf-8")
    text = replace_once(
        text,
        """infoln "Joining org1 peer to the channel..."
joinChannel 1
infoln "Joining org2 peer to the channel..."
joinChannel 2
""",
        """infoln "Joining org1 peer0 to the channel..."
joinChannel 1
infoln "Joining org1 peer1 to the channel..."
joinChannel 11
infoln "Joining org2 peer0 to the channel..."
joinChannel 2
infoln "Joining org2 peer1 to the channel..."
joinChannel 12
""",
        "joinChannel peer1",
    )
    path.write_text(text, encoding="utf-8")


def patch_deploy_cc() -> None:
    path = BASE / "scripts/deployCC.sh"
    backup(path)
    text = path.read_text(encoding="utf-8")
    text = replace_once(
        text,
        """## Install chaincode on peer0.org1 and peer0.org2
infoln "Installing chaincode on peer0.org1..."
installChaincode 1
infoln "Install chaincode on peer0.org2..."
installChaincode 2
""",
        """## Install chaincode on all four peers used by the experiment
infoln "Installing chaincode on peer0.org1..."
installChaincode 1
infoln "Installing chaincode on peer1.org1..."
installChaincode 11
infoln "Installing chaincode on peer0.org2..."
installChaincode 2
infoln "Installing chaincode on peer1.org2..."
installChaincode 12
""",
        "install chaincode all peers",
    )
    path.write_text(text, encoding="utf-8")


def main() -> None:
    if not BASE.exists():
        raise SystemExit(f"Missing test-network: {BASE}")
    patch_cryptogen()
    patch_compose()
    patch_env_var()
    patch_create_channel()
    patch_deploy_cc()
    print("patched test-network for 4 peers")


if __name__ == "__main__":
    main()
