# LABINF laboratory environment

Docker scenarios for the Politecnico di Torino Information Systems Security laboratories, with exercise acceptance checks and recorded evidence. The supplied handout versions are tracked in [the exercise manifest](docs/exercises.json). See [the implementation plan](docs/implementation-plan.md) and [command compatibility](docs/compatibility.md).

Requires Docker Engine/Desktop with Compose v2 or later and host Python 3.10+. Apple Silicon uses native ARM64 containers. AMD64 images are built/tested separately in CI. Docker Desktop must be running before invoking node commands.

```bash
chmod +x labinf.sh
./labinf.sh build --lab 03
./labinf.sh start --lab 03
./labinf.sh shell alice --lab 03
./labinf.sh shell alice --lab 03 --root
./labinf.sh verify --lab 03
./labinf.sh stop --lab 03
```

PowerShell uses the same controller: `.\labinf.ps1 start --lab 03`. `labinf.bat` delegates to it. Launcher errors propagate to the host exit status. Bash/PowerShell wrappers require Python 3.10 or newer; Python dependencies for exercises are inside the containers.

## Scenarios

| Lab | Scenario | Roles and packet path |
|---|---|---|
| 01 | lan (default) | Existing Alice target, Bob and Chuck on the course bridge |
| 01 | dns | Bob → gateway → DNS/web; Alice intercepts Bob–gateway traffic |
| 02 | lan | Complete crypto nodes plus the supplied supplementary Mac application |
| 03 | lan | Complete crypto/PKI nodes and explicit exchange storage |
| 04 | shared (default) | Host routes force Alice ↔ Frank ↔ Bob on a shared LAN |
| 04 | routed | Alice and Bob on different LANs; Frank has two interfaces |
| 05 | lan (default) | Endpoint IPsec/IKE/TLS and Chuck for interception |
| 05 | site | Alice → Gateway A → Gateway B → Bob on three networks |

```bash
./labinf.sh start --lab 04 --scenario routed
./labinf.sh shell frank --lab 04 --scenario routed --root
./labinf.sh verify --lab 04 --scenario routed
./labinf.sh verify --all --build
./labinf.sh coverage
```

`verify` requires an already running scenario. Add `--start` to create it for the run; `--all` starts each scenario in sequence. Automatically started scenarios are removed after verification unless `--keep` is specified. An interrupted/failed exercise must be reset before manual reuse. `stop` retains container configuration; `reset` recreates containers and preserves saved node data/evidence. `build` is an intentional toolchain rebuild; packages resolve from the distribution repository and every run records the resulting versions and immutable local image IDs.

The existing Lab 01 commands (`start`, `alice`, `bob`, `chuck`, `read_email`) remain available. `LABINF_SUBNET`, gateway and node-IP overrides remain supported for that baseline. New scenarios use per-lab subnets; set `LABINF_NETWORK_OCTET` to resolve conflicts. Port/subnet conflicts fail before startup.

## Services, workspaces and GUI

Inside a complete exercise node:

```bash
sudo labinf-service status apache2
sudo labinf-service restart ssh
sudo labinf-service start ipsec
```

This controls real Supervisor processes. Apache uses `/etc/apache2` and `/var/www/html`. Each exercise node has its own persistent `/workspace`, also accessible through `/home/kali/workspace`. `/exchange` is shared deliberately between nodes. Host files live in `workspace/nodes/` and `workspace/exchange/`. Generated state, keys, imports and captures are ignored by Git.

```bash
./labinf.sh gui chuck --lab 03
./labinf.sh gui alice --lab 04 --scenario routed
```

Open the printed URL. GUI binds to loopback, with default ports 6080 for the legacy Lab 01 baseline and 6080+lab number for newer scenarios. Override with `LABINF_GUI_HOST_PORT`. The supplementary Lab 02 app binds to `http://127.0.0.1:15002`; override with `LABINF_APP_HOST_PORT`. Inside Lab 02 nodes it is `http://lab02-app:5000`.

## Professor materials and practice replacements

```bash
./labinf.sh materials import --lab 03 --source '/path/to/03lab - materiale.zip'
./labinf.sh verify --lab 03 --mode practice
./labinf.sh verify --lab 03 --mode official
```

Imports preserve files, record SHA256 hashes and never overwrite replacement files. Conflicting original revisions or changed imported files fail explicitly. The supplied Lab 02 Mac application and optional underscore-named ECB/tree files are included with provenance. Missing core RC4/IHA, AEAD, Apache and StrongSwan materials have labeled practice replacements. Default practice mode uses originals when available and records every replacement. Official mode blocks affected exercises until the original material is available.

## Verification output

New runs are saved to `workspace/runs/<UTC-id>/`. Each lab/scenario contains `log.txt`, structured command evidence and image inventory; captures are collected when required. A run summary reports every passed, failed or blocked case and its material provenance. `coverage` uses results matching the current source fingerprint. A nonzero verifier exit means acceptance is incomplete. Existing published solution PDFs and laboratory logs are preserved.

To run selected checks and their dependencies:

```bash
./labinf.sh verify --lab 05 --case ike_psk --start
./labinf.sh verify --lab 02 --case mac_app --start
python3 -m unittest discover -s tests/unit -v
```

A four-bit brute-force exercise with unknown binary plaintext has sixteen plausible decryptions; tests preserve that lesson. OpenSSL `enc` rejecting AEAD, revoked certificates, failed authentication and firewall drops are intentional outcomes with assertions. Shortened T0 scan timing and container command equivalents are explained in the compatibility guide.

After a complete practice run, `./labinf.sh freeze --runtime desktop` (or `lima`) records the accepted local image IDs. Add `--frozen` to `start` or `verify` to require those exact images and skip builds. The lock is tied to the current source fingerprint; rebuild and freeze again after changing implementation files.

## Alternate Linux kernel through Lima

On macOS, install Lima (`brew install lima`) and initialize the dedicated rootful Docker VM:

```bash
./labinf.sh runtime-init --runtime lima
./labinf.sh build --lab 05 --runtime lima
./labinf.sh verify --lab 05 --runtime lima --start
```

The VM pins its Ubuntu image and SHA256, mounts this project, and loads Netfilter/XFRM modules. The controller selects its Docker socket per invocation, without switching the global Docker context. Image builds and node work use the same repository. Desktop and Lima have separate Docker image stores. Select distinct published host ports when both runtimes are active. Run the actual capability tests on the selected kernel; the existence of the VM is not proof that IPsec passed.

If an existing service occupies a published port, set `LABINF_GUI_HOST_PORT` and, for Lab 02, `LABINF_APP_HOST_PORT` to available loopback ports. The controller checks conflicts before startup and reports the specific port.

## Validation status

Use `./labinf.sh coverage` and `docs/validation.md` for recorded results and remaining limitations. Installed tools, old transcripts, and build success alone do not establish complete exercise compatibility. CI keeps the original Lab 01 regression suite, executes the scenario acceptance suite on native AMD64 and ARM64 Linux runners, and uploads logs even on failure.
