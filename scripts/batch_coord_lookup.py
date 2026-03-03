"""
批量查询高德 POI 坐标，转换为 WGS-84，并更新 YAML 文件。

用法:
    python scripts/batch_coord_lookup.py         # 查询所有
    python scripts/batch_coord_lookup.py --dry    # 仅查询，不修改文件
"""
import math
import json
import urllib.request
import urllib.parse
import ssl
import yaml
import os
import sys
import time

# macOS SSL 证书问题修复
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

PI = math.pi
A = 6378245.0
EE = 0.00669342162296594323
AMAP_KEY = "d13989c82f1d06d53a7662424c25348c"
VIEWPOINTS_DIR = os.path.join(os.path.dirname(__file__), "..", "config", "viewpoints")


def _transform_lat(lng, lat):
    ret = -100.0 + 2.0 * lng + 3.0 * lat + 0.2 * lat * lat + 0.1 * lng * lat + 0.2 * math.sqrt(abs(lng))
    ret += (20.0 * math.sin(6.0 * lng * PI) + 20.0 * math.sin(2.0 * lng * PI)) * 2.0 / 3.0
    ret += (20.0 * math.sin(lat * PI) + 40.0 * math.sin(lat / 3.0 * PI)) * 2.0 / 3.0
    ret += (160.0 * math.sin(lat / 12.0 * PI) + 320 * math.sin(lat * PI / 30.0)) * 2.0 / 3.0
    return ret


def _transform_lng(lng, lat):
    ret = 300.0 + lng + 2.0 * lat + 0.1 * lng * lng + 0.1 * lng * lat + 0.1 * math.sqrt(abs(lng))
    ret += (20.0 * math.sin(6.0 * lng * PI) + 20.0 * math.sin(2.0 * lng * PI)) * 2.0 / 3.0
    ret += (20.0 * math.sin(lng * PI) + 40.0 * math.sin(lng / 3.0 * PI)) * 2.0 / 3.0
    ret += (150.0 * math.sin(lng / 12.0 * PI) + 300.0 * math.sin(lng / 30.0 * PI)) * 2.0 / 3.0
    return ret


def gcj02_to_wgs84(gcj_lng, gcj_lat):
    dlat = _transform_lat(gcj_lng - 105.0, gcj_lat - 35.0)
    dlng = _transform_lng(gcj_lng - 105.0, gcj_lat - 35.0)
    radlat = gcj_lat / 180.0 * PI
    magic = math.sin(radlat)
    magic = 1 - EE * magic * magic
    sqrtmagic = math.sqrt(magic)
    dlat = (dlat * 180.0) / ((A * (1 - EE)) / (magic * sqrtmagic) * PI)
    dlng = (dlng * 180.0) / (A / sqrtmagic * math.cos(radlat) * PI)
    return round(gcj_lng - dlng, 6), round(gcj_lat - dlat, 6)


def search_poi(keyword, city="", types=""):
    """使用高德 POI 搜索 API"""
    params = {
        "key": AMAP_KEY,
        "keywords": keyword,
        "output": "JSON",
        "offset": 5,
        "page": 1,
        "extensions": "base",
    }
    if city:
        params["city"] = city
    if types:
        params["types"] = types
    url = "https://restapi.amap.com/v3/place/text?" + urllib.parse.urlencode(params)
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10, context=SSL_CTX) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if data.get("status") == "1" and data.get("pois"):
            return data["pois"]
    except Exception as e:
        print(f"  ⚠️ API 请求失败: {e}")
    return []


# 每个观景台的搜索策略: (文件名, 搜索关键词列表, 城市限定)
SEARCH_CONFIG = [
    # Task 1: 四姑娘山
    ("siguniang_maobiliang.yaml", ["猫鼻梁观景台", "猫鼻梁"], "阿坝"),
    ("siguniang_changping.yaml", ["长坪沟景区", "四姑娘山长坪沟"], "阿坝"),
    ("siguniang_shuangqiao.yaml", ["双桥沟景区", "四姑娘山双桥沟"], "阿坝"),
    ("siguniang_haizi_chaoshanping.yaml", ["海子沟景区", "海子沟朝山坪"], "阿坝"),
    ("siguniang_erguniang_view.yaml", ["四姑娘山二峰", "二峰大本营"], "阿坝"),
    # Task 2: 贡嘎山
    ("gongga_lenggacuo.yaml", ["冷嘎措", "冷噶措"], "甘孜"),
    ("gongga_niubei.yaml", ["牛背山景区", "牛背山"], "雅安"),
    ("gongga_yaha_pass.yaml", ["雅哈垭口"], "甘孜"),
    ("gongga_yuzixi.yaml", ["鱼子西", "鱼子西观景台"], "甘孜"),
    ("gongga_zimei_pass.yaml", ["子梅垭口"], "甘孜"),
    # Task 3: 格聂
    ("genie_eye.yaml", ["格聂之眼"], "甘孜"),
    ("genie_chachongxi.yaml", ["查冲西村", "格聂查冲西"], "甘孜"),
    ("genie_laolenggusi.yaml", ["冷古寺", "格聂冷古寺"], "甘孜"),
    ("genie_nuda_camp.yaml", ["虎皮坝", "格聂营地"], "甘孜"),
    ("genie_xiazetong.yaml", ["下则通村", "格聂下则通"], "甘孜"),
    # Task 4: 亚丁
    ("yading_echushan_view.yaml", ["俄初山观景台", "俄初山"], "甘孜"),
    ("yading_five_color_lake.yaml", ["五色海", "亚丁五色海"], "甘孜"),
    ("yading_luorong_pasture.yaml", ["洛绒牛场"], "甘孜"),
    ("yading_milk_lake.yaml", ["牛奶海", "亚丁牛奶海"], "甘孜"),
    ("yading_pearl_lake.yaml", ["珍珠海", "卓玛拉措"], "甘孜"),
    # Task 5: 亚拉雪山
    ("yala_balangshengdu.yaml", ["八郎生都", "八郎生都日落"], "甘孜"),
    ("yala_gedilamu.yaml", ["格底拉姆", "雅拉格底拉姆"], "甘孜"),
    ("yala_gunong.yaml", ["姑弄村", "道孚姑弄"], "甘孜"),
    ("yala_tagong_view.yaml", ["塔公草原", "塔公寺"], "甘孜"),
    ("yala_yunrao_view.yaml", ["云绕亚拉", "亚拉雪山观景台"], "甘孜"),
    # Task 6: 交通沿线
    ("tagong_muya.yaml", ["木雅金塔", "塔公木雅金塔"], "甘孜"),
    ("transit_18bends_view.yaml", ["天路十八弯观景台", "天路十八弯"], "甘孜"),
    ("transit_daerpu_valley.yaml", ["达尔普", "大二普", "毕棚沟"], "阿坝"),
    ("transit_gaoersi_pass.yaml", ["高尔寺山", "高尔寺山垭口"], "甘孜"),
    ("transit_jiagenba_view.yaml", ["甲根坝", "甲根坝镇"], "甘孜"),
    ("transit_jianziwan_pass.yaml", ["剪子弯山", "G318剪子弯山"], "甘孜"),
    ("transit_kazila_pass.yaml", ["卡子拉山", "卡子拉山垭口"], "甘孜"),
    ("transit_lixiao_redstone.yaml", ["凉台沟", "理小路红石滩"], "阿坝"),
    ("transit_lixiao_tunnel_view.yaml", ["理小隧道", "简阳坪隧道"], "阿坝"),
    ("transit_xinduqiao_view.yaml", ["新都桥镇", "新都桥"], "甘孜"),
    ("transit_zheduoshan_pass.yaml", ["折多山垭口", "折多山"], "甘孜"),
    # Task 7: 其他独立景区
    ("bipenggou_panyang.yaml", ["毕棚沟磐羊湖", "毕棚沟景区"], "阿坝"),
    ("dagu_4860.yaml", ["达古冰川", "达古冰川4860"], "阿坝"),
    ("duoraogamu_yala_view.yaml", ["墨石公园景区", "墨石公园"], "甘孜"),
    ("guergou_hot_spring_view.yaml", ["牟尼沟", "二道海"], "阿坝"),
    ("jiuzhai_wuhuahai.yaml", ["五花海", "九寨沟五花海"], "阿坝"),
    ("lianbaoyeze_zhagaer.yaml", ["扎尕尔措", "莲宝叶则"], "阿坝"),
    ("majiagou_main_view.yaml", ["磨西古镇", "海螺沟景区"], "甘孜"),
    ("mengtun_gaoqiaogou.yaml", ["孟屯河谷", "高桥沟"], "阿坝"),
    ("moshi_main_view.yaml", ["墨石公园", "八美墨石公园"], "甘孜"),
    ("zhagushan_pass.yaml", ["鹧鸪山", "鹧鸪山垭口"], "阿坝"),
    # Task 8: 牛背山、神木垒、折多山
    ("niubei.yaml", ["牛背山", "牛背山景区"], "雅安"),
    ("shenmulei_redwood_view.yaml", ["神木垒", "神木垒景区"], "雅安"),
    ("zheduo.yaml", ["折多山", "折多山观景台"], "甘孜"),
]


def main():
    dry_run = "--dry" in sys.argv
    results = []

    for filename, keywords, city in SEARCH_CONFIG:
        filepath = os.path.join(VIEWPOINTS_DIR, filename)
        if not os.path.exists(filepath):
            print(f"❌ 文件不存在: {filename}")
            continue

        with open(filepath, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        current_lat = data["location"]["lat"]
        current_lon = data["location"]["lon"]
        name = data.get("name", filename)

        print(f"\n🔍 [{filename}] {name}")
        print(f"   当前坐标: ({current_lon}, {current_lat})")

        best_poi = None
        for kw in keywords:
            pois = search_poi(kw, city=city)
            if pois:
                best_poi = pois[0]
                print(f"   ✅ 找到: {best_poi['name']} ({best_poi.get('address', '')})")
                break
            time.sleep(0.3)  # 避免频率限制

        if best_poi:
            gcj_lng, gcj_lat = [float(x) for x in best_poi["location"].split(",")]
            wgs_lng, wgs_lat = gcj02_to_wgs84(gcj_lng, gcj_lat)
            print(f"   GCJ-02: ({gcj_lng}, {gcj_lat})")
            print(f"   WGS-84: ({wgs_lng}, {wgs_lat})")

            results.append({
                "file": filename,
                "name": name,
                "poi_name": best_poi["name"],
                "poi_address": best_poi.get("address", ""),
                "gcj02_lng": gcj_lng,
                "gcj02_lat": gcj_lat,
                "wgs84_lng": wgs_lng,
                "wgs84_lat": wgs_lat,
                "old_lat": current_lat,
                "old_lon": current_lon,
            })
        else:
            print(f"   ❌ 未找到 POI")
            results.append({
                "file": filename,
                "name": name,
                "poi_name": None,
                "wgs84_lng": None,
                "wgs84_lat": None,
                "old_lat": current_lat,
                "old_lon": current_lon,
            })

        time.sleep(0.2)

    # 输出汇总
    print("\n" + "=" * 80)
    print("📊 POI 查询结果汇总")
    print("=" * 80)
    for r in results:
        if r.get("wgs84_lat"):
            print(f"{r['file']:45s} | {r['name']:15s} | POI: {r['poi_name']:20s} | WGS84: ({r['wgs84_lng']}, {r['wgs84_lat']})")
        else:
            print(f"{r['file']:45s} | {r['name']:15s} | ❌ 未找到")

    # 保存 JSON 供后续使用
    out_path = os.path.join(os.path.dirname(__file__), "coord_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n📝 结果已保存到: {out_path}")


if __name__ == "__main__":
    main()
