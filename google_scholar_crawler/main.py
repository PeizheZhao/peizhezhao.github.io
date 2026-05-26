import os
import json
import random
import time
from datetime import datetime
from scholarly import scholarly, ProxyGenerator

def main():
# 1. 优先获取环境变量，如果为空则使用本地默认值
    scholar_id = os.environ.get("GOOGLE_SCHOLAR_ID")
    scraper_key = os.environ.get("SCRAPERAPI_KEY")

    scholar_id = scholar_id.strip() if scholar_id else None
    scraper_key = scraper_key.strip() if scraper_key else None

    if not scholar_id or scholar_id == "你的GoogleScholarID":
        print("❌ 错误: 未配置 Google Scholar ID。")
        return

    print(f"🚀 开始获取学者数据，ID: {scholar_id}")

    # ==========================================
    # 防卡死核心优化 1 & 2：手动拦截 requests 并注入 ScraperAPI 代理与超时
    # ==========================================
    os.environ["SOLR_TIMEOUT"] = "20"
    
    import requests
    original_get = requests.Session.get

    def timeout_and_proxy_get(self, *args, **kwargs):
        # 1. 强行注入超时时间
        kwargs['timeout'] = kwargs.get('timeout', 25)
        
        # 2. 绕过 scholarly 报错组件，手动注入 ScraperAPI 的官方标准代理
        if scraper_key:
            # ScraperAPI 的标准 HTTP 代理格式
            proxy_url = f"http://scraperapi:{scraper_key}@proxy-server.scraperapi.com:8001"
            kwargs['proxies'] = {
                "http": proxy_url,
                "https": proxy_url
            }
            # 走商业代理时，Google 判定为真人，不需要高延时，轻微伪装即可
            time.sleep(random.uniform(0.3, 1.0))
        else:
            # 如果没有 Key，走原生网络，加入较高延迟降低被封概率
            time.sleep(random.uniform(1.5, 3.0))
            
        return original_get(self, *args, **kwargs)

    # 替换 requests 内部类的类方法，确保 scholarly 所有的请求都能被注入代理
    requests.Session.get = timeout_and_proxy_get
    
    if scraper_key:
        print("✅ 成功通过 requests 拦截器强行注入 ScraperAPI 商业代理！")
    else:
        print("💡 未检测到有效的 SCRAPERAPI_KEY，将使用原生网络进行请求。")

    try:
        # 2. 基础信息查询
        print("📥 正在检索学者基础 ID 节点...")
        author = scholarly.search_author_id(scholar_id)
        
        # ==========================================
        # 防卡死核心优化 3：分步填充与异常隔离
        # ==========================================
        print("📥 正在分步拉取学者基础、指数及计数数据...")
        scholarly.fill(author, sections=["basics", "indices", "counts"])
        
        try:
            print("📥 正在尝试拉取详细论文列表...")
            # scholarly.fill(author, sections=["publications"])
        except Exception as pub_err:
            print(f"⚠️ 警告: 论文列表详细数据拉取失败. 错误信息: {pub_err}")
            if "publications" not in author:
                author["publications"] = []

        # 3. 数据清洗与加工
        author["updated"] = str(datetime.now())
        
        if isinstance(author.get("publications"), list):
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
        print("✅ 主数据 `results/gs_data.json` 写入成功。")

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