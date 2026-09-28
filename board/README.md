# Historical configuration

The files under `board/znlite/` are retained from the earlier board-oriented
prototype. They are **not read by the active Debian live-image build**.

Edit `kernel/znlite.fragment`, `kernel/trim.fragment`, and
`kernel/features.fragment` instead. See `docs/kernel-profile.md` for the merge
order, resolved-configuration audit, compatibility exclusions, and testing.
