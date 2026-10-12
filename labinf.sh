#!/bin/bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$DIR/environment"
COMPOSE_FILE="$INFRA_DIR/docker-compose.yml"

compose() {
  docker compose -f "$COMPOSE_FILE" "$@"
}

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
  compose up -d --build --wait --wait-timeout 90
  echo ""
  echo -e "${GREEN}${BOLD}[+] Ambiente attivo con successo!${RESET}"
  echo -e "    ${CYAN}• Alice${RESET} (Target Server):   ${BOLD}${LABINF_ALICE_IP:-10.0.2.10}${RESET} (SSH 22, Apache 80, Exim4 25, Mock FTP 21/2121, Challenge 1337)"
  echo -e "    ${CYAN}• Bob${RESET}   (Client):          ${BOLD}${LABINF_BOB_IP:-10.0.2.20}${RESET} (Kali Linux)"
  echo -e "    ${CYAN}• Chuck${RESET} (Attaccante/MITM):  ${BOLD}${LABINF_CHUCK_IP:-10.0.2.30}${RESET} (Kali Linux Suite)"
  echo -e "    ${CYAN}• Workspace Condiviso:${RESET}     ${BOLD}./workspace${RESET} (condiviso con tutti i container)"
  echo ""
  echo -e "Accesso rapido ai terminali:"
  echo -e "    ${BOLD}./labinf.sh chuck${RESET}   -> Shell per Chuck"
  echo -e "    ${BOLD}./labinf.sh bob${RESET}     -> Shell per Bob"
  echo -e "    ${BOLD}./labinf.sh alice${RESET}   -> Shell per Alice"
  echo -e "    ${BOLD}./labinf.sh gui${RESET}     -> Avvia Web GUI (Wireshark) su http://localhost:6080"
}

cmd_stop() {
  check_docker || return 1
  echo -e "${YELLOW}[+] Arresto dei container LABINF...${RESET}"
  compose down
  echo -e "${GREEN}[+] Ambiente arrestato con successo.${RESET}"
}

cmd_restart() {
  check_docker || return 1
  echo -e "${YELLOW}[+] Riavvio dell'ambiente LABINF...${RESET}"
  compose restart
  echo -e "${GREEN}[+] Ambiente riavviato.${RESET}"
}

cmd_status() {
  check_docker || return 1
  echo -e "${CYAN}${BOLD}=== Stato dei Container LABINF ===${RESET}"
  compose ps
}

cmd_build() {
  check_docker || return 1
  echo -e "${BLUE}[+] Compilazione locale delle immagini dei nodi...${RESET}"
  compose build
  echo -e "${GREEN}[+] Build completata con successo.${RESET}"
}

cmd_pull() {
  check_docker || return 1
  echo -e "${BLUE}[+] Download immagini precompilate da GitHub Container Registry...${RESET}"
  compose pull || {
    echo -e "${YELLOW}[!] Immagine remota non ancora disponibile. Procedo con compilazione locale...${RESET}"
    compose build
  }
  echo -e "${GREEN}[+] Immagini pronte!${RESET}"
}

cmd_verify() {
  check_docker || return 1
  local failed=0 service container_id health
  echo -e "${CYAN}${BOLD}[+] Verifica stato dei nodi e salute dei servizi...${RESET}"
  for service in alice bob chuck; do
    container_id="$(compose ps -q "$service")"
    if [[ -z "$container_id" ]]; then
      echo -e "  ${RED}• $service: container non avviato${RESET}"
      failed=1
      continue
    fi
    health="$(docker inspect --format '{{.State.Status}}|{{if .State.Health}}{{.State.Health.Status}}{{end}}' "$container_id")"
    if [[ "$health" != "running|healthy" ]]; then
      echo -e "  ${RED}• $service: $health${RESET}"
      failed=1
    else
      echo -e "  ${GREEN}• $service: $health${RESET}"
    fi
  done

  if ! compose exec -T chuck bash -lc '
    failed=0
    for tool in nmap ettercap labinf-ettercap tshark tcpdump iptables nft swanctl openssl hashdeep ip ping nc curl s-nail ftp host sshpass; do
      if command -v "$tool" >/dev/null 2>&1; then
        printf "  • %-10s OK\n" "$tool"
      else
        printf "  • %-10s NON TROVATO\n" "$tool"
        failed=1
      fi
    done
    exit "$failed"
  '; then
    echo -e "  ${RED}• Tool richiesti mancanti su Chuck${RESET}"
    failed=1
  fi

  if ! compose exec -T chuck bash -lc '
    set -e
    for address in "${LABINF_ALICE_IP:-10.0.2.10}" "${LABINF_BOB_IP:-10.0.2.20}"; do
      ping -c 1 -W 2 "$address" >/dev/null
      echo "  • Ping $address: OK"
    done
    for port in 22 25 80 1337; do
      nc -z -w 2 "${LABINF_ALICE_IP:-10.0.2.10}" "$port"
      echo "  • Alice TCP/$port: OK"
    done
    curl --fail --silent --show-error "http://${LABINF_ALICE_IP:-10.0.2.10}/login.html" >/dev/null
    echo "  • Alice HTTP: OK"
  '; then
    echo -e "  ${RED}• Rete o servizi Alice non verificati${RESET}"
    failed=1
  fi

  if compose exec -T alice python3 /usr/local/bin/not_ftp.py --healthcheck; then
    echo "  • Alice mock FTP prompts (21/2121): OK"
  else
    echo -e "  ${RED}• Alice mock FTP prompts (21/2121): FALLITO${RESET}"
    failed=1
  fi

  if (( failed )); then
    echo -e "${RED}${BOLD}[!] Verifica fallita. Correggi gli errori prima di eseguire gli esercizi.${RESET}"
    return 1
  fi
  echo -e "${GREEN}${BOLD}[+] Verifica completata: nodi, strumenti, rete e servizi sono disponibili.${RESET}"
}

cmd_shell() {
  check_docker || return 1
  target="$1"
  case "$target" in
    chuck) compose exec chuck bash ;;
    bob)   compose exec bob bash ;;
    alice) compose exec alice bash ;;
    *) echo -e "${RED}[!] Nodo sconosciuto: $target${RESET}"; return 1 ;;
  esac
}

cmd_read_email() {
  check_docker || return 1
  echo -e "${CYAN}${BOLD}[+] Contenuto della casella email di Alice (/var/mail/alice):${RESET}"
  compose exec -T alice cat /var/mail/alice
}

cmd_gui() {
  check_docker || return 1
  echo -e "${BLUE}[+] Avvio Web GUI Desktop (noVNC + Wireshark) su Chuck...${RESET}"
  compose exec -d chuck /usr/local/bin/labinf-gui start
  sleep 2
  echo -e "${GREEN}${BOLD}[+] Web GUI attiva!${RESET}"
  echo -e "    Apri nel tuo browser: ${BOLD}http://localhost:6080/vnc.html${RESET}"
  if command -v open >/dev/null 2>&1; then
    open "http://localhost:6080/vnc.html" 2>/dev/null || true
  elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "http://localhost:6080/vnc.html" 2>/dev/null || true
  fi
}

cmd_gui_stop() {
  check_docker || return 1
  echo -e "${YELLOW}[+] Arresto Web GUI Desktop su Chuck...${RESET}"
  compose exec chuck /usr/local/bin/labinf-gui stop
}

# Interactive TUI Menu
show_menu() {
  while true; do
    echo ""
    echo -e "${CYAN}==================================================================${RESET}"
    echo -e "   ${BOLD}POLITECNICO DI TORINO — SICUREZZA DEI SISTEMI INFORMATIVI${RESET}"
    echo -e "             ${MAGENTA}LABINF Docker Multi-Node Environment${RESET}"
    echo -e "${CYAN}==================================================================${RESET}"
    echo -e " ${GREEN}[1]${RESET}  🚀 Avvia ambiente (Alice, Bob, Chuck)"
    echo -e " ${RED}[2]${RESET}  🔴 Shell Chuck (Attaccante / Kali Linux)"
    echo -e " ${BLUE}[3]${RESET}  🔵 Shell Bob (Client legittimo)"
    echo -e " ${CYAN}[4]${RESET}  🟢 Shell Alice (Server target)"
    echo -e " ${YELLOW}[5]${RESET}  🩺 Verifica strumenti e connettività"
    echo -e " ${MAGENTA}[6]${RESET}  📊 Stato dei container e indirizzi IP"
    echo -e " ${BOLD}[7]${RESET}  🔨 Compila / Scarica immagini (Build/Pull)"
    echo -e " ${YELLOW}[8]${RESET}  🛑 Arresta ambiente"
    echo -e " ${CYAN}[9]${RESET}  ✉️  Leggi casella email di Alice (Lab 01)"
    echo -e " ${MAGENTA}[10]${RESET} 🌐 Avvia Web GUI (Wireshark da browser: http://localhost:6080)"
    echo -e " ${RED}[0]${RESET}  ❌ Esci"
    echo -e "${CYAN}==================================================================${RESET}"
    read -rp " Seleziona un'opzione [0-10]: " choice
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
      10) cmd_gui ;;
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
  gui)        cmd_gui ;;
  gui-stop)   cmd_gui_stop ;;
  check)      check_docker && echo -e "${GREEN}[+] Docker daemon attivo e raggiungibile.${RESET}" ;;
  chuck)      cmd_shell chuck ;;
  bob)        cmd_shell bob ;;
  alice)      cmd_shell alice ;;
  read_email) cmd_read_email ;;
  menu|"")    show_menu ;;
  *)
    echo "LABINF Environment Manager (Politecnico di Torino)"
    echo "Uso: ./labinf.sh [start|stop|restart|status|build|pull|verify|gui|gui-stop|check|chuck|bob|alice|read_email|menu]"
    echo "     Se eseguito senza argomenti, apre il menu interattivo."
    exit 1
    ;;
esac
