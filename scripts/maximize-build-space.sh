#!/usr/bin/env bash
# 扩大 GitHub Actions 编译机的可用磁盘空间（思路来自 easimon/maximize-build-space，MIT 许可）。
# 删除预装的大型软件后，把根分区和 /mnt 的剩余空间合并成一个 LVM 卷，挂载到工作目录。
# 注意：挂载会盖住工作目录里已有的文件，之后需要重新检出仓库。
set -euo pipefail

ROOT_RESERVE_MB="${ROOT_RESERVE_MB:-8192}"
TEMP_RESERVE_MB="${TEMP_RESERVE_MB:-2048}"
MOUNT_PATH="${BUILD_MOUNT_PATH:-$GITHUB_WORKSPACE}"
VG_NAME=buildvg

echo "清理前:"
df -h / /mnt

echo "删除预装软件..."
sudo rm -rf /usr/share/dotnet /usr/local/lib/android /opt/ghc /usr/local/.ghcup /opt/hostedtoolcache/CodeQL

# 旧 swap 文件可能在 /mnt 上，先释放；swap 由后续步骤重新创建
sudo swapoff -a || true
sudo rm -f /mnt/swapfile

make_pv() { # 用法: make_pv <挂载点> <保留MB> <镜像路径>
  local free_kb size
  free_kb=$(df --block-size=1024 --output=avail "$1" | tail -1)
  size=$(( (free_kb - $2 * 1024) * 1024 ))
  if (( size <= 0 )); then
    echo "$1 剩余空间不足，跳过" >&2
    return 0
  fi
  sudo touch "$3"   # fallocate -z 不会创建文件
  sudo fallocate -z -l "$size" "$3"
  sudo losetup --find --show "$3"
}

PVS=()
# /mnt 是独立的临时盘时才使用（有些编译机上 /mnt 和根目录是同一个分区）
if [[ "$(df --output=source /mnt | tail -1)" != "$(df --output=source / | tail -1)" ]]; then
  dev=$(make_pv /mnt "$TEMP_RESERVE_MB" /mnt/tmp-pv.img); [[ -n "$dev" ]] && PVS+=("$dev")
fi
dev=$(make_pv / "$ROOT_RESERVE_MB" /pv.img);           [[ -n "$dev" ]] && PVS+=("$dev")
(( ${#PVS[@]} > 0 )) || { echo "没有可用空间"; exit 1; }

sudo pvcreate -qf "${PVS[@]}"
sudo vgcreate -q "$VG_NAME" "${PVS[@]}"
sudo lvcreate -q -l 100%FREE -n buildlv "$VG_NAME"
sudo mkfs.ext4 -q -E nodiscard -m0 "/dev/mapper/${VG_NAME}-buildlv"
sudo mkdir -p "$MOUNT_PATH"
sudo mount "/dev/mapper/${VG_NAME}-buildlv" "$MOUNT_PATH"
sudo chown "$(id -u):$(id -g)" "$MOUNT_PATH"

echo "清理后:"
df -h / /mnt "$MOUNT_PATH"
