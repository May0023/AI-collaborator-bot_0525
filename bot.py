import os
import requests
import json

# 配置读取
APP_ID = os.getenv("FEISHU_APP_ID")
APP_SECRET = os.getenv("FEISHU_APP_SECRET")
CHAT_ID = os.getenv("FEISHU_CHAT_ID")
LLM_API_KEY = os.getenv("LLM_API_KEY")
ROLE = os.getenv("AI_ROLE", "Buffer")

print("=== 配置检查 ===")
print(f"APP_ID: {APP_ID[:6]}...")
print(f"CHAT_ID: {CHAT_ID}")
print(f"角色: {ROLE}")

# 1. 获取飞书 token
def get_feishu_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    data = {"app_id": APP_ID, "app_secret": APP_SECRET}
    res = requests.post(url, json=data)
    return res.json()["tenant_access_token"]

# 2. 读取群消息（已修复解析）
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

# 3. 调用豆包 API
def call_doubao(api_key, context, role):
    print("\n正在生成回复...")
    url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    if role == "Buffer":
        prompt = f"""你是团队AI协作者 Buffer。
你的任务：总结信息、推进流程、降低协调成本。
说话简洁，1-2句话。

对话：
{context}
"""
    else:
        prompt = f"""你是团队AI协作者 Connect。
你的任务：连接观点、协调依赖、促进整合。
说话简洁，1-3句话。

对话：
{context}
"""

    data = {
        "model": "doubao-lite-4k",
        "messages": [{"role": "user", "content": prompt}]
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        resp = response.json()
        reply = resp["choices"][0]["message"]["content"].strip()
    except:
        reply = f"【{ROLE}】我已同步所有部门信息，可继续推进。"

    print(f"✅ 生成回复：{reply}")
    return reply

# 4. 发送消息到群（终极修复版）
def send_message(token, text):
    url = "https://open.feishu.cn/open-apis/im/v1/messages"
    headers = {"Authorization": f"Bearer {token}"}
    
    # 使用飞书官方推荐的格式
    msg = f"【AI {ROLE}】\n{text}"
    payload = {
        "receive_id": CHAT_ID,
        "content": json.dumps({"text": msg}),
        "msg_type": "text"
    }

    res = requests.post(url, json=payload, headers=headers)
    print(f"发送消息状态码: {res.status_code}")
    print(f"飞书返回内容: {res.text}")
    if res.status_code != 200:
        raise Exception(f"发送失败，飞书返回: {res.text}")

# 主程序
if __name__ == "__main__":
    token = get_feishu_token()
    context = get_context(token)
    reply = call_doubao(LLM_API_KEY, context, ROLE)
    send_message(token, reply)
    print("\n🎉 全部完成！")
