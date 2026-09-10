#!/usr/bin/env python3
"""Extract only the verified kernel and DTB from the BE2013 stock boot image.

This utility deliberately has a single supported input. It prevents the
recovery build from silently using the historical prebuilt payload that was in
the original 2021 device-tree fork.
"""

from __future__ import annotations

import argparse
import hashlib
import struct
import sys
from pathlib import Path


TARGET_BOOT_SHA256 = "99c55885b969d33aafe230a9ef85598df542cda390c75856d6a839733ec06ef6"
TARGET_CMDLINE = (
    "androidboot.hardware=qcom androidboot.console=ttyMSM0 "
    "androidboot.memcg=1 lpm_levels.sleep_disabled=1 "
    "video=vfb:640x400,bpp=32,memsize=3072000 msm_rtb.filter=0x237 "
    "service_locator.enable=1 swiotlb=2048 loop.max_part=7 buildvariant=user"
)


def align(value: int, page_size: int) -> int:
    return (value + page_size - 1) // page_size * page_size


def abort(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("boot_image", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()

    image = args.boot_image.read_bytes()
    digest = hashlib.sha256(image).hexdigest()
    if digest != TARGET_BOOT_SHA256:
        abort(f"unexpected boot SHA-256: {digest}")
    if len(image) != 100_663_296 or image[:8] != b"ANDROID!":
        abort("not the expected Android boot image")

    kernel_size = struct.unpack_from("<I", image, 8)[0]
    ramdisk_size = struct.unpack_from("<I", image, 16)[0]
    second_size = struct.unpack_from("<I", image, 24)[0]
    page_size = struct.unpack_from("<I", image, 36)[0]
    header_version = struct.unpack_from("<I", image, 40)[0]
    recovery_dtbo_size = struct.unpack_from("<I", image, 1632)[0]
    header_size = struct.unpack_from("<I", image, 1644)[0]
    dtb_size = struct.unpack_from("<I", image, 1648)[0]
    command_line = image[64 : 64 + 1536].split(b"\0", 1)[0].decode("ascii")

    expected = {
        "kernel_size": kernel_size == 15_745_320,
        "ramdisk_size": ramdisk_size == 872_568,
        "second_size": second_size == 0,
        "page_size": page_size == 4096,
        "header_version": header_version == 2,
        "recovery_dtbo_size": recovery_dtbo_size == 0,
        "header_size": header_size == 1660,
        "dtb_size": dtb_size == 328_855,
        "command_line": command_line == TARGET_CMDLINE,
    }
    failures = [name for name, passed in expected.items() if not passed]
    if failures:
        abort("target boot layout mismatch: " + ", ".join(failures))

    kernel_start = page_size
    ramdisk_start = kernel_start + align(kernel_size, page_size)
    second_start = ramdisk_start + align(ramdisk_size, page_size)
    recovery_dtbo_start = second_start + align(second_size, page_size)
    dtb_start = recovery_dtbo_start + align(recovery_dtbo_size, page_size)
    kernel = image[kernel_start : kernel_start + kernel_size]
    dtb = image[dtb_start : dtb_start + dtb_size]
    if len(kernel) != kernel_size or len(dtb) != dtb_size:
        abort("component extends past boot image")
    if not kernel.startswith(b"\x1f\x8b"):
        abort("target kernel payload is not gzip-compressed")
    if not dtb.startswith(b"\xd0\x0d\xfe\xed"):
        abort("target DTB does not begin with an FDT header")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "Image.gz").write_bytes(kernel)
    (args.output_dir / "dtb.img").write_bytes(dtb)
    report = args.output_dir / "target-boot-layout.txt"
    report.write_text(
        "\n".join(
            [
                "target=OnePlus Nord N100 BE2013 / OOS 11.0.5.BE83BA",
                f"boot_sha256={digest}",
                f"header_version={header_version}",
                f"page_size={page_size}",
                f"kernel_size={kernel_size}",
                f"kernel_sha256={hashlib.sha256(kernel).hexdigest()}",
                f"dtb_size={dtb_size}",
                f"dtb_sha256={hashlib.sha256(dtb).hexdigest()}",
                "dtbo_partition=separate-and-unchanged",
            ]
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
