# QEMU/KVM Hosts — malp & asgard

The central, cross-project reference for our two bare-metal QEMU/KVM hypervisors
and the standard pattern for building, accessing, and recovering VMs on them.
Several projects run their compute as VMs here (eagledrive/30A scrapers + geome +
FlareSolverr, maraudersMap datanode, digger's beege FlareSolverr, prod). This
document consolidates what was scattered across per-project memories so there is
**one** source of truth.

> **HARD RULE — STOP and ask before any network/hypervisor change.** Before ANY
> VM/hypervisor/VLAN/netplan/WireGuard/routing change: inspect the existing
> pattern FIRST (`virsh domiflist` across VMs, read netplan, identify VLAN tags /
> NIC layout). If you spot a subnet/IP overlap or an off-pattern choice, **STOP
> and ask** — do not engineer a workaround unilaterally and proceed. This rule is
> written in blood: a live NIC hotplug on the scraper VM that ignored the per-VLAN
> convention and an overlapping subnet caused a VM outage (recovered only
> out-of-band via the guest agent). The VM's only management path often shares the
> same address space you're changing, so mistakes lock you out.

---

## The two hypervisors at a glance

| | **malp** | **asgard** |
|---|---|---|
| Role | KVM hypervisor (residential site) | KVM hypervisor (second site) |
| SSH | `ssh malp` (= `169.254.0.100`, mesh) | `ssh asgard` (user `oneill`, HostName `169.254.0.27`, **port 2269**, key `~/.ssh/oneill`, ProxyJump `default`) |
| Root | `sudo` available | **No sudo / no `su` pw** — but `ssh asgard-root` (root@169.254.0.27:2269, key `~/.ssh/oneill`); the `docker` group is root-equiv |
| NIC pattern | **Tagged VLANs** — `eth0.192` (→192.168.0.0/20 residential LAN), `eth0.40`, etc. Each VLAN has a `macvlan<tag>@eth0.<tag>` host-shim | **Untagged** physical NICs: `eno1`=10.9.0.10/20 (default route), `eno2`=10.6.6.0/20, `eno3`=10.13.0.0/22, eno4 down. Each has a `macvlanN@enoN` host-shim |
| VM disks | `/mnt/tb/<vm>.qcow2` | **`/mnt/ssd2/<vm>.qcow2`** (libvirt SSD2 pool) |
| Machine type | **q35** — all current malp VMs are `pc-q35-10.0` (live-verified 2026-06-30) | **q35 REQUIRED** — every working asgard VM is `pc-q35-5.2`; i440fx fails to get network |
| `virt-install` | installed | **NOT installed by default** (the build script installs it); `virt-customize` + `genisoimage` are present |
| Tooling access | `sudo virsh` | `virsh -c qemu:///system …` works WITHOUT sudo (in `libvirt`/`kvm`/`docker` groups); can't write `/mnt/ssd2` directly → create disks via libvirt storage pools |

### malp RAM is TIGHT — size new VMs modestly

malp has 20 cores but only **31 GiB RAM**, chronically ~27 GiB in use (live-verified
2026-06-30: <1 GiB free). Check `free -h` on malp before building, and keep new VMs to
**4–8 GiB** (the existing fleet: scrape0 16 GiB, the three eagledrive VMs 8 GiB each).
Disk is comfortable (`/mnt/tb` ~687 G free) — RAM is the constraint.

### asgard disk is PRECARIOUS — never write to `/`

asgard's root fs runs near-full and **a build already ran it out of space**:
- `/` (asgard--vg-root) ≈ **9.9G, ~88% used, ~1.3G free** ← DANGER. Never put VM
  images, ISOs, `virt-install` kernel/initrd extraction, or temp here.
- `/boot` = **100% full** (host concern; flag to user, don't touch).
- `/home` = 18G, ~6.6G free — OK for small text (scripts/logs), NOT images.
- **`/mnt/ssd2`** = ~1.7T, ~300G free — VM qcow2 + seed ISOs (the SSD2 pool). **fast.**
- **`/mnt/hdd`** = ~3.6T free — bulk/scratch.
- RAM = 62G total but only ~13G *available* → keep new VMs small (e.g. 4G).

**RULE:** for any asgard op (VM build, docker pull, image save, download) set
`TMPDIR`/output to **`/mnt/ssd2`** (fast) or `/mnt/hdd` (bulk), check `df -h /`
headroom first, and **clean up after** (ssd2 is the prod VM store — don't leave
temp). The first FlareSolverr build failed precisely because `virt-install
--location` extracted the installer kernel/initrd to a temp dir on `/`.

---

## macvtap host-isolation (applies to BOTH hosts)

Every VM NIC here is `<interface type='direct'>` macvtap (mode `bridge`, model
`e1000e`) on a VLAN sub-iface (malp) or physical NIC (asgard). Consequence:

- **A macvtap guest cannot talk to its own hypervisor**, and the hypervisor
  cannot ARP/ping/see the guest's DHCP lease. So `virsh domifaddr --source
  arp/lease` and host→VM ping are **useless**.
- Read a VM's IP via the **qemu-guest-agent**: `virsh domifaddr <vm> --source
  agent` (requires the guest-agent virtio-serial channel — see below).
- The host-shim ifaces (`macvlan<tag>@eth0.<tag>` on malp, `macvlanN@enoN` on
  asgard) exist to let the host reach guests on that L2 when needed.
- **Reach a VM** via: (a) a sibling VM on the same L2 as a jump host, (b) the
  serial console, or (c) the guest agent for out-of-band command exec. Don't try
  to invent host→guest LAN routing around this — it's the established pattern.

---

## Building a fresh VM (the standard recipe)

Always a **fresh autoinstall, NOT a clone**.

1. **Inspect first** (the HARD RULE): `ip -br link`, `virsh list --all` +
   `virsh domiflist <vm>` per VM, read netplan, identify which VLAN/NIC carries
   the target subnet. Match the existing pattern.

2. **Build a CIDATA seed** (Ubuntu 24.04 subiquity autoinstall). On the host
   (no cloud-localds needed):
   ```
   xorriso -as mkisofs -volid CIDATA -joliet -rock -o seed.iso user-data meta-data
   ```
   - `shutdown: poweroff` (NOT reboot) — a powered-off VM is the unambiguous
     install-success signal and stops the pinned install kernel/cmdline from
     re-triggering the installer.
   - **subiquity gotcha:** the `autoinstall.identity` user (`oneill`) is created
     by cloud-init on **first boot**, NOT during curtin install. So
     `late-commands` (which run in-target during install) MUST NOT reference that
     user — `usermod -aG docker oneill` there fails (exit 6, user doesn't exist).
     Put all user-dependent setup (docker group, NOPASSWD sudoers) under
     `autoinstall.user-data:` cloud-init passthrough (`runcmd`/`write_files`),
     which runs after the user exists. Keep `late-commands` to unit enablement
     and other user-independent steps.

3. **`virt-install`** (macvtap NIC, headless, autoinstall over serial):
   ```
   virt-install --name <vm> --memory 4096 --vcpus 4 \
     --disk path=/mnt/ssd2/<vm>.qcow2,size=20,format=qcow2 \
     --disk path=/mnt/ssd2/<vm>-seed.iso,device=cdrom \
     --location <ubuntu-iso>,kernel=casper/vmlinuz,initrd=casper/initrd \
     --network type=direct,source=<NIC>,source_mode=bridge,model=e1000e \
     --osinfo name=ubuntu24.04,require=off \
     --graphics none --noautoconsole --extra-args "autoinstall console=ttyS0,115200"
   ```
   where `<NIC>` = `eth0.192` on malp, `eno3` (etc.) on asgard.
   **On asgard, ALSO pass — learned the hard way:**
   - **`--machine q35`** (or define the domain from a working VM's XML). With the
     default i440fx the NIC won't enumerate as `enp1s0` and gets no network.
   - **`--channel unix,target_type=virtio,name=org.qemu.guest_agent.0`** — without
     this guest-agent virtio-serial channel, + macvtap isolation, there is **no
     way to read the VM's IP** after build. (virt-install omits it by default;
     working VMs like prod have it.)
   - Set `export TMPDIR=/mnt/ssd2/vi-scratch/tmp` and symlink
     `/var/lib/libvirt/boot` → ssd2 BEFORE running, so the `--location` installer
     extraction never lands on root. `trap cleanup EXIT` to `rm -rf` scratch.
   - **`--osinfo name=generic,require=off`** — asgard's `virt-install` is **3.2.0**
     with an old osinfo-db that predates ubuntu24.04. Passing `name=ubuntu24.04`
     **hard-errors** ("Unknown OS name") even with `require=off`; use `generic`.
     With explicit `--machine q35` the generic default (i440fx) is overridden, so
     you still get q35. (malp's newer virt-install accepts `ubuntu24.04`.)

4. **The `--location` halt gotcha:** `--location` boots the installer via direct
   `-kernel/-initrd` with **`-no-reboot`**. When autoinstall finishes and reboots,
   qemu HALTS — the domain *looks* "running" but CPU is idle, the qcow2 is frozen,
   and `virt-install --wait` hangs forever (your ssh session looks crashed).
   **Recovery:** `virsh destroy <vm>` then `virsh start <vm>` — the persistent
   inactive XML already drops the installer kernel + ISO, so it boots from disk.

5. **First access** (no WireGuard / no sshd yet): serial console
   `virsh console <vm>` (needs the **plaintext** local user pw — the autoinstall
   hash isn't usable since ssh is key-only). If you don't have the pw, use the
   **offline-injection winner** below.

### First-access when you have no console password — libguestfs (the deterministic winner)

cloud-init reconfig (attach a new CIDATA seed + reboot) does **NOT** work — a
subiquity-installed system disables cloud-init datasource re-detection post-install.
Instead inject directly into the powered-off qcow2:

```
sudo virsh shutdown <vm>            # disk must be unlocked (a running VM holds the qcow2 lock)
sudo virt-customize -a /mnt/<pool>/<vm>.qcow2 \
  --mkdir /etc/wireguard --copy-in /tmp/wg0.conf:/etc/wireguard \
  --run-command 'chmod 600 /etc/wireguard/wg0.conf' \
  --run-command 'systemctl enable wg-quick@wg0'
sudo virsh start <vm>
```

Use this to inject WireGuard config, an extra `authorized_key`, a netplan fix, or
a **root serial autologin** (`/etc/systemd/system/serial-getty@ttyS0.service.d/autologin.conf`)
so you can drive `/dev/pts/N` (`printf 'cmd\r\n' > pty; cat pty`) to read
`ip -br a` / `networkctl` — the only way in until the VM has network + sshd.

### asgard network gotcha — DHCP only answers reserved MACs

On asgard's `eno3` (the 10.13.0.0/22 prod LAN) the DHCP server **only replies to
known/reserved MACs**. A fresh VM's new MAC gets no lease (DISCOVER sent, no
reply), even with a byte-identical NIC to a working VM. **Resolution: assign a
STATIC address** (inject `/etc/netplan/01-static.yaml` via virt-customize:
`addresses: [10.13.0.x/22]`, `gateway via 10.13.0.1`, nameservers `10.13.0.1` +
`1.1.1.1`, `dhcp4: false`), after confirming the address is free. (Alternatively
ask the user to add a DHCP reservation for the new MAC.) Offline-install apt can
break too — the seed leaves `sources.list` pointing at `file:///cdrom`; activate
`/etc/apt/sources.list.d/ubuntu.sources` and comment the cdrom line.

---

## Deploying services — the SGC playbook (production path)

VM creation is **out-of-band**; the SGC MASH playbook only manages services on
existing hosts. To deploy a service onto a new VM:

1. Add an `inventory/hosts` line (with `ansible_ssh_common_args='-o
   ProxyJump=<jump>'` if the VM is only reachable via a jump host).
2. Add `inventory/host_vars/<host>/vars.yml`: `rev_proxy_type: none` (if no
   Traefik), `revproxy_service_networks: ""`, `sgc_playbook_identifier: <host>`,
   `service_{directory,id}_prefix: "sgc-"`, `systemd_service_manager_enabled:
   true`, `sgc_pgsk:` (generated), plus the per-service enable flags.
3. Enable the role in `requirements.yml` + `setup.yml` (+ `group_vars/mash_servers`).
4. `just roles` then `just setup-all --limit=<host>`.

**Gotchas (all hit + fixed during the FlareSolverr deploys):**
- **Docker start-limit loop** on a fresh host (`dockerd -H fd://` races
  docker.socket): `systemctl reset-failed docker.service docker.socket;
  systemctl enable --now docker.socket; systemctl start docker.service`.
- **`setup-all` configures + enables but does NOT start** the unit — finish with
  `systemctl start sgc-<service>` (or the `start-group` tag).
- **`devture_` → `sysd_` compat shim:** the pinned `flaresolverr` role v3.4.1-0
  uses old MASH `devture_systemd_docker_base_*` var names; this SGC fork renamed
  them to `sysd_*`. The role errors on undefined `devture_*` vars → add a
  host_vars block mapping every referenced `devture_systemd_docker_base_*` to its
  `sysd_docker_*` equivalent. **If a service is added to more than one host, move
  this shim to group_vars (or re-pin the role to a sysd_-native version).**
- **FlareSolverr specifically:** `flaresolverr_container_labels_traefik_enabled:
  false`, `flaresolverr_container_http_bind_port: "8191"`, and docker
  **`/dev/shm` must be `2g`** (the 64MB default crashes heavy Chrome tabs → silent
  wedge). Container runs **non-root** (UID 1000:1000).

---

## WireGuard tunnel recovery (malp VMs → t05)

malp VMs (scrapeEagleDrive, geomeEagleDrive) reach t05's Postgres/Redis over their
own `wg0`. The tunnel can **wedge** (both VMs may drop together): `ssh <vm>` and
deploy scripts time out, the VM is UP in `virsh list`, t05 *receives* the VM's
handshakes but the VM shows `0 B received` (one-way wedged routing).

It is **NOT** t05 down, the AWS security group, the wg keys, a NAT/inbound issue
(wg hole-punches outbound), rp_filter, or the egress IP — all ruled out. The fix
is a **clean down/up** (a `systemctl restart wg-quick@wg0` does NOT fully tear
down the stuck routing), run out-of-band via the malp guest agent:

```
ssh malp
sudo virsh qemu-agent-command <vm> --timeout 20 \
 '{"execute":"guest-exec","arguments":{"path":"/bin/sh","arg":["-c","wg-quick down wg0; wg-quick up wg0"],"capture-output":true}}'
# → {"return":{"pid":N}}, then:
sudo virsh qemu-agent-command <vm> --timeout 10 '{"execute":"guest-exec-status","arguments":{"pid":N}}'
# decode base64 "out-data". guest-ping = {"execute":"guest-ping"}
```

Verify with `sudo wg show wg0` (recent handshake + `received` climbing), then
`ssh <vm>`. The guest agent (qemu-guest-agent over virtio-serial) is the
out-of-band path whenever wg/LAN is down — it's why every VM needs the agent
channel.

**Mesh vs WireGuard are DISTINCT.** Nebula mesh = `169.254.0.0/24` (the `dhd`
interface); WireGuard = the separate VM↔t05 / VM↔dhd tunnels. Don't conflate them.

---

## Resizing a VM

The scraper/FlareSolverr/geome VMs are plain libvirt guests — give them more
vCPU/RAM within reason via `ssh malp` + virsh when the workload needs it
(Playwright render throughput, Cloudflare solving, scraper concurrency). **Caveat:**
this does NOT help the dex LLM bottleneck — dex (LocalAI) runs on the Jetson
`hal`, separate hardware; more scraper-VM CPU only speeds rendering/solving.

---

## Inventory of VMs built on this pattern (cross-project)

| VM | Host | NIC / addr | Purpose | Project |
|---|---|---|---|---|
| `scrape0` | malp | macvtap `eth0.192`, DHCP 192.168.x | datanode (heavy scrape/poll stack) | maraudersMap |
| `scrapeEagleDrive` | malp | macvtap `eth0.192` + **2nd NIC untagged `eth0`** for dex at `10.20.0.55:8081`; wg0 → t05 `10.77.0.3` | scrapers + scheduler + Playwright | eagledrive / **30A** |
| `geomeEagleDrive` | malp | macvtap `eth0.192`; wg0 → t05 `10.77.0.4` | geome live event map | eagledrive |
| `flareface` | malp | macvtap `eth0.192`, DHCP 192.168.14.184 (residential egress) | FlareSolverr (Cloudflare solver) | eagledrive |
| `p3x-989` (= `ssh prod`) | asgard | macvtap `eno3`, 10.13.0.21 | prod | (prod) |
| `beege-flaresolverr` | asgard | macvtap `eno3`, **static 10.13.0.120/22** (reachable inline from prod/BEEGE) | FlareSolverr | digger |
| `odoo` | asgard | macvtap `eno2`, **static 10.6.6.120/20** (q35, guest-agent; reachable directly from the controller) | Odoo back-office (do.sgc.ai) | **30A** |

> The `odoo` VM (built 2026-06-06, `tools/build-odoo-vm.sh` in the 30A repo) is
> the first VM to bake the asgard lessons in up-front: `--machine q35`, the
> guest-agent virtio channel, **static networking from the installer** (no
> DHCP-reserved-MAC dance), and `--osinfo name=generic` (asgard's virt-install
> 3.2.0 rejects `ubuntu24.04`). Reach it: `ssh odoo` (oneill@10.6.6.120, key
> `~/.ssh/oneill`) — the SGC controller routes to 10.6.0.0/20 directly, no jump.

Notes worth carrying: the scraperEagleDrive **dex 2nd-NIC** reaches LocalAI at the
raw LAN IP `http://10.20.0.55:8081` (NOT the mesh `dex.sgc.ai` hostname, which the
VM's full-tunnel can't route); the wg tunnel was renumbered `10.20.0.0/24` →
`10.77.0.0/24` to stop overlapping the dex LAN's `10.20.0.0/20`.
