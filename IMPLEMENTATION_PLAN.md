# LABINF Environment and Automation Implementation Plan

## Goal

Make the environment reproducible and verifiable for the published laboratory assignments, then run the lab workflow only against tested scenarios. Preserve the existing visual design, LaTeX structure, and pedagogical style of all final solution PDFs.

## Source of Truth

- Lab 01 currently in `Desktop/SICUREZZA DEI SISTEMI INFORMATIVI/LABS/lab01/lab01.pdf` is A.A. 2026/27.
- Lab 00 and Labs 02–05 currently in that directory are A.A. 2023/24. Do not silently claim they are a matching current-year set.
- Treat the actual assignment PDF and its supplied support files as authoritative. A solution transcript, README claim, or prior generated PDF is not proof that a command ran successfully.
- Keep the course solution template and visual style intact. Workflow changes may improve evidence capture, validation, and cleanup, but must not change PDF typography, colors, terminal panels, diagrams, section hierarchy, or output naming.

## Implementation Stages

### Stage 1 — Testable Lab 01 baseline

- Align Alice's target services with the Lab 01 instructions, including SSH credential capture, netstat inspection, the default FTP connection path, and the web-linked challenge.
- Keep the three-node Alice/Bob/Chuck bridge and fixed course addresses for this scenario.
- Add process supervision, service readiness checks, and a `verify` command that returns failure when a required node, tool, or service is unavailable.
- Limit broad container privileges to nodes that need them for the exercise and document platform constraints.
- Provide a Docker-compatible Ettercap launcher that preserves kernel forwarding while the MITM session is active.
- Add repeatable tests for configuration, service behavior, launch/verification failure cases, and the Lab 01 exercise path.

### Stage 2 — Reproducible build and CI

- Pin base images by digest or documented release and pin package inputs where practical.
- Build both Kali and Alice images in CI; validate Compose configuration and run container smoke/integration tests on Linux.
- Report architecture-specific limitations explicitly. Keep ARM64 and AMD64 build coverage.

### Stage 3 — Lab-specific topologies and materials

- Add a Frank router/firewall and routed subnets for Lab 04 rather than treating a single LAN as equivalent.
- Define separate Compose profiles/topologies for labs whose required roles and packet paths differ.
- Add or locate the official support files required by Labs 02, 03, and 05 before asserting those exercises are automatable. Never invent missing professor-supplied inputs.
- Maintain a per-lab capability matrix tied to assignment version and acceptance tests.

### Stage 4 — Evidence-first laboratory workflow

- For each lab, ingest the assignment and supplied materials, create a checklist of exercises and expected evidence, then execute in the correct nodes.
- Capture raw commands, stdout, stderr, exit status, timestamps, tool/image versions, and relevant packet captures. Persist the final raw log as `LABS/labXX/log.txt`; keep temporary LaTeX/build files under `.tmp_build/` and purge only those after successful PDF validation.
- Generate solution text only from captured outputs. Mark any unexecuted or unsupported exercise clearly; do not fabricate terminal output.
- Run a technical review and compile/render-check the PDF using the existing template and style without redesigning it.
- Produce one solution PDF and one raw execution log per lab.

## Acceptance Gates

### Static checks

- `docker compose config -q` succeeds.
- Shell scripts pass `bash -n`; Python sources compile.
- Tests cover required ports, SSH login, netstat listeners, expected HTTP challenge content, SMTP mailbox delivery, the mock FTP prompt, and launcher verification failures.

### Container checks

- Both images build for the host architecture; CI additionally builds AMD64 and ARM64 images.
- All expected services reach healthy state and remain supervised.
- Alice, Bob, and Chuck can reach required services using assignment commands.
- Lab 01 acceptance checks exercise service reachability, SSH login, challenge retrieval, ARP cache poisoning with bidirectional HTTP forwarding, HTTP traffic, and SMTP delivery.
- `verify` exits non-zero for stopped containers, missing tools, failed links, or unhealthy services.

### Workflow checks

- Every exercise in the selected assignment maps to a command/result in the raw log or an explicit unsupported/not-run reason.
- Solution terminal outputs match the raw log byte-for-byte where shown.
- PDF compilation, text extraction, page count, and rendered-page inspection pass without changing the established style.
- Final lab folder contains professor-supplied materials plus `log.txt` and `labXX_solution.pdf`; no temporary build files remain.

## Current Progress

- [x] Inspect the repository, current Lab 01 environment, course handouts, and existing solution-generation skill.
- [x] Record the implementation plan before making implementation changes.
- [x] Implement the Stage 1 environment changes and add the applicable Stage 2 CI validation.
- [x] Run Compose validation, shell/Python syntax checks, and the container integration suite.
- [x] Refine the existing solution-generation skill's evidence and test gates while preserving its PDF style requirements.
- [x] Proceed to Lab 01 phase-0 preflight after the environment acceptance gates passed.
- [x] Complete the evidence-backed Lab 01 solution and raw log without changing the established PDF style.
- [x] Preflight the available Lab 00 and Labs 02–05 handouts and inventory their support materials.
- [x] Execute the available Lab 02–05 procedures against the current environment and publish timestamped raw `log.txt` traces only; do not generate or change solution PDFs.
- [ ] Confirm the authoritative assignment versions and obtain missing professor-supplied archives before implementing Labs 02–05.

### Validation Results

- `docker compose -f environment/docker-compose.yml config -q`: passed.
- `bash -n` on the Bash launcher and service scripts: passed.
- `python3 -m py_compile` on the Python services and integration suite: passed.
- `python3 -m unittest discover -s tests -v`: 11 tests passed after fixing Kali entrypoint privilege handling for interface offloads. Coverage includes ARP poisoning, HTTP and SSH forwarding through the MITM, host reachability, service versions, FTP, SMTP, the challenge, and verifier failure handling.
- Final rerun on 2026-10-12: all 11 integration tests passed; Compose validation, shell syntax checks, Python compilation, and `git diff --check` passed.
- `labinf.sh start` and `labinf.sh verify` passed with all three nodes healthy and the expected Lab 01 services reachable on an isolated `10.92.2.0/24` network.
- PowerShell runtime validation was unavailable on this macOS host; `labinf.ps1` was updated in parallel with the tested shell launcher but still needs a Windows or PowerShell Core check.
- Lab 01 phase-0 confirms the 2026/27 handout v1.4 (06/10/2026), and it does not match the older existing solution narrative. The official challenge is linked from `index.html` to `secret.html`; the old solution's standalone port-1337 challenge is supplemental, not the handout's required method.
- The currently supplied Lab 00 and Lab 02–05 handouts are all A.A. 2023/24, while Lab 01 is A.A. 2026/27. Lab 00 is an environment setup guide, not an exercise sheet. Lab 02 has an existing solution and log, but its required support archive (including the brute-force, IHA, ECB-pattern, and hashdeep tree inputs) is absent; the existing solution PDF identifies itself as A.A. 2025/26, so it cannot be treated as a verified answer to the supplied 2023/24 assignment.
- Lab 03 requires the supplied `aes-gcm.py` script, which is absent. Lab 04 requires a routed Alice–Frank–Bob topology and supplied Apache/proxy configuration; the current single bridge does not model that path. Lab 05 requires the supplied StrongSwan PSK and certificate directory trees and related service/configuration artifacts; none are present. Do not generate replacement final solutions or claim full automation for these labs until the authoritative assignment set and support archives are available.
- On 2026-10-12, bounded Lab 02–05 runs produced raw execution logs at `LABS/labXX/log.txt` without creating or modifying any solution PDFs. The logs distinguish completed exercises from generated fixtures and blocked steps. Lab 04's temporary routed topology was exercised and removed; HTTPtunnel/Ptunnel did not produce a working SSH relay, and the supplied Apache proxy configs are missing. Lab 05 local TLS server authentication, mutual TLS, session reuse, and Alice-side manual XFRM traffic passed. Static ESP packet capture and Bob-side XFRM setup are restricted by runtime capabilities/tools; StrongSwan IKE lacks its course configuration and a running daemon. Missing official exercise archives remain prerequisites for full Lab 02/03/05 coverage.
- The updated live trace now captures the handout FTP command and response, the linked web challenge, a remote-browser capability check, and the optional DNS resolver/route preflight. Exercise 8's `remote_browser` plugin is installed, but its required Firefox executable and display are absent. Optional Exercise 9 cannot be exercised faithfully because Bob uses Docker's embedded resolver (`127.0.0.11`) and the scenario has no DNS host/gateway on its isolated bridge.
- The Lab 01 solution PDF was regenerated in the established format and visually reviewed at 20 pages. Its shown transcript excerpts were checked against the full raw execution trace. The final folder contains the validated `lab01_solution.pdf` and unabridged `log.txt`; temporary build files were removed only after validation.
- A full Lab 01 traffic run demonstrated ARP poisoning, bidirectional HTTP forwarding, SMTP delivery and cleartext capture, and successful SSH login while sniffing only visible SSH negotiation metadata. Ping can show duplicate replies during the Ettercap session in this Docker Desktop topology; it showed no packet loss in the captured run.
- The prior `lab01/log.txt` was a planning narrative that referenced a missing raw execution log. It has been replaced by the timestamped raw execution trace after validation, alongside the regenerated solution PDF.

## Known Constraints to Resolve During Implementation

- Docker Desktop was not running during the initial assessment; container tests require a running daemon.
- The Antigravity IDE installation is present, but no Antigravity workflow/project for this repository was found in its saved workspace list. The course `.agents/skills/lab-solution-generator/SKILL.md` is the available global workflow source; it requires source-version preflight, evidence-backed logs, and preservation of the existing PDF style. Its Ettercap guidance now also records the tested Docker Desktop forwarding, redirect, MTU, and offload constraints.
- Labs 02–05 require assignment-version confirmation and course support files before their full scenarios can be implemented or tested. The present `LABS/` folder contains no professor-supplied archives or per-lab support trees.
