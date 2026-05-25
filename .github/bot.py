import os
import requests
import json

# 读取配置
APP_ID = os.getenv("FEISHU_APP_ID")
APP_SECRET = os.getenv("FEISHU_APP_SECRET")
CHAT_ID = os.getenv("FEISHU_CHAT_ID")
API_KEY = os.getenv("LLM_API_KEY")
ROLE = os.getenv("AI_ROLE", "Buffer")

# 1. 获取飞书token
def get_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    res = requests.post(url, json={"app_id": APP_ID, "app_secret": APP_SECRET})
    return res.json()["tenant_access_token"]

# 2. 读取最近20条群消息
def get_context(token):
    url = f"https://open.feishu.cn/open-apis/im/v1/messages?page_size=20&container_id={CHAT_ID}"
    headers = {"Authorization": f"Bearer {token}"}
    res = requests.get(url, headers=headers)
    items = res.json()["data"]["items"]
    texts = []
    for item in items:
        try:
            texts.append(json.loads(item["body"])["content"])
        except:
            pass
    return "\n".join(reversed(texts))

# 3. 调用大模型API
def generate_reply(context):
    prompt = f"""
你是团队AI协作者，角色：{ROLE}
任务：石墨烯护肤品开发 / 危机处理

规则：
- Buffer：核心功能不是促进深度理解，而是降低直接协调成本，使不同主体在保留差异的情况下仍能高效协作，1-3句话
- Connect：通过知识转移/翻译/整合，帮助协作者显性化分歧、讨论差异并最终协调认知，1-3句话

对话内容：
{context}

直接输出你要说的话。
"""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": prompt.strip()}]
    }
    res = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data)
    return res.json()["choices"][0]["message"]["content"].strip()

# 4. 发送到飞书群
def send(token, text):
    url = "https://open.feishu.cn/open-apis/im/v1/messages"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "receive_id": CHAT_ID,
        "content": json.dumps({"text": text}),
        "msg_type": "text",
        "container_id_type": "chat_id"
    }
    requests.post(url, headers=headers, json=payload)

# 主流程
if __name__ == "__main__":
    tk = get_token()
    ctx = get_context(tk)
    reply = generate_reply(ctx)
    send(tk, reply)
    print("成功发送：", reply)
