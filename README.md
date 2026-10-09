# Politecnico di Torino — LABINF Multi-Node Cybersecurity Environment

[![Docker Multi-Arch](https://img.shields.io/badge/Docker-linux%2Famd64%20%7C%20linux%2Farm64-blue?logo=docker)](https://github.com/Beccaceci/polito-ssi-labinf)
[![Kali Linux](https://img.shields.io/badge/OS-Kali%20Linux%20Rolling-557C94?logo=kalilinux)](https://www.kali.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Politecnico di Torino](https://img.shields.io/badge/PoliTO-Sicurezza%20dei%20Sistemi%20Informativi-002D62)](https://www.polito.it/)

Ambiente multi-nodo dockerizzato e riproducibile per lo svolgimento delle esercitazioni di laboratorio del corso di **Sicurezza dei Sistemi Informativi (01UDUOV)** presso il **Politecnico di Torino** (Prof. Cataldo Basile).

Riproduce fedelmente la topologia di rete del **LABINF** consentendo di effettuare attacchi Layer 2 (ARP poisoning, sniffing di credenziali, spoofing), analisi di pacchetti, firewalling con `iptables`/`nftables` e configurazione di tunnel `IPsec`/`TLS` senza la necessità di avviare 3 macchine virtuali complete e pesanti.

---

## 🏗️ Topologia di Rete

I nodi sono collegati sulla sottorete isolata `10.0.2.0/24` (con gateway `10.0.2.1`):

```
                       +-------------------------+
                       |    Gateway Virtuale     |
                       |        10.0.2.1         |
                       +------------+------------+
                                    |
            +-----------------------+-----------------------+
            |                       |                       |
+-----------v-----------+   +-------v-------+   +-----------v-----------+
|     labinf_alice      |   |  labinf_bob   |   |     labinf_chuck      |
|       10.0.2.10       |   |   10.0.2.20   |   |       10.0.2.30       |
|                       |   |               |   |                       |
|   Target Server:      |   |   Client:     |   |   Attaccante / MITM:  |
|   • Apache HTTPD (80) |   |   • Kali Base |   |   • Kali Suite        |
|   • Exim4 SMTP (25)   |   |   • User Bob  |   |   • Nmap / Ettercap   |
|   • Mock FTP (2121)   |   |               |   |   • iptables / IPsec  |
|   • Challenge (1337)  |   |               |   |   • Wireshark CLI     |
+-----------------------+   +---------------+   +-----------------------+
```

---

## ⚡ Quickstart (Avvio Rapido in 3 Passi)

### Prerequisiti
* **Docker Desktop** (su macOS / Windows) oppure **Docker Engine** + **Docker Compose** (su Linux).

### 1. Clona la repository
```bash
git clone https://github.com/Beccaceci/polito-ssi-labinf.git
cd polito-ssi-labinf
```

### 2. Avvia l'ambiente
Puoi utilizzare l'interfaccia a menu interattivo:
```bash
./labinf.sh
```
oppure avviare direttamente i container in background:
```bash
./labinf.sh start
```

### 3. Entra nei terminali dei nodi
```bash
./labinf.sh chuck   # Terminale di Chuck (Attaccante)
./labinf.sh bob     # Terminale di Bob (Client)
./labinf.sh alice   # Terminale di Alice (Server)
```

---

## 💻 CLI & Menu Interattivo (`labinf.sh`)

Eseguendo `./labinf.sh` senza argomenti, si apre la comoda interfaccia TUI a colori:

```text
==================================================================
   POLITECNICO DI TORINO — SICUREZZA DEI SISTEMI INFORMATIVI
             LABINF Docker Multi-Node Environment
==================================================================
 [1] 🚀 Avvia ambiente (Alice, Bob, Chuck)
 [2] 🔴 Shell Chuck (Attaccante / Kali Linux)
 [3] 🔵 Shell Bob (Client legittimo)
 [4] 🟢 Shell Alice (Server target)
 [5] 🩺 Verifica strumenti e connettività
 [6] 📊 Stato dei container e indirizzi IP
 [7] 🔨 Compila / Scarica immagini (Build/Pull)
 [8] 🛑 Arresta ambiente
 [9] ✉️  Leggi casella email di Alice (Lab 01)
 [0] ❌ Esci
==================================================================
```

### Comandi da Riga di Comando (Scriptabili)
| Comando | Descrizione |
| :--- | :--- |
| `./labinf.sh start` | Avvia i container e la rete `10.0.2.0/24` |
| `./labinf.sh stop` | Arresta e rimuove i container preservando le immagini |
| `./labinf.sh restart` | Riavvia l'intero stack |
| `./labinf.sh status` | Mostra lo stato e le porte aperte |
| `./labinf.sh build` | Compila localmente l'immagine Kali con tutti i pacchetti |
| `./labinf.sh pull` | Scarica l'immagine precompilata da GitHub Container Registry |
| `./labinf.sh verify` | Esegue un sanity check su tutti i tool (`nmap`, `iptables`, ecc.) |
| `./labinf.sh chuck` | Apre una shell bash nel nodo attaccante `10.0.2.30` |
| `./labinf.sh bob` | Apre una shell bash nel nodo client `10.0.2.20` |
| `./labinf.sh alice` | Apre una shell bash nel server target `10.0.2.10` |
| `./labinf.sh read_email` | Visualizza la casella email `/var/mail/alice` |

---

## 📚 Copertura dei Laboratori del Corso

| Laboratorio | Tematiche Principali | Supporto in questo Ambiente |
| :--- | :--- | :--- |
| **Lab 01: Attacchi di Rete** | Nmap scans, OS fingerprinting, ARP Poisoning (Ettercap), HTTP Sniffing, SMTP Sniffing. | ✅ **Pieno**: Servizi vulnerabili attivi su Alice; sniffing ed Ettercap L2 funzionanti su Chuck. |
| **Lab 02: Crittografia di Base** | Cifrari simmetrici (AES, DES, RC4), RSA (PKCS#1, CRT), Curve Ellittiche (ECDSA), Hash (MD5, SHA, IHA), Brute Force. | ✅ **Pieno**: Suite `openssl`, script Python e tool di benchmark inclusi. |
| **Lab 03: Crittografia Applicata** | MAC/HMAC, PBKDF2, PKI, Certificate Authority (CA), CSR, certificati X.509, CRL. | ✅ **Pieno**: Comandi OpenSSL per PKI e gestione certificati. |
| **Lab 04: Firewalling** | Personal firewall, filtri stateless/stateful, conntrack, NAT, DMZ, forwarding multi-sottorete. | ✅ **Pieno**: Capacità `NET_ADMIN`, `NET_RAW` e sysctl `net.ipv4.ip_forward=1` abilitate. |
| **Lab 05: IPsec e TLS** | StrongSwan (`swanctl`), negoziazione IKEv2, tunnel/transport IPsec, analisi handshake TLS. | ✅ **Pieno**: Demone StrongSwan e plugin crittografici inclusi. |

---

## 🍎 Perché Docker su Mac Apple Silicon (M1/M2/M3/M4/M5)?

Nei laboratori ufficiali viene originariamente proposto Oracle VM VirtualBox su architettura Intel/x86_64. Su processori Mac Apple Silicon:
1. **VirtualBox x86_64** non supporta la virtualizzazione hardware nativa e causa pesantissimi rallentamenti di emulazione.
2. Eseguire **3 macchine virtuali complete** contemporaneamente richiede 8–12 GB di RAM dedicati solo agli OS guest.
3. Questo ambiente Docker sfrutta il motore nativo Linux ARM64: **l'intero cluster a 3 nodi consuma meno di 1.5 GB di RAM**, si avvia in 2 secondi ed è pronto all'uso.

> **Nota su UTM:** Se necessiti dell'interfaccia grafica desktop di Wireshark anziché da terminale, puoi anche installare macchine virtuali complete su **UTM** seguendo la nostra guida dedicata.

---

## 🤝 Contribuire
Pull request, issue o segnalazioni di compatibilità per nuovi laboratori sono benvenute!

---

## 📄 Licenza
Rilasciato sotto licenza [MIT](LICENSE).
