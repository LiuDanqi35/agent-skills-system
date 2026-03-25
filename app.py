from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import time
import re

app = Flask(__name__)
CORS(app)

# ========== 在这里填你的 API Key ==========
API_KEY = "d3ab65d686824584a5bf2fd4328eac18.MK3XXO2nfmOS0e90"
# ========================================

BASE_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

# 内置技能提示词（云端没有本地文件，直接写在这里）
SKILL_CONTENT = """你是顶级前端开发专家。严格按照以下原则生成代码：
1. 配色：深色科技感背景 #0f172a，强调色 #3b82f6
2. 所有图标用 Font Awesome 6
3. 卡片圆角 1rem，hover 上浮效果
4. 响应式适配移动端
5. 只输出完整 HTML 代码，从 <!DOCTYPE> 开始"""

def call_api_with_retry(payload, headers, max_retries=2, timeout=120):
    for attempt in range(max_retries + 1):
        try:
            print(f"📡 调用智谱API (尝试 {attempt + 1}/{max_retries + 1})...")
            response = requests.post(BASE_URL, json=payload, headers=headers, timeout=timeout)
            if response.status_code == 200:
                return response.json(), None
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                print(f"⚠️ API返回错误: {error_msg}")
                if attempt < max_retries:
                    time.sleep(2)
                    continue
                return None, error_msg
        except requests.exceptions.Timeout:
            print(f"⏰ API请求超时 (尝试 {attempt + 1}/{max_retries + 1})")
            if attempt < max_retries:
                time.sleep(3)
                continue
            return None, "请求超时，请稍后重试"
        except Exception as e:
            print(f"❌ 请求异常: {str(e)}")
            if attempt < max_retries:
                time.sleep(2)
                continue
            return None, str(e)
    return None, "多次重试后仍然失败"

def clean_html_code(raw_code):
    if raw_code.strip().startswith('<!DOCTYPE') or raw_code.strip().startswith('<html'):
        return raw_code
    code_block_pattern = r'```(?:html)?\n([\s\S]*?)\n```'
    match = re.search(code_block_pattern, raw_code)
    if match:
        return match.group(1).strip()
    html_pattern = r'(<html[\s\S]*?</html>)'
    match = re.search(html_pattern, raw_code, re.IGNORECASE)
    if match:
        return match.group(1)
    return raw_code

def ensure_complete_html(html_code):
    html_code = html_code.strip()
    if html_code.startswith('<!DOCTYPE') or html_code.startswith('<html'):
        return html_code
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>生成的网页</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: 'Inter', system-ui, sans-serif;
            background: #0a0c10;
            color: #f3f4f6;
            min-height: 100vh;
        }}
    </style>
</head>
<body>
    {html_code}
</body>
</html>"""

@app.route('/api/generate', methods=['POST'])
def generate():
    data = request.get_json()
    prompt = data.get('prompt', '')
    
    if not prompt:
        return jsonify({'error': '请输入需求'}), 400
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "glm-4-flash",
        "messages": [
            {"role": "system", "content": SKILL_CONTENT},
            {"role": "user", "content": f"生成一个网页：{prompt}"}
        ],
        "temperature": 0.8,
        "max_tokens": 8192
    }
    
    try:
        print(f"📡 开始处理需求: {prompt[:100]}...")
        result, error = call_api_with_retry(payload, headers, max_retries=2, timeout=120)
        
        if error:
            print(f"❌ API调用失败: {error}")
            return jsonify({'error': error}), 500
        
        if "choices" in result and len(result["choices"]) > 0:
            generated_code = result["choices"][0]["message"]["content"]
            print(f"✅ API返回成功，长度: {len(generated_code)} 字符")
            clean_code = clean_html_code(generated_code)
            final_code = ensure_complete_html(clean_code)
            return jsonify({'htmlCode': final_code})
        else:
            error_msg = result.get("error", {}).get("message", "未知错误")
            return jsonify({'error': f'API错误: {error_msg}'}), 500
            
    except Exception as e:
        print(f"❌ 服务器异常: {str(e)}")
        return jsonify({'error': f'服务器错误: {str(e)}'}), 500

if __name__ == '__main__':
    print("🚀 启动后端服务...")
    app.run(host='0.0.0.0', port=5000)
