# Shared checkout dependencies

The Git tree contains the required third_party source snapshots directly (zero gitlinks).
`.gitmodules` retains original repository URLs; `git submodule update --init` is currently a no-op.
Do not replace these snapshots with upstream main. A future submodule conversion must pin commits separately.

| Dependency | Source/version and installation |
|---|---|
| Isaac Sim | `nvcr.io/nvidia/isaac-sim:5.1.0`, fetched by documented Docker build |
| Isaac Lab / Arena / ai_sapiens / zenoh_ros2_sdk | Tracked `third_party/` source snapshots in this branch |
| PyTorch (x86 Docker) | 2.7.0, torchvision 0.22.0; `docker/constraints.isaacsim.txt` |
| Other Python/build dependencies | `docker/Dockerfile.base`, package setup files and constraint files; installed during Docker build. Some inherited optional packages use ranges/unpinned versions, so the image is not fully lockfile-reproducible. |
| RoboDojo objects | Hugging Face `RoboDojo-Benchmark/RoboDojo`, revision `63fcc045f2e974902eb7800d29de48004cf86016`; `python3 scripts/tools/download_make_toast_assets.py` verifies every size and SHA256 in asset_manifest.json |
| Four-groove rack | Both `rack.usda` and `bread_slot.usdz` tracked with LFS. USDZ contains `bread_slot.usdc`, no separate textures. |
| Packing table | Isaac Sim configured asset cloud root + `/Isaac/Props/PackingTable/packing_table.usd`; runtime downloads the USD and referenced materials/textures via Isaac Sim asset resolver. Requires cloud access or user-configured asset root/cache; not bundled in this branch. |
| Quest HTTPS server | Python 3 standard library plus host `openssl` executable; no Python web framework required |
| CPU geometry/tests | Python with numpy, scipy, torch, pxr/USD; simulator Python or separately provisioned environment |
| Browser test | Google Chrome and Python websockets; JS tests require Node.js. These are development checks, not Quest runtime requirements. |

Local index-only export resolved the two new rack LFS objects from the local Git object store.
66 inherited LFS pointers were unavailable locally, including other robot/motion/documentation/food assets;
none was downloaded because GitHub DNS was unavailable. This does not establish remote LFS completeness.
The toast BG2 robot USDs are legacy normal Git blobs, not among those missing pointers.
The documented RoboDojo downloader is still required in a fresh checkout; local downloaded asset caches
were intentionally not copied into the export. Full GPU/renderer dependency resolution remains unverified.
