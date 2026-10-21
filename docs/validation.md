# Environment validation report

Validation date: 2026-10-21. The source fingerprint for the recorded run is `7eec39d86eb23973cf664bb78d1f79287df866aa5b2286bef92dd92688d7d768`.

## Practice coverage

The complete manifest contains 54 executable core and optional cases. Every case passed in both local runtimes:

| Runtime | Run | Results | Platform |
|---|---|---:|---|
| Docker Desktop | `workspace/runs/20261021T075333Z-302b6a4a/` | 54 passed, 0 failed, 0 blocked | Apple Silicon ARM64; Docker Engine 29.5.2; LinuxKit kernel 6.12.76 |
| Lima rootful Docker | `workspace/runs/20261021T074025Z-d64f902f/` | 54 passed, 0 failed, 0 blocked | ARM64; Ubuntu 24.04; Linux 6.8.0-147; Docker Engine 29.9.1 |

Each run contains the manifest snapshot, summary, command-by-command stdout/stderr and exit status, package/image inventory, logs, and captures required by the exercises. The two image stores have runtime-specific locks in `workspace/.labinf/desktop-images.lock.json` and `workspace/.labinf/lima-images.lock.json`.

Lab 00's readiness probe passed on both runtimes. Each lock was then used for a frozen startup and a real acceptance check: Lab 01 services on Docker Desktop (`workspace/runs/20261021T080308Z-711ad334/`) and the StrongSwan PSK exercise on Lima (`workspace/runs/20261021T080333Z-9f3bd107/`).

## Regression and source checks

- `python3 -m unittest discover -s tests/unit -v`: 9 passed.
- `python3 -m unittest discover -s tests -p test_lab01_environment.py -v`: 11 passed.
- Python compilation, Bash syntax checks, and `docker compose config -q`: passed.
- The complete image build and exercise suite ran on Apple Silicon ARM64 on Docker Desktop and on the Lima Linux kernel.
- CI is configured for native AMD64 (`ubuntu-latest`) and ARM64 (`ubuntu-24.04-arm`) build and acceptance runs. The AMD64 hosted job was not run locally.

## Professor materials

Practice mode prefers supplied materials and uses explicitly labeled replacements for files absent from the available course bundle. The material provenance inventory is `environment/materials/provenance.json`.

Official mode was checked for Lab 02 brute force (`workspace/runs/20261021T075208Z-bb62c546/`) and correctly reported `blocked`: the original `Es1.2 Alice Secret Message.py` and `testbruteforce_enc` are not present. Other missing original archives remain an official-source limitation, especially Lab 03–05 configurations. Lab 02's supplied Mac application and supplied optional ECB/hash-tree files are included and exercised. This report therefore establishes complete practice compatibility for the tested source revision; it does not claim byte-for-byte verification against unavailable professor archives.

## Performance and repeatability

Benchmark commands executed each requested algorithm and size. Their durations are observations recorded in the run logs, not classroom-hardware performance claims. The handout's very slow `nmap -T0` timing exercise is documented as a full manual command; automated acceptance exercises the same scan mode against one port with a short explicit delay.

## Published solution and log updates

On 2026-10-21, each published `LABS/labXX/log.txt` received a post-update acceptance addendum with the current source fingerprint, the lab's case IDs, and the Docker Desktop and Lima results. The original timestamped execution records were preserved as historical evidence.

Each matching solution PDF received a final verification appendix with the same scope and material limitations. The Lab 02 PDF's 29 literal missing-output placeholders were replaced with explicit references to the corresponding revalidated cases and appendix.

These published PDFs and logs are stored in sibling lab directories outside this Git checkout. The detailed, command-by-command evidence remains under the local `workspace/runs/` directory and is not part of the source commit.
