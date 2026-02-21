"""为所有 viewpoint YAML 添加 groups 字段"""
from pathlib import Path

GROUP_MAP = {
    "niubei_gongga": ["gongga"],
    "gongga_lenggacuo": ["gongga"],
    "gongga_yaha_pass": ["gongga"],
    "gongga_yuzixi": ["gongga"],
    "gongga_zimei_pass": ["gongga"],
    "zheduo_gongga": ["gongga"],
    "siguniang_changping": ["siguniang"],
    "siguniang_erguniang_view": ["siguniang"],
    "siguniang_haizi_chaoshanping": ["siguniang"],
    "siguniang_maobiliang": ["siguniang"],
    "siguniang_shuangqiao": ["siguniang"],
    "yala_balangshengdu": ["yala"],
    "yala_gedilamu": ["yala"],
    "yala_gunong": ["yala"],
    "yala_tagong_view": ["yala"],
    "yala_yunrao_view": ["yala"],
    "duoraogamu_yala_view": ["yala"],
    "genie_chachongxi": ["genie"],
    "genie_eye": ["genie"],
    "genie_laolenggusi": ["genie"],
    "genie_nuda_camp": ["genie"],
    "genie_xiazetong": ["genie"],
    "yading_echushan_view": ["yading"],
    "yading_five_color_lake": ["yading"],
    "yading_luorong_pasture": ["yading"],
    "yading_milk_lake": ["yading"],
    "yading_pearl_lake": ["yading"],
    "transit_gaoersi_pass": ["318"],
    "transit_zheduoshan_pass": ["318"],
    "transit_jianziwan_pass": ["318"],
    "transit_kazila_pass": ["318"],
    "transit_xinduqiao_view": ["318"],
    "transit_jiagenba_view": ["318"],
    "transit_18bends_view": ["318"],
    "transit_daerpu_valley": ["318"],
    "transit_lixiao_redstone": ["lixiao"],
    "transit_lixiao_tunnel_view": ["lixiao"],
    "jiuzhai_wuhuahai": ["other"],
    "lianbaoyeze_zhagaer": ["other"],
    "bipenggou_panyang": ["other"],
    "dagu_4860": ["other"],
    "guergou_hot_spring_view": ["other"],
    "majiagou_main_view": ["other"],
    "mengtun_gaoqiaogou": ["other"],
    "moshi_main_view": ["other"],
    "shenmulei_redwood_view": ["other"],
    "tagong_muya": ["other"],
    "zhagushan_pass": ["other"],
}

config_dir = Path("config/viewpoints")
for yaml_file in sorted(config_dir.glob("*.yaml")):
    text = yaml_file.read_text(encoding="utf-8")
    if "\ngroups:" in text:
        continue
    vp_id = yaml_file.stem
    groups = GROUP_MAP.get(vp_id, ["other"])
    groups_yaml = "groups:\n" + "".join(f"  - {g}\n" for g in groups)
    text = text.replace("\nlocation:", f"\n{groups_yaml}location:", 1)
    yaml_file.write_text(text, encoding="utf-8")
    print(f"Updated: {yaml_file.name} -> {groups}")
