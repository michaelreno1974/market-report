#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""云端每日数据构建（GitHub Actions 定时执行，手机 H5 数据源）
拉取：大盘/行业热点/概念热点/周边市场/股指期货/推荐/属水板块
输出：report.json（供 index.html 手机端渲染）
依赖：Python 标准库 + curl（runner 自带）
"""
import json, os, re, subprocess, datetime

def http_get(url, timeout=15, referer=None):
    cmd = ["curl", "-s", "--max-time", str(timeout), "-H", "User-Agent: Mozilla/5.0"]
    if referer:
        cmd += ["-H", "Referer: " + referer]
    cmd.append(url)
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        return ""
    return r.stdout

def gbk(raw):
    return raw.decode("gbk", errors="ignore")

def fetch_index():
    raw = gbk(http_get("https://qt.gtimg.cn/q=sh000001,sz399001,sz399006"))
    out = []
    for line in raw.strip().split(";"):
        if "=" not in line: continue
        f = line.split("=", 1)[1].strip().strip('"').split("~")
        if len(f) < 40: continue
        out.append({"name": f[1], "price": float(f[3]), "pct": float(f[32])})
    return out

def fetch_board(bt, n):
    url = f"https://proxy.finance.qq.com/cgi/cgi-bin/rank/pt/getRank?board_type={bt}&sort_type=price&direct=down&offset=0&count={n}"
    try:
        d = json.loads(http_get(url).decode("utf-8", "ignore") or "{}")
        rows = ((d.get("data") or {}).get("rank_list")) or []
        out = []
        for r in rows:
            out.append({"name": r.get("name"), "zdf": float(r.get("zdf") or 0),
                        "zljlr": float(r.get("zljlr") or 0) / 10000,
                        "leader": (r.get("lzg") or {}).get("name", ""),
                        "leader_zdf": float((r.get("lzg") or {}).get("zdf") or 0)})
        out.sort(key=lambda x: x["zdf"], reverse=True)
        return out
    except Exception:
        return []

def fetch_global():
    codes = "gb_$dji,gb_$ixic,gb_$inx,hkHSI,hkHSCEI,fx_susdcny,hf_GC,hf_CL"
    out = {}
    try:
        raw = gbk(http_get(f"https://hq.sinajs.cn/list={codes}", referer="https://finance.sina.com.cn"))
        for line in raw.strip().split("\n"):
            if "=" not in line: continue
            key = line.split("=")[0].replace("var hq_str_", "").strip()
            f = line.split("=", 1)[1].strip().strip('"').split(",")
            try:
                if key == "gb_$dji": out["道琼斯"] = (float(f[1]), float(f[2]))
                elif key == "gb_$ixic": out["纳斯达克"] = (float(f[1]), float(f[2]))
                elif key == "gb_$inx": out["标普500"] = (float(f[1]), float(f[2]))
                elif key == "hkHSI": out["恒生指数"] = (float(f[2]), float(f[8]))
                elif key == "hkHSCEI": out["国企指数"] = (float(f[2]), float(f[8]))
                elif key == "fx_susdcny": out["美元/人民币"] = (float(f[1]), 0)
                elif key == "hf_GC": out["纽约黄金"] = (float(f[0]), 0)
                elif key == "hf_CL": out["纽约原油"] = (float(f[0]), 0)
            except (ValueError, IndexError):
                pass
    except Exception:
        pass
    return out

def fetch_futures():
    today = datetime.date.today()
    out = []
    for prod in ("IF", "IH", "IC", "IM"):
        try:
            url = f"http://www.cffex.com.cn/sj/ccpm/{today:%Y%m}/{today:%d}/{prod}.xml"
            xml = http_get(url).decode("utf-8", "ignore")
            blocks = re.findall(r"<data[^>]*>.*?</data>", xml, re.S)
            rows = []
            for b in blocks:
                def g(t):
                    m = re.search(r"<%s>(.*?)</%s>" % (t, t), b)
                    return m.group(1) if m else ""
                try:
                    rows.append({"instr": g("instrumentid"), "dtype": g("datatypeid"),
                                 "name": g("shortname"), "vol": int(g("volume") or 0),
                                 "vvol": int(g("varvolume") or 0)})
                except ValueError:
                    pass
            longs = [r for r in rows if r["dtype"] == "1"]
            vol = {}
            for r in longs: vol[r["instr"]] = vol.get(r["instr"], 0) + r["vol"]
            if not vol: continue
            main = max(vol, key=vol.get)
            ml = [r for r in rows if r["instr"] == main and r["dtype"] == "1"]
            ms = [r for r in rows if r["instr"] == main and r["dtype"] == "2"]
            cl = sum(r["vol"] for r in ml if "中信" in r["name"])
            cs = sum(r["vol"] for r in ms if "中信" in r["name"])
            cdl = sum(r["vvol"] for r in ml if "中信" in r["name"])
            cds = sum(r["vvol"] for r in ms if "中信" in r["name"])
            out.append({"prod": prod, "main": main,
                        "net20": sum(r["vol"] for r in ml) - sum(r["vol"] for r in ms),
                        "citic_net": cs - cl, "citic_dnet": cds - cdl})
        except Exception:
            pass
    return out

def fetch_picks():
    VALID = ("600", "601", "603", "605", "688", "000", "001", "002", "003", "300", "301")
    picks = []
    try:
        raw = http_get("https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData?page=1&num=12&sort=changepercent&asc=0&node=hs_a&symbol=&_s_r_a=init").decode("utf-8", "ignore")
        for r in json.loads(raw or "[]"):
            name, sym = r.get("name") or "", r.get("symbol") or ""
            if "ST" in name or name.startswith("N") or sym.startswith("bj"): continue
            code = r.get("code") or ""
            if code[:3] not in VALID: continue
            picks.append({"code": code, "name": name, "pct": float(r.get("changepercent") or 0), "src": "涨幅榜"})
    except Exception:
        pass
    try:
        raw = http_get("https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/MoneyFlow.ssl_bkzj_ssggzj?page=1&num=8&sort=netamount&asc=0&daima=hs_a", referer="https://finance.sina.com.cn").decode("utf-8", "ignore")
        for r in json.loads(raw or "[]"):
            name, sym = r.get("name") or "", r.get("symbol") or ""
            if "ST" in name: continue
            code = (sym or "")[2:]
            if code[:3] not in VALID: continue
            if any(p["code"] == code for p in picks): continue
            picks.append({"code": code, "name": name,
                          "pct": float(r.get("changeratio") or 0) * 100,
                          "src": f"资金{float(r.get('netamount') or 0)/1e8:+.1f}亿"})
    except Exception:
        pass
    return picks[:15]

def fetch_water(con):
    kw = ["水务", "港口", "航运", "海运", "旅游", "白酒", "饮料", "传媒", "文化", "物流", "水产", "酒店"]
    rows = [b for b in con if any(k in (b["name"] or "") for k in kw)]
    return [{"name": b["name"], "zdf": b["zdf"], "zljlr": b["zljlr"], "leader": b["leader"]} for b in rows[:6]]

def main():
    print("[1/6] 大盘 ...")
    index = fetch_index()
    print("[2/6] 行业热点 ...")
    ind = fetch_board("hy", 100)
    print("[3/6] 概念热点 ...")
    con = fetch_board("gn", 200)
    print("[4/6] 周边市场 ...")
    g = fetch_global()
    print("[5/6] 股指期货 ...")
    fut = fetch_futures()
    print("[6/6] 推荐与属水 ...")
    picks = fetch_picks()
    water = fetch_water(con)
    payload = {
        "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "index": index, "industry": ind[:8], "concept": con[:5],
        "global": g, "futures": fut, "picks": picks, "water": water,
        "note": "来源：腾讯财经/新浪财经/中金所。盘中数据为当时快照，收盘后为完整数据。属水为个人偏好维度。",
    }
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "report.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    print("完成 report.json")
    for i in index: print(f"  {i['name']} {i['price']} ({i['pct']:+.2f}%)")
    print("  热点:", " | ".join(f"{b['name']} {b['zdf']:+.1f}%" for b in ind[:3]))
    print("  期货:", " ".join(f"{x['prod']}{x['citic_dnet']:+d}" for x in fut))
    print("  推荐:", len(picks), "只 | 属水板块:", len(water))

if __name__ == "__main__":
    main()
