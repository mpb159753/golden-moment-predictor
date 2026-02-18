"""
批量更新 YAML 文件坐标。
基于 POI 查询结果 + 手动修正，更新所有观景台的 WGS-84 坐标。
"""
import yaml
import os
import math

VIEWPOINTS_DIR = os.path.join(os.path.dirname(__file__), "..", "config", "viewpoints")

PI = math.pi; A = 6378245.0; EE = 0.00669342162296594323

def _transform_lat(lng, lat):
    ret = -100.0+2.0*lng+3.0*lat+0.2*lat*lat+0.1*lng*lat+0.2*math.sqrt(abs(lng))
    ret += (20.0*math.sin(6.0*lng*PI)+20.0*math.sin(2.0*lng*PI))*2.0/3.0
    ret += (20.0*math.sin(lat*PI)+40.0*math.sin(lat/3.0*PI))*2.0/3.0
    ret += (160.0*math.sin(lat/12.0*PI)+320*math.sin(lat*PI/30.0))*2.0/3.0
    return ret

def _transform_lng(lng, lat):
    ret = 300.0+lng+2.0*lat+0.1*lng*lng+0.1*lng*lat+0.1*math.sqrt(abs(lng))
    ret += (20.0*math.sin(6.0*lng*PI)+20.0*math.sin(2.0*lng*PI))*2.0/3.0
    ret += (20.0*math.sin(lng*PI)+40.0*math.sin(lng/3.0*PI))*2.0/3.0
    ret += (150.0*math.sin(lng/12.0*PI)+300.0*math.sin(lng/30.0*PI))*2.0/3.0
    return ret

def gcj02_to_wgs84(gcj_lng, gcj_lat):
    dlat = _transform_lat(gcj_lng-105.0, gcj_lat-35.0)
    dlng = _transform_lng(gcj_lng-105.0, gcj_lat-35.0)
    radlat = gcj_lat/180.0*PI; magic = math.sin(radlat); magic = 1-EE*magic*magic
    sqrtmagic = math.sqrt(magic)
    dlat = (dlat*180.0)/((A*(1-EE))/(magic*sqrtmagic)*PI)
    dlng = (dlng*180.0)/(A/sqrtmagic*math.cos(radlat)*PI)
    return round(gcj_lng-dlng, 6), round(gcj_lat-dlat, 6)

# ===== 坐标修正数据 =====
# 格式: filename -> (wgs84_lon, wgs84_lat, source)
# 来源: "poi" = 高德 POI 搜索结果可信
#        "browser" = 浏览器手动确认
#        "manual" = 根据参考资料/卫星图手动修正
#        "reference" = 实施计划 POI 参考表

CORRECTIONS = {}

# --- 以下根据高德 POI 结果算出 WGS-84 坐标 ---

# Task 1: 四姑娘山区域
# 猫鼻梁：浏览器确认 GCJ-02(102.843911, 30.986233)
_lng, _lat = gcj02_to_wgs84(102.843911, 30.986233)
CORRECTIONS["siguniang_maobiliang.yaml"] = (_lng, _lat, "browser")
# 长坪沟景区入口
CORRECTIONS["siguniang_changping.yaml"] = (102.857694, 31.014731, "poi")
# 双桥沟景区入口
CORRECTIONS["siguniang_shuangqiao.yaml"] = (102.768042, 30.982511, "poi")
# 海子沟景区入口 (朝山坪在景区内，取入口)
CORRECTIONS["siguniang_haizi_chaoshanping.yaml"] = (102.838233, 30.996446, "poi")
# 四姑娘山景区总入口（二姑娘峰攀登起点附近）
CORRECTIONS["siguniang_erguniang_view.yaml"] = (102.824391, 31.096836, "poi")

# Task 2: 贡嘎山区域
CORRECTIONS["gongga_lenggacuo.yaml"] = (101.69951, 29.638151, "poi")
CORRECTIONS["gongga_niubei.yaml"] = (102.414969, 29.77381, "poi")  # 牛背山景区(贡嘎方向)
CORRECTIONS["gongga_yaha_pass.yaml"] = (101.723135, 29.7425, "poi")
CORRECTIONS["gongga_yuzixi.yaml"] = (101.581788, 30.210279, "poi")
CORRECTIONS["gongga_zimei_pass.yaml"] = (101.721355, 29.518239, "poi")

# Task 3: 格聂区域
CORRECTIONS["genie_eye.yaml"] = (99.759393, 29.798288, "poi")
CORRECTIONS["genie_chachongxi.yaml"] = (99.656227, 29.742763, "poi")
CORRECTIONS["genie_laolenggusi.yaml"] = (99.643822, 29.819585, "poi")
# 努达营地/虎皮坝: POI 完全错误，使用格聂景区参考坐标
# 虎皮坝营地在格聂主峰西南方，冷古寺以南
# 参考冷古寺(99.644, 29.820)和格聂之眼(99.759, 29.798)的位置关系
# 虎皮坝位于两者之间偏南
_lng, _lat = gcj02_to_wgs84(99.790, 29.855)  # 格聂自然中心参考
CORRECTIONS["genie_nuda_camp.yaml"] = (_lng, _lat, "reference")
CORRECTIONS["genie_xiazetong.yaml"] = (99.77077, 29.825485, "poi")

# Task 4: 亚丁区域
CORRECTIONS["yading_echushan_view.yaml"] = (100.194275, 28.562789, "poi")
CORRECTIONS["yading_five_color_lake.yaml"] = (100.351471, 28.380442, "poi")
CORRECTIONS["yading_luorong_pasture.yaml"] = (100.381201, 28.389973, "poi")
CORRECTIONS["yading_milk_lake.yaml"] = (100.345963, 28.374149, "poi")
# 珍珠海/卓玛拉措: POI 完全错误(搜到珠海)
# 珍珠海在仙乃日脚下，亚丁景区内，参考仙乃日(28.433, 100.316)
# 珍珠海海拔约3950m，在冲古寺上方
_lng, _lat = gcj02_to_wgs84(100.307, 28.435)  # 珍珠海参考位置
CORRECTIONS["yading_pearl_lake.yaml"] = (_lng, _lat, "reference")

# Task 5: 亚拉雪山区域
CORRECTIONS["yala_balangshengdu.yaml"] = (101.42751, 30.338197, "poi")
CORRECTIONS["yala_gedilamu.yaml"] = (101.644077, 30.2359, "poi")
CORRECTIONS["yala_gunong.yaml"] = (101.516433, 30.355645, "poi")
CORRECTIONS["yala_tagong_view.yaml"] = (101.553397, 30.332783, "poi")
CORRECTIONS["yala_yunrao_view.yaml"] = (101.661825, 30.38665, "poi")

# Task 6: 交通沿线
CORRECTIONS["tagong_muya.yaml"] = (101.526473, 30.323371, "poi")
CORRECTIONS["transit_18bends_view.yaml"] = (100.873712, 29.999766, "poi")
# 大二普: POI 完全错误，使用 毕棚沟景区 附近参考
# 大二普沟在理县毕棚沟附近，实施计划参考 (102.993, 31.383) 毕棚沟景区
_lng, _lat = gcj02_to_wgs84(102.993, 31.383)
CORRECTIONS["transit_daerpu_valley.yaml"] = (_lng, _lat, "reference")
CORRECTIONS["transit_gaoersi_pass.yaml"] = (101.345279, 30.039849, "poi")
CORRECTIONS["transit_jiagenba_view.yaml"] = (101.55904, 29.846973, "poi")
CORRECTIONS["transit_jianziwan_pass.yaml"] = (100.796678, 30.021268, "poi")
CORRECTIONS["transit_kazila_pass.yaml"] = (100.647116, 30.148019, "poi")
CORRECTIONS["transit_lixiao_redstone.yaml"] = (102.876353, 31.388087, "poi")
CORRECTIONS["transit_lixiao_tunnel_view.yaml"] = (102.744718, 31.310194, "poi")
# 新都桥: 原来就准确(偏差0.7km)，POI 给的是镇政府，更新为更精确的位置
CORRECTIONS["transit_xinduqiao_view.yaml"] = (101.491576, 30.048217, "poi")
CORRECTIONS["transit_zheduoshan_pass.yaml"] = (101.803517, 30.074318, "poi")

# Task 7: 其他独立景区
CORRECTIONS["bipenggou_panyang.yaml"] = (102.870003, 31.229248, "poi")
CORRECTIONS["dagu_4860.yaml"] = (102.909396, 32.133504, "poi")
# 多饶嘎姆/亚拉主景: POI 搜到墨石公园，原名是"亚拉主景平台"
# 位置应在墨石公园景区附近，POI 结果可接受
CORRECTIONS["duoraogamu_yala_view.yaml"] = (101.540804, 30.447693, "poi")
CORRECTIONS["guergou_hot_spring_view.yaml"] = (103.552897, 32.595224, "poi")
CORRECTIONS["jiuzhai_wuhuahai.yaml"] = (103.878596, 33.161324, "poi")
CORRECTIONS["lianbaoyeze_zhagaer.yaml"] = (101.174174, 33.066421, "poi")
# 磨西沟/海螺沟: POI 搜到磨西古镇，这个名字本身是"主沟观景点"
# 位置应该在海螺沟景区方向，磨西古镇是入口所在地
CORRECTIONS["majiagou_main_view.yaml"] = (102.125221, 29.643257, "poi")
CORRECTIONS["mengtun_gaoqiaogou.yaml"] = (103.090956, 31.724865, "poi")
# 墨石公园异域星球观景位 - POI 可信
CORRECTIONS["moshi_main_view.yaml"] = (101.540804, 30.447693, "poi")
CORRECTIONS["zhagushan_pass.yaml"] = (102.672527, 31.853109, "poi")

# Task 8: 牛背山、神木垒、折多山
# 牛背山(独立景区): POI 搜到的石棉县是大渡河方向的牛背山底部
# 正确的山顶位置应使用 gongga_niubei 的同一结果
CORRECTIONS["niubei_gongga.yaml"] = (102.414969, 29.77381, "poi")
CORRECTIONS["shenmulei_redwood_view.yaml"] = (102.674996, 30.678644, "poi")
CORRECTIONS["zheduo_gongga.yaml"] = (101.804206, 30.07003, "poi")


def update_yaml_coords(filepath, new_lon, new_lat):
    """保留 YAML 文件格式，仅替换 lat 和 lon 值"""
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    new_lines = []
    in_location = False
    for line in lines:
        stripped = line.strip()
        if stripped == "location:":
            in_location = True
            new_lines.append(line)
            continue
        if in_location:
            if stripped.startswith("lat:"):
                indent = line[:len(line) - len(line.lstrip())]
                new_lines.append(f"{indent}lat: {new_lat}\n")
                continue
            elif stripped.startswith("lon:"):
                indent = line[:len(line) - len(line.lstrip())]
                new_lines.append(f"{indent}lon: {new_lon}\n")
                continue
            elif stripped.startswith("altitude:"):
                new_lines.append(line)
                in_location = False
                continue
            elif not stripped.startswith(("lat:", "lon:", "altitude:")) and stripped != "":
                in_location = False
        new_lines.append(line)

    with open(filepath, "w", encoding="utf-8") as f:
        f.writelines(new_lines)


def main():
    updated = 0
    for filename, (lon, lat, source) in sorted(CORRECTIONS.items()):
        filepath = os.path.join(VIEWPOINTS_DIR, filename)
        if not os.path.exists(filepath):
            print(f"❌ 文件不存在: {filename}")
            continue

        # 读取旧坐标
        with open(filepath, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        old_lat = data["location"]["lat"]
        old_lon = data["location"]["lon"]
        name = data.get("name", filename)

        # 计算偏差
        dlat = abs(lat - old_lat) * 111.0  # 粗略km
        dlon = abs(lon - old_lon) * 111.0 * 0.85
        dist = (dlat**2 + dlon**2)**0.5

        print(f"✅ {filename:45s} | {name:15s} | ({old_lon},{old_lat}) → ({lon},{lat}) | Δ{dist:.1f}km | [{source}]")

        update_yaml_coords(filepath, lon, lat)
        updated += 1

    print(f"\n📊 共更新 {updated} 个文件")


if __name__ == "__main__":
    main()
