# Aurora desktop/platform profile (revision 3)

The product target is a customizable 64-bit PC/VM distribution. The earlier
[laptop profile](kernel-profile.md) is historical, not the current exclusion list.

## Kernel inputs and trade-offs

Merge order: upstream `x86_64_defconfig`, `trim.fragment`, `znlite.fragment`,
`features.fragment`, then `platform.fragment`. No conflicting assignments are
permitted between policy files. `olddefconfig` resolves dependencies; the audit
rejects any setting that did not survive and any name missing from upstream.

Revision 3 restores Intel/AMD virtualization, VirtIO, VMware/Hyper-V/Xen device
support, common discrete GPUs, NUMA/hotplug, hibernation capability, NFS/SMB/9P,
bridging, and legacy iptables compatibility alongside nftables. It includes newer
Wi-Fi opmodes/chipsets, Intel and AMD power management, and multiple vendor hotkey
modules. Matching kernel headers are exported for deliberate out-of-tree builds.

Hardware-specific drivers are usually modules: availability does not mean every
one is running. The broader kernel and firmware set cost disk space and build time.
No universal hardware compatibility or reduction in ISO size is claimed. A driver
being configured does not prove its firmware, hardware or suspend path is working.

Instrumentation/test builds and some niche legacy buses remain disabled by default;
change the public policy and rebuild if you need them. Hibernation needs correctly
configured disk-backed swap/resume; zram alone cannot preserve a hibernation image.
A kernel capability is not automatic user-space setup for containers, hypervisors,
NAS mounts, encrypted installations or Secure Boot. Add/configure those tools as
needed. CPU mitigations, seccomp, AppArmor/Landlock and memory hardening remain.

## Desktop policy

Sway is the chosen default, not a lock-in. There is no full desktop metapackage,
telemetry agent, browser/office/game bundle, forced real-time scheduling, unsafe
GPU flag or root desktop. Greetd authenticates and launches the user session; the
text greeter is intentionally small. It is wanted only by graphical.target, so
console/rescue boots do not have to fight a running compositor.

Sway configuration and presets are plain files. Changes are user-owned and are not
rewritten at login. `znlite customize init` never overwrites existing paths or
symlinks. Sway, Waybar and application defaults are fallback configuration, not a
requirement to use the supplied theme. Arbitrary hand-edited configurations can be
invalid: keep a rescue login and validate/reload before closing your working session.

## Mirror policy

The build adopts only its known Debian-generated source files after the live-build
chroot phase; unexpected sources fail the build rather than get deleted. Boot-time
selection cannot adopt existing/custom installations. Each selected mirror must
pass HTTPS, Debian-keyring signature, codename/origin, date and expiry checks for
all three archive suites. Security remains a separate fixed URI. A sampled index
measures responsiveness/throughput; APT still validates complete downloaded indexes
and packages before use. No package or remote script is executed by the selector.

A process lock prevents overlapping selections. APT's POSIX lists lock guards the
atomic source replacement. Ownership is rechecked immediately before replacement.
If a crash happens between updating sources and saving their ownership hash, the
next run freezes changes instead of guessing. An administrator can turn selection
off or intentionally make the sources user-managed. No apt lock file is deleted.

## Acceptance checklist before release

- Test BIOS and UEFI boots; the existing CI QEMU test covers BIOS/serial login only.
- Authenticate through greetd, launch Sway and applications, test lock/unlock/logout.
- Test Intel, AMD, Nouveau, VirtIO/QXL and other supported VM graphics individually.
- Check PipeWire audio, portals/screen sharing, keyboard layouts, hotkeys, Wi-Fi,
  suspend/resume, external monitors and mixed DPI.
- Validate personal-config precedence, both presets and console-only rescue boot.
- Boot offline; verify login is not delayed and APT sources are unchanged.
- Test candidate mirrors with a correct clock, invalid signatures and expired data.
- Add a custom repository/edit the managed file and confirm selection is frozen.
- Confirm kernel/header package metadata matches `6.12.111-znlite3` / `6.12.111-3`.
- Keep the previously working kernel/image until real hardware checks pass.

Performance is a measured property of workloads and devices, not a branding claim.
This revision has not eliminated upstream kernel bugs or established an automatic
security-update channel for the custom kernel. Continue reviewing stable releases.
