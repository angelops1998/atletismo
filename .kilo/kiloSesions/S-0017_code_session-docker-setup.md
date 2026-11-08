# Docker Desktop and PostgreSQL test environment setup

**Date:** 2026-11-07  
**Status:** Blocked at firmware virtualization prerequisite; installation not started.

## Preflight results

| Component | Result |
|---|---|
| Windows | Registry reports Windows 10 Pro, Professional edition, display version 26H2, build 26300. The user-provided environment says Windows 11; this discrepancy was not resolved. |
| Architecture | x64 (64-bit) |
| RAM | 17,013,952,512 bytes (about 15.8 GiB) |
| Disk | C: has about 429.2 GB free |
| Hardware virtualization | **Disabled / unavailable to Windows.** `Win32_Processor` reports `VirtualizationFirmwareEnabled=False`, `VMMonitorModeExtensions=False`, and `SecondLevelAddressTranslationExtensions=False`. |
| WSL | `wsl.exe` is present, but reports that Windows Subsystem for Linux is not installed. Version/status/default WSL version could not be obtained. |
| WSL / Virtual Machine Platform features | Query requires elevation; current PowerShell process is not elevated. Feature states remain unverified. |
| Docker Desktop / Engine | No Docker CLI, Docker services, installation registry entries, or common Docker configuration directories were found. |
| Docker Compose / Linux container / PostgreSQL image and container | Not attempted. |

## Blocker and next action

Windows cannot expose hardware virtualization or SLAT to the hypervisor. Before enabling WSL 2 or installing Docker Desktop, the user must enter BIOS/UEFI setup and enable the CPU virtualization option (often named Intel Virtualization Technology, VT-x, or Vanderpool). Save and restart Windows, then rerun preflight. Do not change firmware settings automatically.

After firmware virtualization is enabled, an elevated Windows session will be needed to inspect and enable the WSL and Virtual Machine Platform features, install/update WSL, and install Docker Desktop if required. Any reboot requested by Windows must happen before continuing verification.

## Work completed

Read-only checks only. No Windows features or packages were changed, no installer or container images were downloaded, no containers or volumes were created, and no repository application files or database configuration were modified. No credentials were accessed. No migrations were run.

**Readiness:** Not ready for PostgreSQL migration validation. Resume setup after firmware virtualization is enabled and Windows has restarted.

## Recheck after user update (2026-11-07)

- `wsl --version`: WSL 3.0.3.0; kernel 6.1.8.54.1-1.
- `wsl --status`: default version 2.
- Hardware virtualization recheck still reports `VirtualizationFirmwareEnabled=False`, `VMMonitorModeExtensions=False`, and `SecondLevelAddressTranslationExtensions=False`.
- No Docker CLI or Docker service was found.
- Docker Desktop install, image pull, and PostgreSQL container checks remain unperformed because Windows still reports the firmware virtualization prerequisite unavailable. No additional configuration was changed.
