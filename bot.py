import os
import requests
import json

# ================== 配置 ==================
APP_ID = os.getenv("FEISHU_APP_ID")
APP_SECRET = os.getenv("FEISHU_APP_SECRET")
CHAT_ID = os.getenv("FEISHU_CHAT_ID")
LLM_API_KEY = os.getenv("LLM_API_KEY")
ROLE = os.getenv("AI_ROLE", "Buffer")

print("=== 启动 AI 协作者 ===", flush=True)
print(f"群ID: {CHAT_ID}", flush=True)
print(f"角色: {ROLE}", flush=True)


# ================== 获取飞书 TOKEN ==================
def get_feishu_token():
    print("获取飞书 token...", flush=True)

    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"

    data = {
        "app_id": APP_ID,
        "app_secret": APP_SECRET
    }

    res = requests.post(
        url,
        json=data,
        timeout=10
    )

    return res.json()["tenant_access_token"]


# ================== 读取群消息 ==================
def get_context(token):
    print("读取群消息...", flush=True)

    url = "https://open.feishu.cn/open-apis/im/v1/messages"

    headers = {
        "Authorization": f"Bearer {token}"
    }

    params = {
        "container_id": CHAT_ID,
        "container_id_type": "chat",
        "page_size": 20
    }

    res = requests.get(
        url,
        headers=headers,
        params=params,
        timeout=10
    )

    data = res.json()

    items = data.get("data", {}).get("items", [])

    texts = []

    for item in items:
        try:
            content = item["body"]["content"]

            if isinstance(content, str):
                content = json.loads(content)

            text = content.get("text", "")

            if text:
                texts.append(text)

        except:
            continue

    return "\n".join(reversed(texts))


# ================== 调用豆包 ==================
def call_doubao(context, role):
    print("调用豆包生成回复...", flush=True)

    # 注意这里修正了
    url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"

    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json"
    }

    if role == "Buffer":
        prompt = f"""
你是团队协作者 Buffer。

职责：
总结信息、推进流程、降低协调成本。

请基于以下群聊内容自然回复1-2句话：

{context}
"""
    else:
        prompt = f"""
你是团队协作者 Connect。

职责：
连接观点、协调依赖、促进协作。

请基于以下群聊内容自然回复1-3句话：

{context}
"""

    data = {
        "model": "doubao-lite-4k",
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    }

    try:
        res = requests.post(
            url,
            headers=headers,
            json=data,
            timeout=15
        )

        result = res.json()

        return result["choices"][0]["message"]["content"].strip()

    except Exception as e:
        print("豆包调用失败:", e, flush=True)
        return "已同步本次讨论信息。"


# ================== 发消息到飞书 ==================
def send_message(token, text):
    print("发送飞书消息...", flush=True)

    url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    payload = {
        "receive_id": CHAT_ID,
        "msg_type": "text",
        "content": json.dumps({
            "text": f"【AI {ROLE}】{text}"
        })
    }

    res = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=10
    )

    print("飞书返回:", res.text, flush=True)


# ================== 主程序（单次运行）
# ==================
if __name__ == "__main__":
    try:
        token = get_feishu_token()

        context = get_context(token)

        if context:
            reply = call_doubao(context, ROLE)
            send_message(token, reply)

        print("✅ 执行完成", flush=True)

    except Exception as e:
        print(f"❌ 错误: {e}", flush=True)
