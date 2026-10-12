"""End-to-end acceptance checks for the isolated Lab 01 Compose scenario."""

from __future__ import annotations

import os
import subprocess
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPOSE_FILE = ROOT / "environment" / "docker-compose.yml"
PROJECT = f"labinf-test-{os.getpid()}"
ALICE_IP = "10.88.2.10"
BOB_IP = "10.88.2.20"
CHUCK_IP = "10.88.2.30"
MAIL_TOKEN = f"labinf-test-{os.getpid()}"
RUN_ENV: dict[str, str] | None = None


def command(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=check,
        timeout=300,
        env=RUN_ENV,
    )


def compose(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return command(
        "docker",
        "compose",
        "--project-name",
        PROJECT,
        "--file",
        str(COMPOSE_FILE),
        *args,
        check=check,
    )


class Lab01EnvironmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        global RUN_ENV
        info = command("docker", "info", check=False)
        if info.returncode:
            raise RuntimeError("Docker daemon is required for Lab 01 integration tests")

        cls.compose_env = {
            **os.environ,
            "LABINF_SUBNET": "10.88.2.0/24",
            "LABINF_GATEWAY": "10.88.2.1",
            "LABINF_ALICE_IP": ALICE_IP,
            "LABINF_BOB_IP": BOB_IP,
            "LABINF_CHUCK_IP": CHUCK_IP,
            "LABINF_GUI_HOST_PORT": "16080",
            "COMPOSE_PROJECT_NAME": PROJECT,
        }
        RUN_ENV = cls.compose_env
        config = subprocess.run(
            ["docker", "compose", "--project-name", PROJECT, "-f", str(COMPOSE_FILE), "config", "-q"],
            cwd=ROOT,
            env=cls.compose_env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        if config.returncode:
            raise RuntimeError(f"Compose config failed:\n{config.stdout}")

        up = subprocess.run(
            [
                "docker", "compose", "--project-name", PROJECT, "-f", str(COMPOSE_FILE),
                "up", "--build", "--detach", "--wait", "--wait-timeout", "300",
            ],
            cwd=ROOT,
            env=cls.compose_env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=1800,
        )
        if up.returncode:
            subprocess.run(
                ["docker", "compose", "--project-name", PROJECT, "-f", str(COMPOSE_FILE), "logs", "--no-color"],
                cwd=ROOT,
                env=cls.compose_env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            raise RuntimeError(f"Compose startup/build failed:\n{up.stdout}")

    @classmethod
    def tearDownClass(cls) -> None:
        subprocess.run(
            ["docker", "compose", "--project-name", PROJECT, "-f", str(COMPOSE_FILE), "down", "--volumes", "--remove-orphans"],
            cwd=ROOT,
            env=getattr(cls, "compose_env", os.environ),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=120,
        )

    def in_node(self, service: str, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return compose("exec", "--no-TTY", service, *args, check=check)

    def test_all_nodes_are_ready_and_verify_passes(self) -> None:
        result = command("bash", "./labinf.sh", "verify", check=False)
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_assigned_service_ports_are_reachable(self) -> None:
        result = self.in_node(
            "chuck", "bash", "-lc",
            f"set -e; for port in 22 25 80 1337; do nc -z -w 2 {ALICE_IP} $port; done",
        )
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_all_lab_hosts_can_ping_each_other_and_inspect_neighbors(self) -> None:
        addresses = {"alice": ALICE_IP, "bob": BOB_IP, "chuck": CHUCK_IP}
        for source, source_ip in addresses.items():
            link = self.in_node(source, "ip", "-o", "link", "show", "dev", "eth0")
            self.assertIn("mtu 9000", link.stdout)
            offloads = self.in_node(source, "ethtool", "-k", "eth0")
            self.assertIn(
                "generic-segmentation-offload: off", offloads.stdout,
                f"{source} started with GSO enabled:\n{offloads.stdout}",
            )
            self.assertIn(
                "tcp-segmentation-offload: off", offloads.stdout,
                f"{source} started with TSO enabled:\n{offloads.stdout}",
            )
            for target, target_ip in addresses.items():
                if source == target:
                    continue
                result = self.in_node(
                    source, "sh", "-c",
                    f"ping -c 1 -W 2 {target_ip} && ip neigh show {target_ip}",
                    check=False,
                )
                self.assertEqual(
                    result.returncode, 0,
                    f"{source} ({source_ip}) could not reach {target} ({target_ip}): {result.stdout}",
                )
                self.assertIn(target_ip, result.stdout)

    def test_alice_netstat_and_ssh_login(self) -> None:
        listeners = compose("exec", "--no-TTY", "--user", "0", "alice", "netstat", "-ltupn")
        for port in (21, 22, 25, 80, 1337, 2121):
            self.assertIn(f":{port} ", listeners.stdout)

        login = self.in_node(
            "bob", "sshpass", "-p", "alice", "ssh",
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "-o", "ConnectTimeout=5",
            f"alice@{ALICE_IP}", "id", "-un", check=False,
        )
        self.assertEqual(login.returncode, 0, login.stdout)
        self.assertIn("alice", login.stdout)

    def test_arp_mitm_updates_neighbor_and_forwards_http(self) -> None:
        started = compose(
            "exec", "--detach", "chuck", "labinf-ettercap", "-T", "-q",
            "-M", "arp", f"/{ALICE_IP}//", f"/{BOB_IP}//", check=False,
        )
        self.assertEqual(started.returncode, 0, started.stdout)
        try:
            mac_result = self.in_node("chuck", "cat", "/sys/class/net/eth0/address")
            chuck_mac = mac_result.stdout.strip().lower()
            self.assertTrue(chuck_mac)

            deadline = time.monotonic() + 30
            observed = ""
            while time.monotonic() < deadline:
                probe = self.in_node(
                    "bob", "bash", "-lc",
                    f"ping -c 1 -W 1 {ALICE_IP} >/dev/null 2>&1; ip neigh show {ALICE_IP} dev eth0",
                    check=False,
                )
                observed = probe.stdout.strip().lower()
                if chuck_mac in observed:
                    break
                time.sleep(1)
            self.assertIn(chuck_mac, observed, f"Bob's ARP entry was not poisoned: {observed}")

            ping = self.in_node(
                "bob", "ping", "-c", "2", "-W", "2", ALICE_IP, check=False
            )
            self.assertEqual(ping.returncode, 0, ping.stdout)
            self.assertNotIn("Redirect Host", ping.stdout, ping.stdout)

            forwarding = self.in_node("chuck", "sudo", "-n", "sysctl", "-n", "net.ipv4.ip_forward")
            self.assertEqual(forwarding.stdout.strip(), "1", "MITM launcher must preserve kernel forwarding")
            redirects = self.in_node(
                "chuck", "sudo", "-n", "sysctl", "-n", "net.ipv4.conf.eth0.send_redirects"
            )
            self.assertEqual(redirects.stdout.strip(), "0", "Chuck must not redirect victims around the MITM")
            offloads = self.in_node("chuck", "ethtool", "-k", "eth0")
            self.assertIn("generic-segmentation-offload: off", offloads.stdout)
            self.assertIn("tcp-segmentation-offload: off", offloads.stdout)

            forward = self.in_node(
                "bob", "curl", "--max-time", "5", "--fail", "--silent",
                f"http://{ALICE_IP}/login.html", check=False
            )
            self.assertEqual(forward.returncode, 0, forward.stdout)

            encrypted_login = self.in_node(
                "bob", "sshpass", "-p", "alice", "ssh",
                "-o", "StrictHostKeyChecking=no",
                "-o", "UserKnownHostsFile=/dev/null",
                "-o", "PreferredAuthentications=password",
                "-o", "PubkeyAuthentication=no",
                "-o", "ConnectTimeout=5",
                f"alice@{ALICE_IP}", "id", "-un", check=False,
            )
            self.assertEqual(encrypted_login.returncode, 0, encrypted_login.stdout or "")
            self.assertIn("alice", encrypted_login.stdout)
        finally:
            compose("exec", "--detach", "chuck", "pkill", "-INT", "-x", "ettercap", check=False)

    def test_web_challenge_is_reachable_from_index(self) -> None:
        result = self.in_node(
            "bob", "python3", "-c",
            f"import urllib.request; base='http://{ALICE_IP}'; "
            "index=urllib.request.urlopen(base+'/index.html',timeout=5).read().decode(); "
            "assert 'secret.html' in index; "
            "secret=urllib.request.urlopen(base+'/secret.html',timeout=5).read().decode(); "
            "assert 'SSI{p0rt_scann3r5_4r3_4w3s0m3}' in secret",
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_mock_ftp_answers_on_standard_and_legacy_ports(self) -> None:
        code = (
            "import socket\n"
            f"for port in (21, 2121):\n"
            f"    with socket.create_connection(('{ALICE_IP}', port), timeout=5) as s:\n"
            "        s.settimeout(5)\n"
            "        assert s.recv(256) == b'Enter your username: '\n"
            "        s.sendall(b'bob\\r\\n')\n"
            "        assert s.recv(256) == b'Enter your password: '\n"
            "        s.sendall(b'test\\r\\n')\n"
            "        assert b'stole your credentials' in s.recv(512)\n"
        )
        result = self.in_node("bob", "python3", "-c", code, check=False)
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_nmap_service_detection_does_not_stall_on_mock_ftp(self) -> None:
        result = self.in_node(
            "bob", "timeout", "30", "nmap", "-sV", "-Pn", "-p", "21", ALICE_IP,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("21/tcp open", result.stdout)

    def test_challenge_tcp_service_returns_same_flag(self) -> None:
        code = (
            "import socket\n"
            f"with socket.create_connection(('{ALICE_IP}', 1337), timeout=5) as s:\n"
            "    s.settimeout(5)\n"
            "    assert b'Press enter' in s.recv(256)\n"
            "    s.sendall(b'\\n')\n"
            "    data=b''\n"
            "    while True:\n"
            "        chunk=s.recv(4096)\n"
            "        if not chunk: break\n"
            "        data += chunk\n"
            "    assert b'SSI{p0rt_scann3r5_4r3_4w3s0m3}' in data\n"
        )
        result = self.in_node("bob", "python3", "-c", code, check=False)
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_smtp_mail_is_delivered_to_alice_mailbox(self) -> None:
        code = (
            "import smtplib\n"
            f"smtp=smtplib.SMTP('{ALICE_IP}',25,timeout=5)\n"
            f"smtp.sendmail('bob@kali',['alice@kali'],'Subject: {MAIL_TOKEN}\\n\\n{MAIL_TOKEN}\\n')\n"
            "smtp.quit()\n"
        )
        sent = self.in_node("bob", "python3", "-c", code, check=False)
        self.assertEqual(sent.returncode, 0, sent.stdout)

        deadline = time.monotonic() + 20
        last = ""
        while time.monotonic() < deadline:
            read = self.in_node("alice", "grep", "-F", MAIL_TOKEN, "/var/mail/alice", check=False)
            if read.returncode == 0:
                return
            last = read.stdout
            time.sleep(1)
        self.fail(f"SMTP message did not appear in /var/mail/alice: {last}")

    def test_verify_fails_when_a_node_is_stopped(self) -> None:
        stopped = compose("stop", "bob", check=False)
        self.assertEqual(stopped.returncode, 0, stopped.stdout)
        try:
            result = command("bash", "./labinf.sh", "verify", check=False)
            self.assertNotEqual(result.returncode, 0, result.stdout)
            self.assertIn("container non avviato", result.stdout)
        finally:
            compose("up", "--detach", "--wait", "--wait-timeout", "60", "bob", check=False)


if __name__ == "__main__":
    unittest.main(verbosity=2)
