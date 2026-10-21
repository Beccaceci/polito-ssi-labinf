# Laboratory compatibility implementation plan

Approved scope: all executable core and optional exercises in Labs 01–05; Lab 00 is setup/preflight. Docker is primary, command equivalents are explicit, missing professor inputs may have labeled practice replacements, and rootful Docker in a dedicated Lima VM is the kernel fallback. Existing published solutions/logs are preserved.

## Sequence and gates

1. [x] Create the versioned exercise manifest and material provenance inventory.
2. [x] Complete exercise-node packages, supervised services, privileges, persistent workspaces and unified launchers.
3. [x] Integrate the Lab 02 Mac app/optional originals and implement Lab 02/03 practice inputs and crypto acceptance cases.
4. [x] Implement Lab 04 shared-LAN and routed scenarios, firewall policies, real HTTP/ICMP SSH tunnels, SOCKS restrictions and the HTTPS forward proxy.
5. [x] Implement reciprocal XFRM modes, StrongSwan PSK/certificates, TLS/mTLS/resumption/interception and site-to-site traffic for Lab 05.
6. [x] Complete Lab 01 browser and isolated DNS scenarios; retain existing regression suite.
7. [x] Provide rootful Lima, native ARM64 evidence, AMD64/ARM64 build CI, compatibility documentation and immutable image inventory.

## Required evidence

Every exercise manifest entry identifies the handout version/page, original operation, node, privileges, dependencies, inputs, equivalent invocation, expected outcome and acceptance case. Lab 01 is 2026/27 v1.4; Labs 02–05 are 2023/24 (v1.1, v3.8, v3.7 and the supplied Lab 05 handout respectively). The newer Lab 02 Mac app is supplementary.

Verification writes new timestamped runs under workspace/runs/, retaining stdout/stderr, command, node/user, exit status, duration, input provenance, versions and captures. Expected failures are asserted. Failed dependencies are blocked, never passed. No existing LABS/labXX/log.txt or solution PDF is overwritten.

## Completion

Practice-complete requires a passing result for every executable core/optional entry on a supported runtime. Official-complete additionally requires all original inputs. Missing, blocked, unimplemented and untested cases remain visible and cannot count as passed. Tool installation alone is insufficient. External services are supplemental; deterministic local scenarios are the acceptance baseline. Performance results have no fixed throughput thresholds.

This checklist records implementation progress; the run reports are the authority for runtime acceptance.
