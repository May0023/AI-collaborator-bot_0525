import os
import requests
import json
import time

APP_ID = os.getenv("FEISHU_APP_ID")
APP_SECRET = os.getenv("FEISHU_APP_SECRET")
CHAT_ID = os.getenv("FEISHU_CHAT_ID")
LLM_API_KEY = os.getenv("LLM_API_KEY")
ROLE = os.getenv("AI_ROLE", "Buffer")

print("=== AI Collaborator Bot Started ===")
print(f"CHAT_ID: {CHAT_ID}")
print(f"ROLE: {ROLE}")


# 获取飞书 token
def get_feishu_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"

    data = {
        "app_id": APP_ID,
        "app_secret": APP_SECRET
    }

    res = requests.post(url, json=data)
    return res.json()["tenant_access_token"]


# 获取最近消息 + 最新 message_id
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

        except:
            pass

    latest_message_id = items[0]["message_id"] if items else None

    return "\n".join(reversed(texts)), latest_message_id


# 调豆包
def call_doubao(context, role):

    url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"

    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json"
    }

    if role == "Buffer":
        prompt = f"""
你是团队AI协作者 Buffer。

职责：
- 总结讨论
- 推进流程
- 降低协调成本

要求：
- 回复自然
- 简洁
- 不超过2句话

群聊内容：
{context}
"""
    else:
        prompt = f"""
你是团队AI协作者 Connect。

职责：
- 连接观点
- 协调依赖
- 推进协作

要求：
- 回复自然
- 简洁
- 不超过3句话

群聊内容：
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

        return result["choices"][0]["message"]["content"].strip()

    except Exception as e:
        print("豆包调用失败:", e)
        return None


# 发回飞书
def send_message(token, text):

    url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    payload = {
        "receive_id": CHAT_ID,
        "msg_type": "text",
        "content": json.dumps({
            "text": f"【AI {ROLE}】\n{text}"
        })
    }

    res = requests.post(
        url,
        headers=headers,
        json=payload
    )

    print("发送状态:", res.status_code)
    print(res.text)


# 主循环：每10秒检查一次
if __name__ == "__main__":

    token = get_feishu_token()

    last_message_id = None

    while True:
        try:
            context, latest_message_id = get_context(token)

            if latest_message_id != last_message_id:

                print("\n检测到新消息，开始生成回复...")

                reply = call_doubao(context, ROLE)

                if reply:
                    send_message(token, reply)

                last_message_id = latest_message_id

            else:
                print("无新消息，10秒后继续检查...")

        except Exception as e:
            print("运行异常：", e)

        time.sleep(10)
