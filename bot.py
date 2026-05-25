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
    print(f"Token API 响应内容: {res.text}")
    if res.status_code != 200:
        raise Exception("获取Token失败")
    token = res.json().get("tenant_access_token")
    if not token:
        raise Exception("Token为空")
    print("Token获取成功！")
    return token

# 2. 读取最近20条群消息
def get_context(token):
    url = f"https://open.feishu.cn/open-apis/im/v1/messages?page_size=20&container_id={CHAT_ID}&container_id_type=chat_id"
    headers = {"Authorization": f"Bearer {token}"}
    print(f"\n正在获取群消息，请求URL: {url}")
    res = requests.get(url, headers=headers)
    print(f"消息API响应码: {res.status_code}")
    print(f"消息API响应内容: {res.text}")
    if res.status_code != 200:
        raise Exception("获取群消息失败")
    
    resp_data = res.json()
    if "data" not in resp_data:
        raise Exception(f"响应中没有data字段，完整响应: {resp_data}")
    
    items = resp_data["data"].get("items", [])
    texts = []
    for item in items:
        try:
            texts.append(json.loads(item["body"])["content"])
        except Exception as e:
            print(f"解析消息失败: {e}")
    return "\n".join(reversed(texts))

# 3. 调用豆包API（火山引擎版）
def call_doubao(ak, sk, context, role):
    print("\n正在调用豆包API...")
    if not ak or not sk:
        raise Exception("VOLC_AK 或 VOLC_SK 未配置")

    # 先获取token
    token_url = "https://open.volcengineapi.com/api/v2/getAccessToken"
    headers = {"Content-Type": "application/json"}
    data = {"ak": ak, "sk": sk}
    res = requests.post(token_url, headers=headers, json=data)
    print(f"豆包Token响应码: {res.status_code}")
    if res.status_code != 200:
        raise Exception(f"获取豆包Token失败: {res.text}")
    access_token = res.json().get("access_token")
    if not access_token:
        raise Exception("豆包Token为空")

    # 拼接prompt
    if role == "Buffer":
        prompt = f"""你是团队AI协作者，角色：Buffer。
任务：石墨烯护肤品开发 / 危机处理。
你的作用：降低协调成本、总结信息、推进流程、提醒下一步。
只说1-2句话，不引发深度讨论，不制造分歧。

最近对话：
{context}
"""
    else:
        prompt = f"""你是团队AI协作者，角色：Connect。
任务：石墨烯护肤品开发 / 危机处理。
你的作用：连接不同信息、指出差异、促进理解、整合观点。
只说1-3句话，不总结进度，不控制流程。

最近对话：
{context}
"""

    # 调用模型
    chat_url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "doubao-lite-4k",
        "messages": [{"role": "user", "content": prompt.strip()}]
    }
    res = requests.post(chat_url, headers=headers, json=data)
    print(f"豆包API响应码: {res.status_code}")
    if res.status_code != 200:
        raise Exception(f"调用豆包失败: {res.text}")
    reply = res.json()["choices"][0]["message"]["content"].strip()
    print(f"豆包回复: {reply}")
    return reply

# 4. 发送到飞书群
def send_message(token, text):
    print("\n正在发送消息到飞书群...")
    url = "https://open.feishu.cn/open-apis/im/v1/messages"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "receive_id": CHAT_ID,
        "content": json.dumps({"text": text}),
        "msg_type": "text",
        "container_id_type": "chat_id"
    }
    res = requests.post(url, headers=headers, json=payload)
    print(f"发送消息响应码: {res.status_code}")
    print(f"发送消息响应内容: {res.text}")
    if res.status_code != 200:
        raise Exception("发送消息失败")
    print("消息发送成功！")

# 主流程
if __name__ == "__main__":
    try:
        tk = get_feishu_token()
        ctx = get_context(tk)
        print(f"\n获取到的对话上下文: {ctx}")
        reply = call_doubao(VOLC_AK, VOLC_SK, ctx, ROLE)
        send_message(tk, reply)
        print(f"\n【{ROLE}】流程全部完成，发送成功！")
    except Exception as e:
        print(f"\n❌ 程序出错: {e}")
        raise
