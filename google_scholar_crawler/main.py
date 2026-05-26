import os
import json
import random
import time
from datetime import datetime
from scholarly import scholarly

def main():

    # 1. 优先获取环境变量，如果为空则使用本地默认值
    scholar_id = os.environ.get("GOOGLE_SCHOLAR_ID")
    # 云端也可以配置一个名为 SOCKS_PROXY 的密文环境变量
    # SOCKS5 代理地址 (例如 "127.0.0.1:7890" 或带有账号密码的 "user:pass@ip:port")
    socks_proxy = os.environ.get("SOCKS_PROXY")

    scholar_id = scholar_id.strip() if scholar_id else None
    socks_proxy = socks_proxy.strip() if socks_proxy else None

    if not scholar_id or scholar_id == "你的GoogleScholarID":
        print("❌ 错误: 未配置 Google Scholar ID。")
        return

    print(f"🚀 开始获取学者数据，ID: {scholar_id}")

    # ==========================================
    # 防卡死核心优化 1 & 2：手动拦截 requests 并注入 SOCKS5 代理与超时
    # ==========================================
    os.environ["SOLR_TIMEOUT"] = "20"
    
    import requests
    original_get = requests.Session.get

    def timeout_and_proxy_get(self, *args, **kwargs):
        # 1. 强行注入超时时间
        kwargs['timeout'] = kwargs.get('timeout', 25)
        
        # 2. 注入 SOCKS5 代理
        if socks_proxy:
            # 格式化为 requests 识别的 socks5h:// (带 h 表示让代理服务器去解析 DNS，防污染/防卡死)
            proxy_url = f"socks5h://{socks_proxy}"
            kwargs['proxies'] = {
                "http": proxy_url,
                "https": proxy_url
            }
            # 既然用了你自己的代理，建议保留轻微伪装延时
            time.sleep(random.uniform(1.0, 2.5))
        else:
            # 如果没有配置代理，走原生网络
            time.sleep(random.uniform(1.5, 3.0))
            
        return original_get(self, *args, **kwargs)

    # 替换 requests 内部类的类方法，确保 scholarly 所有的请求都能被注入代理
    requests.Session.get = timeout_and_proxy_get
    
    if socks_proxy:
        print(f"✅ 成功通过 requests 拦截器强行注入 SOCKS5 代理 [{socks_proxy}]！")
    else:
        print("💡 未检测到有效的 SOCKS5 代理配置，将使用原生网络进行请求。")

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