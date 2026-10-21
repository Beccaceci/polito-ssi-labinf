#!/usr/bin/env bash
set -euo pipefail
openssl dgst -sha256 -binary -- "$1" | od -An -tx1 | tr -d ' \n' | cut -c1
