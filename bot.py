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
    res = requests.post(url, json={
        "app_id": APP_ID,
        "app_secret": APP_SECRET
    }, timeout=10)

    print("TOKEN响应:", res.text, flush=True)

    data = res.json()
    if "tenant_access_token" not in data:
        raise Exception(f"获取token失败: {data}")

    return data["tenant_access_token"]


# ================== 获取群消息 ==================
def get_context(token):
    url = "https://open.feishu.cn/open-apis/im/v1/messages"
    headers = {"Authorization": f"Bearer {token}"}

    res = requests.get(url, headers=headers, params={
        "container_id": CHAT_ID,
        "container_id_type": "chat",
        "page_size": 20
    }, timeout=10)

    print("消息API返回:", res.text, flush=True)

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

        except Exception as e:
            print("解析消息失败:", e, flush=True)

    context = "\n".join(reversed(texts))
    print("context长度:", len(context), flush=True)

    return context


# ================== 通义千问 ==================
def ask_tongyi(context, role):
    if not context:
        print("⚠️ context为空，跳过LLM", flush=True)
        return None

    url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    prompt = (
        f"你是{role}，"
        f"总结并推进讨论，用1-2句话：\n{context}"
        if role == "Buffer"
        else
        f"你是{role}，连接观点，用1-3句话：\n{context}"
    )

    data = {
        "model": "qwen-turbo",
        "input": {
            "messages": [
                {"role": "user", "content": prompt}
            ]
        },
        "parameters": {
            "temperature": 0.3
        }
    }

    res = requests.post(url, headers=headers, json=data, timeout=15)

    print("LLM原始返回:", res.text, flush=True)

    try:
        data = res.json()
        return data["output"]["text"].strip()
    except Exception as e:
        print("LLM解析失败:", e, flush=True)
        return None


# ================== 发消息 ==================
def send_message(token, text):
    url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"

    payload = {
        "receive_id": CHAT_ID,
        "msg_type": "text",
        "content": json.dumps({"text": f"【AI {ROLE}】{text}"})
    }

    res = requests.post(
        url,
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
        timeout=10
    )

    print("飞书发送响应:", res.text, flush=True)

    if res.status_code != 200:
        raise Exception(f"飞书发送失败 HTTP {res.status_code}")


# ================== 主程序 ==================
if __name__ == "__main__":
    try:
        token = get_feishu_token()

        context = get_context(token)

        print("最终context:", context, flush=True)

        reply = ask_tongyi(context, ROLE)

        print("LLM回复:", reply, flush=True)

        if reply:
            send_message(token, reply)
            print("✅ 已发送成功", flush=True)
        else:
            print("⚠️ 没有生成回复", flush=True)

        print("✅ 执行完成", flush=True)

    except Exception as e:
        print("❌ 全局错误:", str(e), flush=True)
        raise
