import os
import json
import random
import time
from datetime import datetime
from scholarly import scholarly, ProxyGenerator

def main():
    # 1. 检查环境变量
    scholar_id = os.environ.get("GOOGLE_SCHOLAR_ID")
    if not scholar_id:
        print("❌ 错误: 未找到环境变量 GOOGLE_SCHOLAR_ID")
        return

    print(f"🚀 开始获取学者数据，ID: {scholar_id}")

    # ==========================================
    # 防卡死核心优化 1：设置全局网络超时与反爬轻度伪装
    # ==========================================
    # scholarly 底层使用 requests，我们可以通过环境变量强制设定全局超时时间（单位：秒）
    os.environ["SOLR_TIMEOUT"] = "15"  # 限制内部某些组件超时
    
    # 强制为 scholarly 内部的 requests 会话注入超时
    # 这样即使被 Google 拦截或断网，15秒内一定会抛出异常，绝不无限制卡死
    import requests
    original_get = requests.Session.get
    def timeout_get(*args, **kwargs):
        kwargs['timeout'] = kwargs.get('timeout', 15)
        # 顺便加入随机延迟，模拟人类人类行为，降低被封锁概率
        time.sleep(random.uniform(1.0, 3.0))
        return original_get(*args, **kwargs)
    requests.Session.get = timeout_get

    try:
        # 2. 基础信息查询
        author = scholarly.search_author_id(scholar_id)
        
        # ==========================================
        # 防卡死核心优化 2：分步填充（Step-by-step filling）与异常捕获
        # ==========================================
        print("📥 正在分步拉取学者基础、指数及计数数据...")
        scholarly.fill(author, sections=["basics", "indices", "counts"])
        
        # 将 publications 的填充单独剥离，因为这一步最容易因论文过多触发反爬卡死
        try:
            print("📥 正在尝试拉取详细论文列表（此步骤最易触发 Google 拦截）...")
            scholarly.fill(author, sections=["publications"])
        except Exception as pub_err:
            print(f"⚠️ 警告: 论文列表详细数据拉取失败 (可能触发了Google人机验证). 错误信息: {pub_err}")
            print("💡 系统将保留已获取的基础引用数据，继续生成报告，防止整个任务崩溃。")
            if "publications" not in author:
                author["publications"] = []

        # 3. 数据清洗与加工
        author["updated"] = str(datetime.now())
        
        # 兼容处理：确保 publications 是列表且可以被正确转化
        if isinstance(author.get("publications"), list):
            author["publications"] = {v["author_pub_id"]: v for v in author if "author_pub_id" in v}
        elif isinstance(author.get("publications"), dict):
            pass # 已经是字典格式则不处理
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
        # 如果因为某些原因极度不顺（比如第一步就挂了），退出并返回非0代码让 Action 报错
        exit(1)

if __name__ == "__main__":
    main()