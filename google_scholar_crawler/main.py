import os
import json
import random
import time
from datetime import datetime
from scholarly import scholarly, ProxyGenerator

def main():
    # 1. 优先检查并获取所有环境变量
    scholar_id = os.environ.get("GOOGLE_SCHOLAR_ID")
    scraper_key = os.environ.get("SCRAPERAPI_KEY")

    if not scholar_id:
        print("❌ 错误: 未找到环境变量 GOOGLE_SCHOLAR_ID")
        return

    print(f"🚀 开始获取学者数据，ID: {scholar_id}")

    # ==========================================
    # 防卡死核心优化 1：注入商业级免封锁代理
    # ==========================================
    if scraper_key:
        try:
            pg = ProxyGenerator()
            success = pg.ScraperAPI(scraper_key)
            if success:
                scholarly.use_proxy(pg)
                print("✅ 成功注入商业级免封锁代理！")
            else:
                print("⚠️ 代理激活返回失败，将尝试使用原生网络...")
        except Exception as proxy_err:
            print(f"⚠️ 注入代理时发生异常: {proxy_err}，转为原生网络...")
    else:
        print("⚠️ 未检测到 SCRAPERAPI_KEY，将使用原生网络（在 GitHub Actions 中极易卡死）")

    # ==========================================
    # 防卡死核心优化 2：设置全局网络超时与反爬轻度伪装
    # ==========================================
    os.environ["SOLR_TIMEOUT"] = "20"  # 适当延长到 20 秒，给代理节点留出响应时间
    
    import requests
    original_get = requests.Session.get
    def timeout_get(*args, **kwargs):
        # 如果走 ScraperAPI 代理，节点切换有时需要较长时间，这里给 25 秒防死锁超时
        kwargs['timeout'] = kwargs.get('timeout', 25)
        # 既然用了付费商业代理，可以减少不必要的等待，这里设为轻微的 0.5 ~ 1.5 秒
        time.sleep(random.uniform(0.5, 1.5))
        return original_get(*args, **kwargs)
    requests.Session.get = timeout_get

    try:
        # 2. 基础信息查询
        print("📥 正在检索学者基础 ID 节点...")
        author = scholarly.search_author_id(scholar_id)
        
        # ==========================================
        # 防卡死核心优化 3：分步填充与异常隔离
        # ==========================================
        print("📥 正在分步拉取学者基础、指数及计数数据...")
        scholarly.fill(author, sections=["basics", "indices", "counts"])
        
        # 将 publications 的填充单独剥离，由于调用了 ScraperAPI，这一步的成功率会暴增
        try:
            print("📥 正在尝试拉取详细论文列表（通过代理进行）...")
            # scholarly.fill(author, sections=["publications"])
        except Exception as pub_err:
            print(f"⚠️ 警告: 论文列表详细数据拉取失败. 错误信息: {pub_err}")
            print("💡 系统将保留已获取的基础引用数据，继续生成报告，防止整个任务崩溃。")
            if "publications" not in author:
                author["publications"] = []

        # 3. 数据清洗与加工 (修正了原代码的循环 Bug)
        author["updated"] = str(datetime.now())
        
        if isinstance(author.get("publications"), list):
            # ✅ 修复：遍历目标改为列表本身 author["publications"]
            author["publications"] = {
                v["author_pub_id"]: v for v in author["publications"] if "author_pub_id" in v
            }
        elif isinstance(author.get("publications"), dict):
            pass 
        else:
            author["publications"] = {}

        # 4. 创建结果目录并持久化
        os.makedirs("results", exist_ok=True)
        
        # 写入主数据
        with open("results/gs_data.json", "w", encoding="utf-8") as outfile:
            json.dump(author, outfile, ensure_ascii=False, indent=2)
        print("✅ 主数据 `gs_data.json` 写入成功。")

        # 写入 Shields.io 徽章数据
        shieldio_data = {
            "schemaVersion": 1,
            "label": "citations",
            "message": f"{author.get('citedby', 0)}",
            "color": "brightgreen"
        }
        with open("results/gs_data_shieldsio.json", "w", encoding="utf-8") as outfile:
            json.dump(shieldio_data, outfile, ensure_ascii=False, indent=2)
        print(f"✅ 徽章数据写入成功。当前总引用量: {author.get('citedby', 0)}")

    except Exception as e:
        print(f"❌ 运行过程中遭遇致命错误: {e}")
        exit(1)

if __name__ == "__main__":
    main()