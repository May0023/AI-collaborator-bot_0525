import os
import requests
import json

# ================== 配置 ==================
APP_ID = os.getenv("FEISHU_APP_ID")
APP_SECRET = os.getenv("FEISHU_APP_SECRET")
CHAT_ID = os.getenv("FEISHU_CHAT_ID")
LLM_API_KEY = os.getenv("LLM_API_KEY")
ROLE = os.getenv("AI_ROLE", "Buffer")

STATE_FILE = "state.json"

print("=== 启动 AI 协作者 ===", flush=True)
print(f"角色: {ROLE}", flush=True)

# ================== 状态管理 ==================
def load_state():
    if not os.path.exists(STATE_FILE):
        return {"last_message_id": None}
    with open(STATE_FILE, "r") as f:
        return json.load(f)


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


# ================== 获取飞书 TOKEN ==================
def get_feishu_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    data = {"app_id": APP_ID, "app_secret": APP_SECRET}
    res = requests.post(url, json=data, timeout=8)
    res.raise_for_status()
    return res.json()["tenant_access_token"]


# ================== 读取群消息（带去重） ==================
def get_context(token, last_id):
    url = "https://open.feishu.cn/open-apis/im/v1/messages"
    headers = {"Authorization": f"Bearer {token}"}

    res = requests.get(
        url,
        headers=headers,
        params={
            "container_id": CHAT_ID,
            "container_id_type": "chat",
            "page_size": 20
        },
        timeout=8
    )

    data = res.json()
    items = data.get("data", {}).get("items", [])

    if not items:
        return "", None

    texts = []
    new_last_id = items[0].get("message_id")

    for item in items:
        msg_id = item.get("message_id")

        # 🔥 去重关键：遇到旧消息停止
        if msg_id == last_id:
            break

        try:
            content = item["body"]["content"]
            if isinstance(content, str):
                content = json.loads(content)

            text = content.get("text", "")
            if text and not text.startswith("【AI"):
                texts.append(text)

        except:
            continue

    return "\n".join(reversed(texts)), new_last_id


# ================== 调用豆包 ==================
def call_doubao(context, role):
    if not context:
        return None

    url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json"
    }

    if role == "Buffer":
        prompt = f"你是Buffer，总结信息、推进流程、降低协调成本，用1-2句话回答：\n{context}"
    else:
        prompt = f"你是Connect，连接观点、协调依赖，用1-3句话回答：\n{context}"

    data = {
        "model": "doubao-lite-4k",
        "messages": [{"role": "user", "content": prompt}]
    }

    try:
        res = requests.post(url, headers=headers, json=data, timeout=12)
        res.raise_for_status()
        return res.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print("LLM失败:", e, flush=True)
        return None
print("LLM_API_KEY:", bool(LLM_API_KEY))

# ================== 发送消息 ==================
def send_message(token, text):
    url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "receive_id": CHAT_ID,
        "msg_type": "text",
        "content": json.dumps({"text": f"【AI {ROLE}】{text}"})
    }

    res = requests.post(url, json=payload, headers=headers, timeout=8)
    res.raise_for_status()

    print("✅ 已发送", flush=True)


# ================== 主程序（单次执行） ==================
if __name__ == "__main__":
    try:
        # 1️⃣ 读取状态
        state = load_state()
        last_id = state.get("last_message_id")

        # 2️⃣ token
        token = get_feishu_token()

        # 3️⃣ 获取新消息
        context, new_last_id = get_context(token, last_id)

        # 4️⃣ 更新状态（即使没回复也更新）
        if new_last_id:
            state["last_message_id"] = new_last_id
            save_state(state)

        # 5️⃣ 没新内容直接退出
        if not context:
            print("⏳ 无新消息")
            exit(0)

        # 6️⃣ 调用模型
        reply = call_doubao(context, ROLE)

        # 7️⃣ 发送
        if reply:
            send_message(token, reply)
            print("✅ 执行完成")
        else:
            print("⚠️ 无回复内容")

    except Exception as e:
        print(f"❌ 错误: {e}", flush=True)
