# Handout command compatibility

The source of truth is docs/exercises.json. It records the exact supplied handout hashes and all executable exercise groups, including optional tasks. Lab 00 is installation/preflight. Current source handouts are Lab 01 2026/27 and Labs 02–05 2023/24; matching current-year originals have not been inferred.

| Classroom operation | Container equivalent and reason |
|---|---|
| systemctl start/stop/restart/status ssh/apache2 | sudo labinf-service <action> ssh/apache2; Supervisor controls actual foreground daemons. Containers do not run systemd. |
| sudo ./lab01.sh run/clean | Host ./labinf.sh start/stop --lab 01; no host Docker socket is mounted into a node. reset explicitly recreates node state. |
| root SSH/SCP password and /root | Use kali:kali (ali:ali for Frank's gateway exercise) and /workspace; use shell <node> --root for administrative commands. Public-key root login remains available when deliberately configured. |
| manual edits to sysctl under read-only /proc/sys | Compose sets namespaced forwarding/redirect flags at creation. Runtime control requiring writable sysctls is confined to explicitly privileged attacker nodes. |
| implicit DES/RC4 availability | /etc/ssl/openssl-lab.cnf enables OpenSSL's default and legacy providers inside the node; TLS security is not globally lowered. |
| openssl speed <alias> not compiled into speed | openssl speed -evp <cipher-or-digest>; asymmetric aliases are tested separately. |
| raw pkeyutl signing on old OpenSSL | Explicit -rawin -digest sha256 on modern OpenSSL; verifyrecover exposes the signed DigestInfo. dgst is also exercised. |
| openssl enc -aes-128-gcm | Expected rejection, preserved as part of Lab 03; the separately labeled four-file aes-gcm.py implements AEAD. |
| invalid example key/IV (e.g. 123/432) | Use validated full-size key/nonce; malformed values are negative tests, not successful encryption. |
| detached S/MIME text newline conversion | Acceptance uses explicit -binary to preserve input bytes. Normal S/MIME canonicalizes text newlines. |
| full nmap -T0 scan of 1024 ports | The full command remains available. Automated acceptance uses one port with --scan-delay 20ms, exercising the scan family without claiming the classroom timing measurement. |
| xhost + and hardcoded Firefox locations | ./labinf.sh gui plus the installed labinf-browser launcher in the node's noVNC/X display. The actual remote_browser plugin must trigger a visible Firefox window. |
| DNS spoof against public destinations | The isolated dns scenario routes a local example.test query through the attacker/gateway. Controlled resolver delay makes the race repeatable. |
| lynx with an HTTPS proxy unsupported by a build | curl --proxy https://Frank:443 --proxy-cacert <CA>; this is a forward proxy, not a reverse proxy. |
| historical ipsec.conf/ipsec.secrets | StrongSwan starter, charon and stroke are installed, with explicit IKEv2 replacement configurations. swanctl alone is insufficient. |
| historical NULL/weak TLS experiments | Explicit per-process TLS1.2 cipher/security settings in the isolated experiment; normal trust/hostname verification stays enabled. |
| timings measured in physical lab | Record the local architecture, kernel, image and actual elapsed/CPU time. No performance parity with classroom hardware is asserted. |

Original material imports are immutable and checked against SHA256 metadata. Practice mode chooses imported/bundled originals first, then independently implemented replacements. Official mode blocks cases whose required originals are absent. Replacement configurations live separately; they do not claim byte compatibility with unavailable course archives. Imported Apache configurations retain their classroom paths and may require the same IP/path edits described in the handouts.

Verification mutates the selected isolated lab's services, firewall and crypto state. Work and logs are retained under workspace; reset discards container configuration but preserves node files and evidence. Keep one material revision per basename to avoid ambiguity. Do not run two verifiers concurrently on the same lab/scenario.

## Evidence contract

Each run includes exact executed invocations, stdout/stderr, user/node, timestamps, exit status, expected status, material provenance, source fingerprint, image IDs/digests, package versions and relevant packet captures. Multi-line invocations run under bash -euo pipefail. A failed command or pipeline cannot be hidden by a later successful command. Intended failures have exact status assertions. Dependencies that did not pass are blocked. No blocked, failed, unimplemented or untested case counts as passed.

Coverage is tied to the current implementation fingerprint. Historic results from another source revision do not establish current compatibility. Existing published LABS/labXX/log.txt and final PDFs are not targets of the verifier.
