# Raspberry Pi SSH access to RM2 devices

This guide explains how to set up passwordless SSH from the Raspberry Pi to a validation or production RM2 for unattended raw-copy operations.

Run these commands on the Raspberry Pi only. Do not SSH, SCP, or rsync to an RM2 from a developer Mac.

## Preferred config mode

Prefer an SSH alias in the Raspberry Pi user's SSH config and set:

```toml
[rm2]
host = "rm2"
ssh_alias = true
```

With `ssh_alias = true`, `rm2-backup sync-plan` emits remote paths like:

```text
rm2:/home/root/.local/share/remarkable/xochitl/
```

That means SSH decides the real hostname, user, port, and key from the Raspberry Pi's private `~/.ssh/config`.

Do not use `user = ""`. Empty user values are unsupported.

## Generate a dedicated key on the Raspberry Pi

Use a dedicated key for the validation RM2:

```bash
mkdir -p "$HOME/.ssh"
chmod 700 "$HOME/.ssh"
ssh-keygen -t ed25519 -f "$HOME/.ssh/rm2_validation_ed25519" -C "rm2-backup-validation"
```

Do not commit this key or its path to the repository.

## Install the public key on the RM2

Install the public key into the RM2 root account using your existing approved RM2 access path from the Raspberry Pi.

The target file on the RM2 is:

```text
/home/root/.ssh/authorized_keys
```

The RM2 permissions should be:

```bash
chmod 700 /home/root/.ssh
chmod 600 /home/root/.ssh/authorized_keys
```

This step modifies the validation RM2's SSH authorization state. Do it only for the validation device unless production deployment has been explicitly approved.

## Configure the Raspberry Pi SSH alias

Edit the Raspberry Pi user's private SSH config:

```bash
nano "$HOME/.ssh/config"
chmod 600 "$HOME/.ssh/config"
```

Add a block for the validation RM2:

```sshconfig
Host rm2
    HostName VALIDATION_RM2_HOST_OR_LOCAL_IP
    User root
    Port 22
    IdentityFile ~/.ssh/rm2_validation_ed25519
    IdentitiesOnly yes
```

For multiple RM2 devices, use separate aliases:

```sshconfig
Host rm2-validation
    HostName VALIDATION_RM2_HOST_OR_LOCAL_IP
    User root
    Port 22
    IdentityFile ~/.ssh/rm2_validation_ed25519
    IdentitiesOnly yes

Host rm2-production
    HostName PRODUCTION_RM2_HOST_OR_LOCAL_IP
    User root
    Port 22
    IdentityFile ~/.ssh/rm2_production_ed25519
    IdentitiesOnly yes
```

Keep real hostnames, IP addresses, and key paths out of committed files.

## Test passwordless SSH

On the Raspberry Pi:

```bash
ssh rm2 'hostname && cat /etc/version'
```

It should complete without a password prompt.

If your private config uses an IP address directly and you are not using `ssh_alias = true`, also test the explicit form:

```bash
ssh root@VALIDATION_RM2_HOST_OR_LOCAL_IP 'hostname && cat /etc/version'
```

The explicit form must use the same key, either through a matching `Host` block or an explicit `ssh_key` in private config.

## Why alias mode matters

This can work:

```bash
ssh rm2
```

while this still asks for a password:

```bash
ssh root@VALIDATION_RM2_HOST_OR_LOCAL_IP
```

The first command uses the `Host rm2` block from `~/.ssh/config`. The second command does not use that alias block unless a matching host block exists for the IP/hostname. If `rsync` uses `root@host`, it can bypass the alias and prompt for a password.

Use `ssh_alias = true` to make `rm2-backup` use the alias directly.

## Private config examples

Alias mode:

```toml
[rm2]
host = "rm2"
ssh_alias = true
```

Explicit host/key mode:

```toml
[rm2]
host = "VALIDATION_RM2_HOST_OR_LOCAL_IP"
user = "root"
port = 22
ssh_key = "/PRIVATE/RPI/ONLY/PATH/TO/RM2_KEY"
```

Use one mode or the other. `ssh_alias = true` cannot be combined with `ssh_key`.

## Remove stale host fingerprints

RM2 software updates can change the SSH host fingerprint. Remove stale entries on the Raspberry Pi only:

```bash
ssh-keygen -f "$HOME/.ssh/known_hosts" -R rm2
ssh-keygen -f "$HOME/.ssh/known_hosts" -R VALIDATION_RM2_HOST_OR_LOCAL_IP
```

Then reconnect and verify the new host key through your normal trusted process.

## Check the generated rsync plan

For alias mode:

```bash
rm2-backup sync-plan --config /etc/rm2-backup-validation/config.toml
```

The remote source should look like:

```text
rm2:/home/root/.local/share/remarkable/xochitl/
```

It should not look like:

```text
root@VALIDATION_RM2_HOST_OR_LOCAL_IP:/home/root/.local/share/remarkable/xochitl/
```

unless you intentionally configured explicit host/key mode.
