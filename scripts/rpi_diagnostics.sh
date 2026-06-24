#!/usr/bin/env bash
set -Eeuo pipefail

# Read-only hardware-in-the-loop diagnostics for the spare/test RM2.
# This script must not write to, delete from, or restart anything on the RM2.

RM2_SSH_TARGET="${RM2_SSH_TARGET:-rm2}"
DEV_BACKUP_ROOT="${DEV_BACKUP_ROOT:-/home/k11-user/rm2-backup-dev}"
SSH_OPTS=(-o BatchMode=yes -o ConnectTimeout=10)

section() {
  printf '\n## %s\n' "$1"
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "ERROR: required command not found: $1" >&2
    exit 1
  fi
}

section "Runner identity"
uname -a
id
pwd

section "Required local commands"
for cmd in bash ssh rsync python3 df find wc sed awk; do
  require_cmd "$cmd"
  printf '%s: %s\n' "$cmd" "$(command -v "$cmd")"
done

section "Python"
python3 --version

section "Disk space"
df -h "$HOME" || true
df -h "$(dirname "$DEV_BACKUP_ROOT")" || true

section "Development backup root"
echo "DEV_BACKUP_ROOT=$DEV_BACKUP_ROOT"
mkdir -p "$DEV_BACKUP_ROOT"
ls -ld "$DEV_BACKUP_ROOT"

section "SSH alias check"
echo "RM2_SSH_TARGET=$RM2_SSH_TARGET"
# BatchMode prevents the workflow from hanging waiting for passwords.
ssh "${SSH_OPTS[@]}" "$RM2_SSH_TARGET" "hostname; whoami" >/tmp/rm2_diag_ssh_identity.txt
sed 's/.*/RM2: &/' /tmp/rm2_diag_ssh_identity.txt

section "RM2 read-only source checks"
ssh "${SSH_OPTS[@]}" "$RM2_SSH_TARGET" \
  "test -d /home/root/.local/share/remarkable/xochitl && echo xochitl=present || echo xochitl=missing; test -d /usr/share/remarkable/templates && echo templates=present || echo templates=missing"

section "RM2 source counts"
# Counts only, no notebook names in logs.
ssh "${SSH_OPTS[@]}" "$RM2_SSH_TARGET" \
  "find /home/root/.local/share/remarkable/xochitl -maxdepth 1 -type f -name '*.metadata' 2>/dev/null | wc -l | sed 's/^/metadata_files=/'; find /home/root/.local/share/remarkable/xochitl -maxdepth 1 -type d 2>/dev/null | wc -l | sed 's/^/top_level_dirs=/'; find /usr/share/remarkable/templates -maxdepth 1 -type f 2>/dev/null | wc -l | sed 's/^/template_files=/'; true"

section "RM2 listening ports summary"
# Useful for confirming that SSH is present and that no assumption is being made about web export.
ssh "${SSH_OPTS[@]}" "$RM2_SSH_TARGET" \
  "(ss -ltnp 2>/dev/null || netstat -tlnp 2>/dev/null || true) | sed -E 's/[0-9]+\/[^ ]+/PID\/PROCESS/g'"

section "Diagnostics result"
echo "RPI diagnostics completed successfully. No RM2 files were modified."
