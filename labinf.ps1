<#
.SYNOPSIS
    LABINF Environment Manager (Politecnico di Torino) for Windows PowerShell.
.DESCRIPTION
    Automates the multi-node cybersecurity environment (Alice, Bob, Chuck)
    on Docker Desktop (WSL2 backend) for the Information Systems Security course.
#>

[CmdletBinding()]
param(
    [Parameter(Position=0)]
    [ValidateSet("start", "stop", "restart", "status", "build", "pull", "verify", "gui", "gui-stop", "check", "chuck", "bob", "alice", "read_email", "menu", "")]
    [string]$Command = ""
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ComposeFile = Join-Path $ScriptDir "environment\docker-compose.yml"

function Test-Docker {
    try {
        $null = docker info 2>&1
        if ($LASTEXITCODE -ne 0) {
            throw "Docker daemon unreachable."
        }
        return $true
    }
    catch {
        Write-Host "`n[!] Errore: Docker Desktop non è in esecuzione o non è raggiungibile." -ForegroundColor Red
        Write-Host "    1. Avvia 'Docker Desktop' dal menu Start di Windows." -ForegroundColor Yellow
        Write-Host "    2. Assicurati che nelle impostazioni di Docker Desktop sia attivo il backend 'WSL 2'." -ForegroundColor Yellow
        Write-Host "    3. Se WSL non è aggiornato, apri un terminale come Amministratore ed esegui: wsl --update`n" -ForegroundColor Yellow
        return $false
    }
}

function Invoke-Start {
    if (-not (Test-Docker)) { return }
    Write-Host "`n[+] Avvio dell'ambiente multi-nodo LABINF (Alice, Bob, Chuck)..." -ForegroundColor Cyan
    docker compose -f $ComposeFile up -d
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[!] Errore durante l'avvio dei container." -ForegroundColor Red
        return
    }
    Write-Host "`n[+] Ambiente attivo con successo!" -ForegroundColor Green
    Write-Host "    • Alice (Target Server):     10.0.2.10 (Apache 80, Exim4 25, Mock 2121/1337)" -ForegroundColor Cyan
    Write-Host "    • Bob   (Client):            10.0.2.20 (Kali Linux)" -ForegroundColor Cyan
    Write-Host "    • Chuck (Attaccante/MITM):    10.0.2.30 (Kali Linux Suite)" -ForegroundColor Cyan
    Write-Host "    • Workspace Condiviso:       .\workspace (cartella condivisa con tutti i nodi)`n" -ForegroundColor Cyan
    Write-Host "Accesso rapido ai terminali:"
    Write-Host "    .\labinf.ps1 chuck      -> Shell per Chuck" -ForegroundColor White
    Write-Host "    .\labinf.ps1 bob        -> Shell per Bob" -ForegroundColor White
    Write-Host "    .\labinf.ps1 alice      -> Shell per Alice" -ForegroundColor White
    Write-Host "    .\labinf.ps1 gui        -> Avvia Web GUI (Wireshark) su http://localhost:6080`n" -ForegroundColor White
}

function Invoke-Stop {
    if (-not (Test-Docker)) { return }
    Write-Host "`n[+] Arresto dei container LABINF..." -ForegroundColor Yellow
    docker compose -f $ComposeFile down
    Write-Host "[+] Ambiente arrestato con successo.`n" -ForegroundColor Green
}

function Invoke-Restart {
    if (-not (Test-Docker)) { return }
    Write-Host "`n[+] Riavvio dell'ambiente LABINF..." -ForegroundColor Yellow
    docker compose -f $ComposeFile restart
    Write-Host "[+] Ambiente riavviato.`n" -ForegroundColor Green
}

function Invoke-Status {
    if (-not (Test-Docker)) { return }
    Write-Host "`n=== Stato dei Container LABINF ===" -ForegroundColor Cyan
    docker compose -f $ComposeFile ps
}

function Invoke-Build {
    if (-not (Test-Docker)) { return }
    Write-Host "`n[+] Compilazione locale delle immagini dei nodi..." -ForegroundColor Cyan
    docker compose -f $ComposeFile build
    Write-Host "[+] Build completata con successo.`n" -ForegroundColor Green
}

function Invoke-Pull {
    if (-not (Test-Docker)) { return }
    Write-Host "`n[+] Download immagini precompilate da GitHub Container Registry..." -ForegroundColor Cyan
    try {
        docker compose -f $ComposeFile pull
    } catch {
        Write-Host "[!] Immagine remota non ancora pronta. Procedo con la build locale..." -ForegroundColor Yellow
        docker compose -f $ComposeFile build
    }
    Write-Host "[+] Immagini pronte!`n" -ForegroundColor Green
}

function Invoke-Verify {
    if (-not (Test-Docker)) { return }
    Write-Host "`n[+] Verifica strumenti e connettività su Chuck (10.0.2.30)..." -ForegroundColor Cyan
    docker exec labinf_chuck bash -c '
        echo -n "  • Nmap:       "; nmap --version 2>/dev/null | head -n 1 || echo "NON TROVATO"
        echo -n "  • Ettercap:   "; ettercap --version 2>/dev/null | head -n 1 || echo "NON TROVATO"
        echo -n "  • iptables:   "; iptables --version 2>/dev/null || echo "NON TROVATO"
        echo -n "  • nftables:   "; nft --version 2>/dev/null || echo "NON TROVATO"
        echo -n "  • StrongSwan: "; swanctl --version 2>/dev/null || echo "NON TROVATO"
        echo -n "  • OpenSSL:    "; openssl version 2>/dev/null || echo "NON TROVATO"
        echo -n "  • Hashdeep:   "; hashdeep -v 2>/dev/null | head -n 1 || echo "NON TROVATO"
        echo -n "  • Wireshark:  "; wireshark --version 2>/dev/null | head -n 1 || echo "NON TROVATO"
    '
    Write-Host "`n[+] Verifica connettività verso Alice e Bob..." -ForegroundColor Cyan
    docker exec labinf_chuck bash -c '
        ping -c 1 -W 1 10.0.2.10 >/dev/null 2>&1 && echo "  • Ping Alice (10.0.2.10): OK" || echo "  • Ping Alice: FALLITO"
        ping -c 1 -W 1 10.0.2.20 >/dev/null 2>&1 && echo "  • Ping Bob   (10.0.2.20): OK" || echo "  • Ping Bob: FALLITO"
    '
    Write-Host "`n[+] Verifica completata!`n" -ForegroundColor Green
}

function Invoke-Shell([string]$Target) {
    if (-not (Test-Docker)) { return }
    switch ($Target) {
        "chuck" { docker exec -it labinf_chuck bash }
        "bob"   { docker exec -it labinf_bob bash }
        "alice" { docker exec -it labinf_alice bash }
        Default { Write-Host "[!] Nodo sconosciuto: $Target" -ForegroundColor Red }
    }
}

function Invoke-ReadEmail {
    if (-not (Test-Docker)) { return }
    Write-Host "`n[+] Contenuto della casella email di Alice (/var/mail/alice):" -ForegroundColor Cyan
    docker exec -it labinf_alice cat /var/mail/alice
}

function Invoke-Gui {
    if (-not (Test-Docker)) { return }
    Write-Host "`n[+] Avvio Web GUI Desktop (noVNC + Wireshark) su Chuck..." -ForegroundColor Cyan
    docker exec -d labinf_chuck /usr/local/bin/labinf-gui start
    Start-Sleep -Seconds 2
    Write-Host "[+] Web GUI attiva!" -ForegroundColor Green
    Write-Host "    Apri nel tuo browser: http://localhost:6080/vnc.html`n" -ForegroundColor White
    Start-Process "http://localhost:6080/vnc.html"
}

function Invoke-GuiStop {
    if (-not (Test-Docker)) { return }
    Write-Host "`n[+] Arresto Web GUI Desktop su Chuck..." -ForegroundColor Yellow
    docker exec -it labinf_chuck /usr/local/bin/labinf-gui stop
    Write-Host "[+] Web GUI arrestata.`n" -ForegroundColor Green
}

function Show-Menu {
    while ($true) {
        Write-Host ""
        Write-Host "==================================================================" -ForegroundColor Cyan
        Write-Host "   POLITECNICO DI TORINO — SICUREZZA DEI SISTEMI INFORMATIVI" -ForegroundColor White
        Write-Host "             LABINF Docker Multi-Node Environment (Windows)" -ForegroundColor Magenta
        Write-Host "==================================================================" -ForegroundColor Cyan
        Write-Host " [1]  🚀 Avvia ambiente (Alice, Bob, Chuck)" -ForegroundColor Green
        Write-Host " [2]  🔴 Shell Chuck (Attaccante / Kali Linux)" -ForegroundColor Red
        Write-Host " [3]  🔵 Shell Bob (Client legittimo)" -ForegroundColor Blue
        Write-Host " [4]  🟢 Shell Alice (Server target)" -ForegroundColor Cyan
        Write-Host " [5]  🩺 Verifica strumenti e connettività" -ForegroundColor Yellow
        Write-Host " [6]  📊 Stato dei container e indirizzi IP" -ForegroundColor Magenta
        Write-Host " [7]  🔨 Compila / Scarica immagini (Build/Pull)" -ForegroundColor White
        Write-Host " [8]  🛑 Arresta ambiente" -ForegroundColor Yellow
        Write-Host " [9]  ✉️  Leggi casella email di Alice (Lab 01)" -ForegroundColor Cyan
        Write-Host " [10] 🌐 Avvia Web GUI (Wireshark da browser: http://localhost:6080)" -ForegroundColor Magenta
        Write-Host " [0]  ❌ Esci" -ForegroundColor Red
        Write-Host "==================================================================" -ForegroundColor Cyan
        
        $choice = Read-Host " Seleziona un'opzione [0-10]"
        Write-Host ""

        switch ($choice) {
            "1"  { Invoke-Start }
            "2"  { Invoke-Shell "chuck" }
            "3"  { Invoke-Shell "bob" }
            "4"  { Invoke-Shell "alice" }
            "5"  { Invoke-Verify }
            "6"  { Invoke-Status }
            "7"  { Invoke-Build }
            "8"  { Invoke-Stop }
            "9"  { Invoke-ReadEmail }
            "10" { Invoke-Gui }
            "0"  { Write-Host "Arrivederci!`n" -ForegroundColor Green; exit 0 }
            Default { Write-Host "[!] Scelta non valida." -ForegroundColor Red }
        }
        Write-Host ""
        $null = Read-Host "Premi INVIO per continuare..."
    }
}

# Route command
switch ($Command) {
    "start"      { Invoke-Start }
    "stop"       { Invoke-Stop }
    "restart"    { Invoke-Restart }
    "status"     { Invoke-Status }
    "build"      { Invoke-Build }
    "pull"       { Invoke-Pull }
    "verify"     { Invoke-Verify }
    "gui"        { Invoke-Gui }
    "gui-stop"   { Invoke-GuiStop }
    "check"      { if (Test-Docker) { Write-Host "[+] Docker daemon attivo e raggiungibile.`n" -ForegroundColor Green } }
    "chuck"      { Invoke-Shell "chuck" }
    "bob"        { Invoke-Shell "bob" }
    "alice"      { Invoke-Shell "alice" }
    "read_email" { Invoke-ReadEmail }
    "menu"       { Show-Menu }
    ""           { Show-Menu }
}
