#!/bin/bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$DIR/environment"
COMPOSE_FILE="$INFRA_DIR/docker-compose.yml"

# ANSI Color codes
BOLD="\033[1m"
RESET="\033[0m"
GREEN="\033[32m"
BLUE="\033[34m"
CYAN="\033[36m"
YELLOW="\033[33m"
RED="\033[31m"
MAGENTA="\033[35m"

check_docker() {
  if ! docker info >/dev/null 2>&1; then
    echo -e "${RED}[!] Errore:${RESET} Il daemon Docker non è in esecuzione o non è raggiungibile."
    echo -e "    Su macOS/Windows: avvia ${BOLD}Docker Desktop${RESET} (/Applications/Docker.app)."
    echo -e "    Su Linux: esegui ${BOLD}sudo systemctl start docker${RESET}."
    return 1
  fi
  return 0
}

cmd_start() {
  check_docker || return 1
  echo -e "${BLUE}[+] Avvio dell'ambiente multi-nodo LABINF (Alice, Bob, Chuck)...${RESET}"
  docker compose -f "$COMPOSE_FILE" up -d
  echo ""
  echo -e "${GREEN}${BOLD}[+] Ambiente attivo con successo!${RESET}"
  echo -e "    ${CYAN}• Alice${RESET} (Target Server):   ${BOLD}10.0.2.10${RESET} (Apache 80, Exim4 25, Mock 2121/1337)"
  echo -e "    ${CYAN}• Bob${RESET}   (Client):          ${BOLD}10.0.2.20${RESET} (Kali Linux)"
  echo -e "    ${CYAN}• Chuck${RESET} (Attaccante/MITM):  ${BOLD}10.0.2.30${RESET} (Kali Linux Suite)"
  echo ""
  echo -e "Accesso rapido ai terminali:"
  echo -e "    ${BOLD}./labinf.sh chuck${RESET}   -> Shell per Chuck"
  echo -e "    ${BOLD}./labinf.sh bob${RESET}     -> Shell per Bob"
  echo -e "    ${BOLD}./labinf.sh alice${RESET}   -> Shell per Alice"
}

cmd_stop() {
  check_docker || return 1
  echo -e "${YELLOW}[+] Arresto dei container LABINF...${RESET}"
  docker compose -f "$COMPOSE_FILE" down
  echo -e "${GREEN}[+] Ambiente arrestato con successo.${RESET}"
}

cmd_restart() {
  check_docker || return 1
  echo -e "${YELLOW}[+] Riavvio dell'ambiente LABINF...${RESET}"
  docker compose -f "$COMPOSE_FILE" restart
  echo -e "${GREEN}[+] Ambiente riavviato.${RESET}"
}

cmd_status() {
  check_docker || return 1
  echo -e "${CYAN}${BOLD}=== Stato dei Container LABINF ===${RESET}"
  docker compose -f "$COMPOSE_FILE" ps
}

cmd_build() {
  check_docker || return 1
  echo -e "${BLUE}[+] Compilazione locale delle immagini dei nodi...${RESET}"
  docker compose -f "$COMPOSE_FILE" build
  echo -e "${GREEN}[+] Build completata con successo.${RESET}"
}

cmd_pull() {
  check_docker || return 1
  echo -e "${BLUE}[+] Download immagini precompilate da GitHub Container Registry...${RESET}"
  docker compose -f "$COMPOSE_FILE" pull || {
    echo -e "${YELLOW}[!] Immagine remota non ancora disponibile. Procedo con compilazione locale...${RESET}"
    docker compose -f "$COMPOSE_FILE" build
  }
  echo -e "${GREEN}[+] Immagini pronte!${RESET}"
}

cmd_verify() {
  check_docker || return 1
  echo -e "${CYAN}${BOLD}[+] Verifica strumenti e connettività su Chuck (10.0.2.30)...${RESET}"
  docker exec labinf_chuck bash -c '
    echo -n "  • Nmap:       "; nmap --version 2>/dev/null | head -n 1 || echo "NON TROVATO"
    echo -n "  • Ettercap:   "; ettercap --version 2>/dev/null | head -n 1 || echo "NON TROVATO"
    echo -n "  • iptables:   "; iptables --version 2>/dev/null || echo "NON TROVATO"
    echo -n "  • nftables:   "; nft --version 2>/dev/null || echo "NON TROVATO"
    echo -n "  • StrongSwan: "; swanctl --version 2>/dev/null || echo "NON TROVATO"
    echo -n "  • OpenSSL:    "; openssl version 2>/dev/null || echo "NON TROVATO"
    echo -n "  • Hashdeep:   "; hashdeep -v 2>/dev/null | head -n 1 || echo "NON TROVATO"
  '
  echo ""
  echo -e "${CYAN}${BOLD}[+] Verifica connettività verso Alice e Bob...${RESET}"
  docker exec labinf_chuck bash -c '
    ping -c 1 -W 1 10.0.2.10 >/dev/null 2>&1 && echo "  • Ping Alice (10.0.2.10): OK" || echo "  • Ping Alice: FALLITO"
    ping -c 1 -W 1 10.0.2.20 >/dev/null 2>&1 && echo "  • Ping Bob   (10.0.2.20): OK" || echo "  • Ping Bob: FALLITO"
  '
  echo ""
  echo -e "${GREEN}${BOLD}[+] Verifica completata!${RESET}"
}

cmd_shell() {
  check_docker || return 1
  target="$1"
  case "$target" in
    chuck) docker exec -it labinf_chuck bash ;;
    bob)   docker exec -it labinf_bob bash ;;
    alice) docker exec -it labinf_alice bash ;;
    *) echo -e "${RED}[!] Nodo sconosciuto: $target${RESET}"; return 1 ;;
  esac
}

cmd_read_email() {
  check_docker || return 1
  echo -e "${CYAN}${BOLD}[+] Contenuto della casella email di Alice (/var/mail/alice):${RESET}"
  docker exec -it labinf_alice cat /var/mail/alice
}

# Interactive TUI Menu
show_menu() {
  while true; do
    echo ""
    echo -e "${CYAN}==================================================================${RESET}"
    echo -e "   ${BOLD}POLITECNICO DI TORINO — SICUREZZA DEI SISTEMI INFORMATIVI${RESET}"
    echo -e "             ${MAGENTA}LABINF Docker Multi-Node Environment${RESET}"
    echo -e "${CYAN}==================================================================${RESET}"
    echo -e " ${GREEN}[1]${RESET} 🚀 Avvia ambiente (Alice, Bob, Chuck)"
    echo -e " ${RED}[2]${RESET} 🔴 Shell Chuck (Attaccante / Kali Linux)"
    echo -e " ${BLUE}[3]${RESET} 🔵 Shell Bob (Client legittimo)"
    echo -e " ${CYAN}[4]${RESET} 🟢 Shell Alice (Server target)"
    echo -e " ${YELLOW}[5]${RESET} 🩺 Verifica strumenti e connettività"
    echo -e " ${MAGENTA}[6]${RESET} 📊 Stato dei container e indirizzi IP"
    echo -e " ${BOLD}[7]${RESET} 🔨 Compila / Scarica immagini (Build/Pull)"
    echo -e " ${YELLOW}[8]${RESET} 🛑 Arresta ambiente"
    echo -e " ${CYAN}[9]${RESET} ✉️  Leggi casella email di Alice (Lab 01)"
    echo -e " ${RED}[0]${RESET} ❌ Esci"
    echo -e "${CYAN}==================================================================${RESET}"
    read -rp " Seleziona un'opzione [0-9]: " choice
    echo ""

    case "$choice" in
      1) cmd_start ;;
      2) cmd_shell chuck ;;
      3) cmd_shell bob ;;
      4) cmd_shell alice ;;
      5) cmd_verify ;;
      6) cmd_status ;;
      7) cmd_build ;;
      8) cmd_stop ;;
      9) cmd_read_email ;;
      0) echo -e "${GREEN}Arrivederci!${RESET}"; exit 0 ;;
      *) echo -e "${RED}[!] Scelta non valida.${RESET}" ;;
    esac
    echo ""
    read -rp "Premi INVIO per continuare..." _dummy
  done
}

# CLI Argument Router
case "$1" in
  start)      cmd_start ;;
  stop)       cmd_stop ;;
  restart)    cmd_restart ;;
  status)     cmd_status ;;
  build)      cmd_build ;;
  pull)       cmd_pull ;;
  verify)     cmd_verify ;;
  check)      check_docker && echo -e "${GREEN}[+] Docker daemon attivo e raggiungibile.${RESET}" ;;
  chuck)      cmd_shell chuck ;;
  bob)        cmd_shell bob ;;
  alice)      cmd_shell alice ;;
  read_email) cmd_read_email ;;
  menu|"")    show_menu ;;
  *)
    echo "LABINF Environment Manager (Politecnico di Torino)"
    echo "Uso: ./labinf.sh [start|stop|restart|status|build|pull|verify|check|chuck|bob|alice|read_email|menu]"
    echo "     Se eseguito senza argomenti, apre il menu interattivo."
    exit 1
    ;;
esac
