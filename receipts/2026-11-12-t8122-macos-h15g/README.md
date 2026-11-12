# 2026-11-12-t8122-macos-h15g: the H15 add on a real T8122 under macOS, and the J613 27.2 ANE ADT

Machine: 13-inch MacBook Air M3, Mac15,12, board J613, T8122. macOS 27.2 (26B5112a),
SIP on, no kext, no root. Everything here is userspace on macOS. Nothing ran under Linux.

## Results

1. MEASURED: `fixtures/h15-hwx/add/model.mil`, compiled by this Mac's own ANE compiler
   (`_ANEInMemoryModel`) and run on its ANE, gives the smoke golden. The 512 valid fp16
   lanes hash to `94041b7cc10a66dfd76ecfd469728ad9d66f68b508f4a9744ce41208d6a4de0b`
   (`H14_GOLDEN`), the full 32768-byte surface equals the expected surface, and no fp16
   outside the lanes is non-zero. 20 timed calls after 2 warmups, min 0.081 ms.
   Inputs, packing, rounding (nearest, ties away from zero) and the golden are the ones in
   `packaging/omarchy-ane-smoke`. So on T8122 silicon, under Apple's stack, the smoke's
   expected output is right. This says nothing about the Linux path.
2. MEASURED: ANECompiler 10.205.4 on this Mac emits the same task stream for targets
   `H15` and `H15G` for this MIL. `__TEXT.__text` (0x11c bytes at file 0x8000) and
   `__TEXT.__const` (0x4000 bytes at 0x8140) are byte-identical between the two, and
   `tools/hwx_h15_staged_to_anec.py` turns both into the same ANEC
   (`747468bfcf654ba3bcb6d5d80bdb42bf1e7236eb5b4ed80bd7963d8fbe4812b7`). Only load
   commands differ: the H15G thread-state command is 2208 bytes, H15 2192.
3. MEASURED: against the shipped fixture (Mac Studio, macOS 26.6.2, target h15), three
   task-stream words differ, each by exactly 0x00800000. `__const` is equal.

   | word (text offset) | fixture | this Mac, H15 and H15G |
   | --- | --- | --- |
   | 56 (0x0e0) | `0x23009344` | `0x22809344` |
   | 59 (0x0ec) | `0x2380934a` | `0x2300934a` |
   | 62 (0x0f8) | `0x24009442` | `0x23809442` |

   The fixture's ANEC is `5f8c00133202e0566fb5fdb4283021c648725cdda6fb064ff2a07fd45537f46b`.
   INFERENCE: the low half looks like a register address and the upper bits a field the
   compiler version moves. Which ANEC the 26A428 firmware accepts on Linux is not known;
   these three words are the first thing to look at if the fixture fails there.
4. MEASURED: an HWX file hash is not a program identity. The file embeds the compiler
   command line (`-i <mil path> -o <output path>`), so two compiles of one MIL into
   different directories give different file hashes (`784c73ec…`, `3015d8b6…` for H15G
   here). The text, const and ANEC hashes above were the same across both compiles.

## The J613 ANE and DART nodes under macOS 27.2

`ioreg -a -p IODeviceTree -r -n ane -d 2` and the same for `dart-ane`, saved as
`ane.plist` (`3e06aa64143105307ea0d3428bfd21906602c7799307431386ad1fb6e7d47b78`) and
`dart-ane.plist` (`3087198ca0e086fecf3f32d126560ec17df0d2e2e198ee1b579dc28b6e5a8087`).
This is the macOS 27.2 boot, not a Linux stub boot.

- `ane`: `iop,ascwrap-v6`, ane-type 176, iop-version 1. IODeviceMemory: wrapper
  0x311400000+0x6c000, RVBAR block 0x311050000+0x4000, engine 0x310000000+0x2000000,
  pmgr 0x2d0700000+0x18000, 0x2d0724000+0x4000. Interrupts 507 506 509 508 524.
  clock-ids 330 329 328, power-gates and clock-gates 0xd1 0x185, role `ANE`.
- `ane` `segment-ranges`, decoded as `{phys, vmaddr, iova, size}` per entry:
  `{0x100009c4000, 0x0, 0x10000000000, 0xc8000}` (`__TEXT`) and
  `{0x100015d0000, 0xc8000, 0x100000c8000, 0x2a4000}` (`__DATA`). DATA IOVA is vm-base
  plus the TEXT vmsize. The README calls that layout inferred for T6030; here it is measured
  on T8122 for the 27.2 image.
- `dart-ane`: `dart,t8110`, dart-id 23, windows 0x311800000, 0x311810000, 0x311820000,
  0x311804000 (0x4000 each), instances TRAD/DARTLLT, TRAD/DARTBRD, TRAD/DARTBWR,
  FPAD/DAPFLLT. sid `0 13 15`, sid-count 16, `bypass-13` and `bypass-15` present,
  vm-base 0x10000000000, vm-size 0x30000000000, page-size 0x4000, options 0x25.
  `dapf-instance-0` (260 bytes) and `dart-tunables-instance-0..2` (216, 600, 600 bytes)
  are in the dump. Linux does not program the DAPF windows today (README, Not verified).

The 27.2 values agree with what issue #379 measured from a Linux boot (stream 0,
vm-base, vm-size, page size, window bases). The phandles differ, as expected across boots.

## The 27.2 firmware against the 26A428 layout

The image iBoot loaded for this boot is on the Preboot volume,
`restore/Firmware/ane/h15_ane_fw_themis_j51y.im4p` (26B5112a). A staged update sits beside
it in `restore-staged` (26C5035r). Unwrapped with `im4p_payload()` from
`packaging/omarchy-ane-firmware-fetch`. The images stay local; only hashes are here.

| build | payload bytes | payload sha256 | `__TEXT` vmsize | `__DATA` vmaddr, vmsize, fileoff |
| --- | --- | --- | --- | --- |
| 26A428 (pin in `ane_h15_fw_pins.h`) | 1605632 | `19b6a499…` | 0xcc000 (`ANE_H15_FW_TEXT_SIZE`) | 0xcc000, 0x2a0000 implied, 0xd0000 |
| 26B5112a (this boot) | 1589248 | `ee74c90d5e542daf8371da841b135a58c79ebc74cd2bed6f25f9536e32ec3573` | 0xc8000 | 0xc8000, 0x2a4000, 0xcc000 |
| 26C5035r (staged) | 1785856 | `757e6fddbf528824ad7b6ebe3039834a3941659078d0df197b4a7c23d658f53a` | 0xf8000 | 0xf8000, 0x274000, 0xfc000 |

The live `segment-ranges` match the 26B5112a Mach-O exactly. Every build ends at VM
0x36c000 (`ANE_H15_FW_IMAGE_SIZE`), but the TEXT/DATA split moves per build. The constants in
`ane/h15/ane_h15_fw_layout.h` are right for 26A428 only. The sha pin in front of
`ane_h15_fw_copy()` already refuses any other payload, so this is not a bug today. Loading
another build would need the split read from the Mach-O instead.

## Reproduce

```
clang -O2 -fobjc-arc -framework Foundation -framework IOSurface \
    tools/native-macos/ane_inmem_run.m -o SCRATCH/ane_inmem_run
python3 -I tools/native-macos/h15_add_smoke.py SCRATCH

clang -O2 -fobjc-arc -framework Foundation tools/native-macos/anec_compile.m -o SCRATCH/anec_compile
cp fixtures/h15-hwx/add/model.mil SCRATCH/H15G/
SCRATCH/anec_compile SCRATCH/H15G/model.mil SCRATCH/H15G add H15G
python3 -I tools/hwx_h15_staged_to_anec.py SCRATCH/H15G/add SCRATCH/H15G/add.anec
```

`h15_add_smoke.py` exits 0 only on a lane match, a full-surface match and no stray values.

## Not shown

- Nothing ran under Linux. The Linux T8122 start (stage 5 with the power gate, a mapped image)
  is still open (issues #366, #379).
- That the compiler aned used for result 1 targeted H15G is INFERENCE: it is the host
  compiler, and result 2 shows H15 and H15G agree for this MIL anyway.
- One MIL. Other ops may split H15 from H15G.
