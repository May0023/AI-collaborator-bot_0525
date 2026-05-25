import os
import requests
import json

# =========================
# 配置读取
# =========================
APP_ID = os.getenv("FEISHU_APP_ID")
APP_SECRET = os.getenv("FEISHU_APP_SECRET")
CHAT_ID = os.getenv("FEISHU_CHAT_ID")
LLM_API_KEY = os.getenv("LLM_API_KEY")
ROLE = os.getenv("AI_ROLE", "Buffer")

print("=== 配置检查 ===")
print(f"APP_ID: {APP_ID[:6]}...")
print(f"CHAT_ID: {CHAT_ID}")
print(f"角色: {ROLE}")


# =========================
# 1. 获取飞书 token
# =========================
def get_feishu_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"

    data = {
        "app_id": APP_ID,
        "app_secret": APP_SECRET
    }

    res = requests.post(url, json=data)
    res.raise_for_status()

    return res.json()["tenant_access_token"]


# =========================
# 2. 拉取群消息上下文
# =========================
def get_context(token):
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
        params=params
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

        except Exception:
            continue

    return "\n".join(reversed(texts))


# =========================
# 3. 调用豆包生成回复
# =========================
def call_doubao(api_key, context, role):
    print("\n正在生成回复...")

    url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    if role == "Buffer":
        prompt = f"""
你是团队 AI 协作者 Buffer。

职责：
- 总结讨论信息
- 推进流程
- 减少协作成本

回复要求：
- 简洁自然
- 1~2句话
- 像真实团队成员发言

以下是群聊内容：

{context}
"""
    else:
        prompt = f"""
你是团队 AI 协作者 Connect。

职责：
- 连接观点
- 协调依赖
- 推动跨团队协作

回复要求：
- 简洁自然
- 1~3句话
- 像真实团队成员发言

以下是群聊内容：

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
            timeout=30
        )

        result = res.json()

        reply = result["choices"][0]["message"]["content"].strip()

    except Exception as e:
        print("豆包调用失败：", e)
        reply = f"【{ROLE}】我已同步当前讨论信息，可继续推进。"

    print(f"✅ 生成回复：{reply}")

    return reply


# =========================
# 4. 发消息到飞书群（修复版）
# =========================
def send_message(token, text):

    # 注意：receive_id_type 必须放 URL 上
    url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8"
    }

    msg = f"【AI {ROLE}】\n{text}"

    payload = {
        "receive_id": CHAT_ID,
        "msg_type": "text",
        "content": json.dumps({
            "text": msg
        })
    }

    res = requests.post(
        url,
        headers=headers,
        json=payload
    )

    print(f"发送消息状态码: {res.status_code}")
    print(f"飞书返回内容: {res.text}")

    if res.status_code != 200:
        raise Exception(f"发送失败: {res.text}")


# =========================
# 主程序
# =========================
if __name__ == "__main__":
    token = get_feishu_token()
    context = get_context(token)
    reply = call_doubao(LLM_API_KEY, context, ROLE)
    send_message(token, reply)

    print("\n🎉 全部完成！")
