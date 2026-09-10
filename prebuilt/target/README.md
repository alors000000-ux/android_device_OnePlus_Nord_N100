# Target boot payload (generated in private CI only)

`Image.gz` and `dtb.img` in this directory are intentionally absent from the
public device tree. They must be extracted during GitHub Actions from the
verified stock boot image for OnePlus Nord N100 BE2013, OxygenOS
`11.0.5.BE83BA`, build `BE2013_7_220331` / incremental `2203311222`.

The original files directly under `prebuilt/` are historical firmware inputs
from the source fork. `BoardConfig.mk` does not reference them. Do not insert a
generic Bengal kernel, an Android-10 payload, a foreign N100 payload, or a
DTBO image here. The target uses boot-header v2 with a separate, unchanged
DTBO partition.
