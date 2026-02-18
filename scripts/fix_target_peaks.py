"""
批量修正 targets 山峰坐标。
"""
import os
import re

VIEWPOINTS_DIR = os.path.join(os.path.dirname(__file__), "..", "config", "viewpoints")

# 山峰正确 WGS-84 坐标（来源: 实施计划参考 + Wikipedia/地图验证）
PEAK_COORDS = {
    "幺妹峰": (102.902, 31.106),
    "贡嘎主峰": (101.879, 29.596),
    "贡嘎山": (101.879, 29.596),
    "格聂主峰": (99.773, 29.831),
    "格聂山": (99.773, 29.831),
    "仙乃日": (100.316, 28.433),
    "央迈勇": (100.334, 28.398),
    "夏诺多吉": (100.371, 28.413),
    "亚拉雪山": (101.560, 30.380),
}

# 每个文件中 target name 到正确山峰名的映射
# 格式: { filename: { old_target_name: correct_peak_key } }
# 大多数文件 target 名称就是山峰名


def fix_targets_in_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
        lines = content.split("\n")

    modified = False
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # 检测 target name
        if stripped.startswith("- name:"):
            target_name = stripped.replace("- name:", "").strip()
            # 查找匹配的正确坐标
            correct = None
            for peak_name, coords in PEAK_COORDS.items():
                if peak_name in target_name or target_name in peak_name:
                    correct = coords
                    break

            if correct:
                correct_lon, correct_lat = correct
                # 检查接下来的 lat 和 lon 行
                j = i + 1
                while j < len(lines) and j <= i + 5:
                    s = lines[j].strip()
                    indent = lines[j][:len(lines[j]) - len(lines[j].lstrip())]
                    if s.startswith("lat:"):
                        old_val = float(s.split(":")[1].strip())
                        if abs(old_val - correct_lat) > 0.01:
                            lines[j] = f"{indent}lat: {correct_lat}"
                            print(f"  {os.path.basename(filepath)}: {target_name} lat {old_val} → {correct_lat}")
                            modified = True
                    elif s.startswith("lon:"):
                        old_val = float(s.split(":")[1].strip())
                        if abs(old_val - correct_lon) > 0.01:
                            lines[j] = f"{indent}lon: {correct_lon}"
                            print(f"  {os.path.basename(filepath)}: {target_name} lon {old_val} → {correct_lon}")
                            modified = True
                    elif s.startswith("- name:") or s == "":
                        break
                    j += 1
        i += 1

    if modified:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    return modified


def main():
    count = 0
    for filename in sorted(os.listdir(VIEWPOINTS_DIR)):
        if not filename.endswith(".yaml"):
            continue
        filepath = os.path.join(VIEWPOINTS_DIR, filename)
        if fix_targets_in_file(filepath):
            count += 1
    print(f"\n📊 共修改 {count} 个文件的 targets 坐标")


if __name__ == "__main__":
    main()
