import os
import requests
import json

# ================== 配置 ==================
APP_ID = os.getenv("FEISHU_APP_ID")
APP_SECRET = os.getenv("FEISHU_APP_SECRET")
CHAT_ID = os.getenv("FEISHU_CHAT_ID")
API_KEY = os.getenv("LLM_API_KEY")
ROLE = os.getenv("AI_ROLE", "Buffer")

print("=== AI 协作者启动 ===", flush=True)
print("角色:", ROLE, flush=True)

# ================== 飞书 TOKEN ==================
def get_feishu_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    data = {"app_id": APP_ID, "app_secret": APP_SECRET}
    res = requests.post(url, json=data, timeout=10)
    return res.json()["tenant_access_token"]

# ================== 读取群消息 ==================
def get_context(token):
    url = "https://open.feishu.cn/open-apis/im/v1/messages"
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "container_id": CHAT_ID,
        "container_id_type": "chat",
        "page_size": 20
    }
    res = requests.get(url, headers=headers, params=params, timeout=10)
    data = res.json()
    items = data.get("data", {}).get("items", [])
    texts = []
    for item in items:
        try:
            content = item["body"]["content"]
            if isinstance(content, str):
                content = json.loads(content)
            text = content.get("text", "")
            if text and not text.startswith("【AI"):
                texts.append(text)
        except:
            continue
    return "\n".join(reversed(texts))

# ================== 通义千问 AI ==================
def ask_tongyi(context, role):
    if not context:
        return None

    url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    if role == "Buffer":
        prompt = f"你是团队协作者Buffer，总结信息、推进流程、降低协调成本，1-2句话：\n{context}"
    else:
        prompt = f"你是团队协作者Connect，连接观点、协调依赖、促进协作，1-3句话：\n{context}"

    data = {
        "model": "qwen-turbo",
        "input": {
            "messages": [{"role": "user", "content": prompt}]
        },
        "parameters": {
            "temperature": 0.3
        }
    }

    try:
        res = requests.post(url, headers=headers, json=data, timeout=15)
        response = res.json()
        return response["output"]["text"].strip()
    except Exception as e:
        print("API错误:", e, flush=True)
        return "已同步讨论内容，可继续推进。"

# ================== 发消息到飞书 ==================
def send_message(token, text):
    url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "receive_id": CHAT_ID,
        "msg_type": "text",
        "content": json.dumps({"text": f"【AI {ROLE}】{text}"})
    }
    requests.post(url, json=payload, timeout=10)
    print("✅ 已发送AI回复", flush=True)

# ================== 主程序 ==================
if __name__ == "__main__":
    try:
        token = get_feishu_token()
        context = get_context(token)
        reply = ask_tongyi(context, ROLE)
        if reply:
            send_message(token, reply)
        print("✅ 执行完成", flush=True)
    except Exception as e:
        print("❌ 错误:", e, flush=True)
