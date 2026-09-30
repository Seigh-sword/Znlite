> **Historical profile:** this document describes the earlier laptop-only
> revision 2. Revision 3 adds `kernel/platform.fragment` and restores broad
> PC/VM support; see [the desktop profile](desktop-profile.md). The exclusions
> and configuration counts below do not describe the current default image.

# Znlite laptop kernel profile, revision 2

This is a configuration of upstream Linux **6.12.111**, not an unreviewed source
fork, universal speed patch, or claim of zero bugs. The exact upstream commit and
archive checksum remain pinned in `kernel/source.lock`. Profile revision 2 uses
`6.12.111-znlite2` and Debian package version `6.12.111-2`: a distinct kernel
package/release avoids silently replacing the previous kernel and its modules.

## Changes and trade-offs

| Area | Policy | Reason / limit |
| --- | --- | --- |
| Interactive work | Full preemption with dynamic switching, tickless idle, 250 Hz | A responsiveness-oriented compromise, not hard real-time or a benchmark result. `preempt=voluntary` can select the previous preemption model at boot. |
| Memory pressure | Memory cgroup limits and modular zram, LZ4; logical swap = half RAM, capped at 2048 MiB | Compression consumes CPU and RAM; this is not extra physical memory and is not guaranteed to improve every workload. No disk writeback or arbitrary global swappiness change. |
| Audio | HDA controller/codecs built as modules | Load the codecs actually needed, rather than every supported codec at boot. Keep HDMI/analog/USB support. |
| Networking | nftables/connection tracking/NAT/logging/rate-limit/route-lookup modules, WireGuard and TUN | Corrects the previous blanket `NETFILTER=n`, which prevented native firewalling and could break connection sharing. **No deny policy or VPN is auto-enabled.** Native nftables, not legacy iptables extensions. |
| Laptop input | Acer WMI, Bay Trail/Braswell pinctrl, DesignWare I²C, ACPI HID | Helps hotkeys and I²C-connected input hardware; support still depends on the actual model/firmware. |
| Storage | exFAT and dm-crypt modules with tools/initramfs integration | Supports removable media and encrypted devices. Does not encrypt, format, repartition or mount any existing disk automatically. Encryption/install workflows require separate testing. |
| Hardening | CPU mitigations, KASLR, strong stack protector, read-only executable memory, usercopy/fortify checks, hardened/randomized slab freelists, allocation zeroing | Some defenses cost performance; they are deliberately retained. No `mitigations=off`, forced module loading, overclocking or unsafe power settings. |
| Sandboxing | seccomp, AppArmor, Yama, Landlock | Replaces unused SELinux configuration. AppArmor policy coverage depends on installed profiles; kernel support alone does not confine every process. |
| Diagnostics | ORC unwinder, printk/kallsyms, SysRq, serial console, build audit | Removing debug symbols/tracers does not mean hiding failures. `znlite doctor` reports current state without changing anything. |

### Removed from the generic baseline

Hypervisor hosting/guest acceleration, hibernation/crash kernels, tracing/debug
instrumentation, profiling, forced module unload, NUMA/memory hotplug, explicit
huge-page filesystems, PCMCIA/CardBus, FireWire, InfiniBand, Macintosh/EeePC extras,
network-root/NFS/9P filesystems, multicast routing, selected legacy NIC families,
and MIDI sequencing are excluded from this laptop profile. These are legitimate
features for other use cases, not inherently "bad code". Re-enable them in the
policy and rebuild if needed. QEMU still works with emulated conventional devices;
this profile is not a general-purpose virtualization/container-host kernel.

Normal suspend, CPU idle/frequency management, ACPI thermal/battery support, Intel
graphics, mixed-mode EFI compatibility, 32-bit application compatibility, normal
huge-page optimization where selected, broad Wi-Fi/Ethernet modules, USB, storage,
and raster/serial rescue paths remain. Exact laptop model and PCI/USB IDs are
needed before safely trimming hardware drivers further. This is **not** a promise
of universal GPU/Wi-Fi support or Secure Boot enrollment/signing.

## Configuration is checked, not assumed

The canonical inputs are:

1. Upstream `x86_64_defconfig` from the pinned source.
2. `kernel/trim.fragment`: explicit exclusions.
3. `kernel/znlite.fragment`: hardware, boot and recovery requirements.
4. `kernel/features.fragment`: latency, memory, networking and hardening policy.

`./scripts/configure-kernel.sh SOURCE_DIRECTORY REPORT_DIRECTORY` merges these,
runs the kernel's own `olddefconfig`, then verifies **every requested value**
against the resolved `.config`. Unknown upstream symbols and dependency-induced
changes are errors, not warnings to ignore. Duplicate/conflicting fragment entries
are rejected. An invisible disabled symbol may legitimately be omitted by
Kconfig; the upstream name check still detects misspellings.

The previous profile contained four obsolete symbols (three HDA codec names and
`SQUASHFS_LZMA`) plus a FAT setting that was promoted by a dependency. These are
corrected rather than accepted as if they had worked. Hardware fragment files
under `board/` are historical, not active build inputs.

The ISO artifact includes `kernel.config` and `kernel-audit.json`, and both are
covered by `SHA256SUMS`. Failure artifacts retain the resolved configuration and
audit report too. Inspecting the fragment alone is **not** proof of a feature in
a shipped image.

A local native Kconfig comparison using the pinned source and GCC 12 resolved the
previous profile to 1545 built-in / 89 module selections and revision 2 to 1507
built-in / 171 module selections. These are counts of `=y`/`=m` Kconfig symbols,
**not driver counts, bytes saved, boot-time measurements or a performance score**.
The additional modules include new features and dependencies, so total disk usage
may increase even while fewer drivers are resident by default. Compiler/version
choices can affect these counts.

## Runtime checks and rollback

```sh
znlite doctor
zramctl
swapon --show
sudo aa-status
sudo nft list ruleset          # inspect; no firewall policy is installed for you
journalctl -b -p warning
```

Zram settings live in `/etc/systemd/zram-generator.conf`. To test without it, add
`systemd.zram=0` to the boot command line for one boot. Avoid `swapoff` on a busy,
low-memory machine just to compare benchmarks; reboot into the alternate setting
instead. Compare the same workload, RAM, power source and thermal conditions.

Before replacing an installed kernel, keep the known-good kernel/package and
recovery media, back up data, and verify its boot-menu entry. The `-znlite2` name
permits side-by-side installation with the previous `-znlite` kernel. Select the
older kernel to recover. The ISO's raster-rescue option addresses renderer issues;
it does not replace a previous kernel as a recovery mechanism.

Required acceptance checks on the target laptop include boot in its actual BIOS
or UEFI mode, keyboard/touchpad/hotkeys, Wi-Fi reconnects, suspend/resume, audio,
battery/thermal behavior, vector/raster login, and memory pressure with/without
zram. The existing QEMU BIOS login smoke test does **not** cover all of these.
Measure before claiming better battery life, smaller RAM usage or faster workloads.

## Security maintenance

This work changes configuration, not upstream C code or the upstream stable
version. It does **not** fix all kernel bugs or establish an ongoing patch SLA.
Review new upstream stable/security releases, update the source pin/checksum,
rebuild, and repeat acceptance tests regularly. `znlite update` still updates
APT-managed packages only; it does not deliver custom Znlite kernel updates.
