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
print(f"APP_SECRET: {APP_SECRET[:4]}...")
print(f"CHAT_ID: {CHAT_ID}")
print(f"AI_ROLE: {ROLE}")
print("====================")

# 1. 获取飞书token
def get_feishu_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    data = {"app_id": APP_ID, "app_secret": APP_SECRET}
    print("\n正在获取飞书Token...")
    res = requests.post(url, json=data)
    print(f"Token API 响应码: {res.status_code}")
    if res.status_code != 200:
        raise Exception("获取Token失败")
    token = res.json().get("tenant_access_token")
    if not token:
        raise Exception("Token为空")
    print("Token获取成功！")
    return token

# 2. 读取最近20条群消息（已修复飞书API接口）
def get_context(token):
    url = f"https://open.feishu.cn/open-apis/im/v1/messages?page_size=20&receive_id={CHAT_ID}"
    headers = {"Authorization": f"Bearer {token}"}
    print(f"\n正在获取群消息...")
    res = requests.get(url, headers=headers)
    print(f"消息API响应码: {res.status_code}")
    
    if res.status_code != 200:
        raise Exception("获取群消息失败")
    
    resp_data = res.json()
    if "data" not in resp_data:
        raise Exception(f"飞书返回无data字段")
    
    items = resp_data["data"].get("items", [])
    texts = []
    for item in items:
        try:
            texts.append(json.loads(item["body"])["content"])
        except:
            pass
    return "\n".join(reversed(texts))

# 3. 调用豆包API
def call_doubao(ak, sk, context, role):
    print("\n正在调用豆包API...")
    token_url = "https://open.volcengineapi.com/api/v2/getAccessToken"
    res = requests.post(token_url, json={"ak": ak, "sk": sk})
    access_token = res.json().get("access_token")
    
    if role == "Buffer":
        prompt = f"""你是团队AI协作者，角色：Buffer。
任务：石墨烯护肤品开发 / 危机处理。
你的作用：总结信息、推进流程、降低协调成本。
只说1-2句话，简洁，不引发新讨论。

最近对话：
{context}
"""
    else:
        prompt = f"""你是团队AI协作者，角色：Connect。
任务：石墨烯护肤品开发 / 危机处理。
你的作用：连接观点、指出关联、促进整合。
只说1-3句话，促进协作。

最近对话：
{context}
"""

    chat_url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "doubao-lite-4k",
        "messages": [{"role": "user", "content": prompt}]
    }
    res = requests.post(chat_url, headers=headers, json=data)
    reply = res.json()["choices"][0]["message"]["content"].strip()
    print(f"豆包生成：{reply}")
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
    res = requests.post(url, json=payload, headers=headers)
    print("发送到飞书成功！")

# 主流程
if __name__ == "__main__":
    try:
        tk = get_feishu_token()
        ctx = get_context(tk)
        reply = call_doubao(VOLC_AK, VOLC_SK, ctx, ROLE)
        send_message(tk, reply)
        print("\n✅ 全部执行成功！")
    except Exception as e:
        print(f"\n❌ 出错: {e}")
        raise
