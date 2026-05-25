import os
import requests
import json

# 读取配置
APP_ID = os.getenv("FEISHU_APP_ID")
APP_SECRET = os.getenv("FEISHU_APP_SECRET")
CHAT_ID = os.getenv("FEISHU_CHAT_ID")
VOLC_AK = os.getenv("VOLC_AK")
VOLC_SK = os.getenv("VOLC_SK")
ROLE = os.getenv("AI_ROLE", "Buffer")

print("=== 配置信息检查 ===")
print(f"APP_ID: {APP_ID[:4]}...")
print(f"CHAT_ID: {CHAT_ID}")
print(f"AI_ROLE: {ROLE}")
print("====================")

# 1. 获取飞书token
def get_feishu_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    data = {"app_id": APP_ID, "app_secret": APP_SECRET}
    res = requests.post(url, json=data)
    return res.json()["tenant_access_token"]

# 2. 读取最近20条群消息（已修复解析）
def get_context(token):
    url = "https://open.feishu.cn/open-apis/im/v1/messages"
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "container_id": CHAT_ID,
        "container_id_type": "chat",
        "page_size": 20
    }
    res = requests.get(url, headers=headers, params=params)
    resp_data = res.json()
    items = resp_data["data"].get("items", [])
    texts = []
    
    for item in items:
        try:
            content = item["body"]["content"]
            if isinstance(content, dict):
                texts.append(content.get("text", ""))
            else:
                texts.append(json.loads(content)["text"])
        except:
            pass
    
    return "\n".join(reversed(texts))

# 3. 调用豆包API（修复火山引擎接口！）
def call_doubao(ak, sk, context, role):
    print("\n正在调用豆包API...")
    url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
    headers = {
        "Authorization": f"Bearer {ak}:{sk}",
        "Content-Type": "application/json"
    }

    if role == "Buffer":
        prompt = f"""你是团队AI协作者，角色：Buffer。
任务：石墨烯护肤品开发/危机处理。
你的作用：总结信息、推进流程、降低协调成本。
只说1-2句话，简洁。

最近对话：
{context}
"""
    else:
        prompt = f"""你是团队AI协作者，角色：Connect。
任务：石墨烯护肤品开发/危机处理。
你的作用：连接观点、促进整合、加强协作。
只说1-3句话。

最近对话：
{context}
"""

    data = {
        "model": "doubao-lite-4k",
        "messages": [{"role": "user", "content": prompt}]
    }

    response = requests.post(url, headers=headers, json=data)
    reply = response.json()["choices"][0]["message"]["content"].strip()
    print(f"✅ 豆包生成：{reply}")
    return reply

# 4. 发送到飞书群
def send_message(token, text):
    url = "https://open.feishu.cn/open-apis/im/v1/messages"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "receive_id": CHAT_ID,
        "content": json.dumps({"text": text}),
        "msg_type": "text"
    }
    requests.post(url, json=payload, headers=headers)
    print("✅ 消息已发送到飞书群！")

# 主流程
if __name__ == "__main__":
    tk = get_feishu_token()
    ctx = get_context(tk)
    reply = call_doubao(VOLC_AK, VOLC_SK, ctx, ROLE)
    send_message(tk, reply)
    print("\n🎉 全部执行成功！机器人已发言！")
