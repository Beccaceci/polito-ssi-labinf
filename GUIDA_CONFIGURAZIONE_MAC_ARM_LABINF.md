# Procedura di Configurazione Ambiente LABINF su Mac Apple Silicon (M-series / ARM64)

Questa guida illustra la configurazione completa per riprodurre in locale su macOS il laboratorio **LABINF (Politecnico di Torino)** del corso *Sicurezza dei Sistemi Informativi* (Prof. Cataldo Basile), garantendo piena fedeltà agli attacchi di rete Layer 2 (ARP poisoning con Ettercap, sniffing con Wireshark, scansioni Nmap), firewalling con iptables/nftables e tunnel IPsec/TLS.

---

## 1. Linee Guida Ufficiali del Docente (A.A. 2025/2026)

Come confermato ufficialmente dal docente:
> *"Contrariamente agli anni passati, abbiamo ritenuto inutile condividere una ISO Live preparata per il corso. Riteniamo sia più semplice e comodo scaricare una VM dal sito ufficiale: è più aggiornata, è subito pronta senza dover installare nulla e non crea i tipici problemi di persistenza delle Live ISO (perdita di file al riavvio, elevato consumo di RAM). Non abbiamo alcuna incompatibilità nell'esecuzione delle esercitazioni sulle VM ufficiali di Kali."*

Su Mac Apple Silicon (M1/M2/M3/M4/M5), gli studenti dispongono di due opzioni equivalenti e pienamente supportate:
* **Opzione A (Consigliata per rapidità e automazione): Stack Docker Multi-Nodo (`./labinf.sh`)**
  Avvia istantaneamente i tre nodi isolati (**Alice 10.0.2.10**, **Bob 10.0.2.20**, **Chuck 10.0.2.30**) su rete bridge dedicata con tutti i pacchetti precompilati per tutti i 5 laboratori.
* **Opzione B (Consigliata per interfaccia grafica desktop): Virtualizzazione Nativa con UTM**
  Esegue macchine virtuali Kali Linux ARM64 complete con GUI desktop, Wireshark grafico ed accelerazione hardware tramite `Hypervisor.framework`.

---

## 2. Opzione A: Stack Docker Multi-Nodo (`labinf.sh`)

La cartella `LABS/` include un gestore d'ambiente automatizzato pronto all'uso:

1. **Avvio dell'infrastruttura**:
   ```bash
   ./labinf.sh start
   ```
2. **Accesso immediato alle shell dei nodi**:
   ```bash
   ./labinf.sh chuck   # Shell Kali per l'attaccante/analista
   ./labinf.sh bob     # Shell Kali per il client legittimo
   ./labinf.sh alice   # Shell per il server target
   ```
3. **Verifica dei tool installati**:
   ```bash
   ./labinf.sh verify
   ```
4. **Arresto dell'ambiente**:
   ```bash
   ./labinf.sh stop
   ```

Tutti i tool richiesti dal corso (inclusi `iptables`, `nftables`, `strongswan`, `nmap`, `ettercap`, `openssl`, `hashdeep`) sono già preinstallati nell'immagine unificata.

---

## 3. Opzione B: Macchine Virtuali Kali Linux su UTM

Se preferisci utilizzare macchine virtuali complete con ambiente desktop grafico:

### 3.1 Download dell'Immagine Kali Linux ARM64
* **Download Diretto (Mirror Ufficiale GARR / Kali):**
  * Versione Installer ISO ARM64: [kali-linux-2026.2-installer-arm64.iso](https://kali.mirror.garr.it/kali-images/kali-2026.2/kali-linux-2026.2-installer-arm64.iso)
  * Pagina base releases: [https://www.kali.org/get-kali/#kali-arm](https://www.kali.org/get-kali/#kali-arm)
* **Galleria UTM (Pre-installata):**
  * [Kali Linux ARM64 UTM Gallery](https://mac.getutm.app/gallery/kali-2023)

### 3.2 Configurazione della Macchina Master
1. Apri **UTM** (`/Applications/UTM.app`).
2. Clicca su **+** -> **Virtualize** -> **Linux**.
3. Seleziona la ISO Kali ARM64 scaricata.
4. Alloca le risorse consigliate:
   * **RAM:** 2.5 GB - 3 GB.
   * **CPU:** 2 vCPU.
   * **Disco:** 20-30 GB.
5. Completa l'installazione impostando l'utente `kali` con password `kali`.
6. Nelle impostazioni della VM -> Sezione **Network**, imposta **Network Mode:** `Shared Network` (oppure `Host Only`).

### 3.3 Clonazione Rapida per Topologia Multi-Nodo
Una volta completata l'installazione del master e dei pacchetti:
1. Arresta la macchina virtuale.
2. Clic destro sulla VM in UTM -> **Clone**.
3. Crea i tre nodi di laboratorio:
   * `Kali-Alice` (10.0.2.10 o DHCP)
   * `Kali-Bob` (10.0.2.20 o DHCP)
   * `Kali-Chuck` (10.0.2.30 o DHCP)

---

## 4. Installazione Pacchetti di Laboratorio per UTM (Appendice Completa)

All'interno della macchina virtuale Kali (prima di clonarla), apri un terminale ed esegui l'installazione della suite completa valida per tutti i laboratori del semestre (Lab 01-05):

```bash
sudo apt update && sudo apt install -y \
  # Network Recon & MITM (Lab 01)
  nmap \
  ettercap-text-only \
  ettercap-graphical \
  dsniff \
  tcpdump \
  tshark \
  wireshark \
  netcat-openbsd \
  lynx \
  s-nail \
  dnsutils \
  ftp \
  # Cryptography & Integrity (Lab 02 & Lab 03)
  openssl \
  hashdeep \
  hexedit \
  p7zip-full \
  # Packet Filtering & Firewalling (Lab 04)
  iptables \
  iptables-persistent \
  nftables \
  conntrack \
  ulogd2 \
  # IPsec & Tunneling (Lab 05)
  strongswan \
  strongswan-swanctl \
  libstrongswan-extra-plugins \
  ptunnel \
  httptunnel \
  # Support Utilities
  apache2 \
  vsftpd \
  python3 \
  net-tools \
  iproute2 \
  iputils-ping \
  procps \
  curl \
  wget \
  nano
```
