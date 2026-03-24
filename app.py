from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import time
import re

app = Flask(__name__)
CORS(app)

# ========== 在这里填你的 API Key ==========
API_KEY = "d3ab65d686824584a5bf2fd4328eac18.MK3XXO2nfmOS0e90"  # 把 API Key 填在这里，例如 "d3ab65d686824584a5bf2fd4328eac18.MK3XXO2nfmOS0e90"
# ========================================

# 智谱 API 地址
BASE_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

# 读取 frontend-design 技能文件作为系统提示词
SKILL_PATH = os.path.expanduser("~/.claude/skills/frontend-design/SKILL.md")
try:
    with open(SKILL_PATH, 'r', encoding='utf-8') as f:
        SKILL_CONTENT = f.read()
    print(f"✅ 已加载技能文件: {SKILL_PATH}")
except Exception as e:
    print(f"⚠️ 技能文件加载失败: {e}")
    SKILL_CONTENT = "你是前端开发专家，生成高质量、美观的HTML/CSS代码。"

def call_api_with_retry(payload, headers, max_retries=2, timeout=120):
    """带重试机制的API调用"""
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
                    print(f"⏳ 等待 2 秒后重试...")
                    time.sleep(2)
                    continue
                return None, error_msg
        except requests.exceptions.Timeout:
            print(f"⏰ API请求超时 (尝试 {attempt + 1}/{max_retries + 1})")
            if attempt < max_retries:
                print(f"⏳ 等待 3 秒后重试...")
                time.sleep(3)
                continue
            return None, "请求超时，请稍后重试"
        except Exception as e:
            print(f"❌ 请求异常: {str(e)}")
            if attempt < max_retries:
                print(f"⏳ 等待 2 秒后重试...")
                time.sleep(2)
                continue
            return None, str(e)
    return None, "多次重试后仍然失败"

def clean_html_code(raw_code):
    """清理和提取HTML代码"""
    if raw_code.strip().startswith('<!DOCTYPE') or raw_code.strip().startswith('<html'):
        return raw_code
    
    # 提取 markdown 代码块中的 HTML
    code_block_pattern = r'```(?:html)?\n([\s\S]*?)\n```'
    match = re.search(code_block_pattern, raw_code)
    if match:
        return match.group(1).strip()
    
    # 提取 <html> 标签内的内容
    html_pattern = r'(<html[\s\S]*?</html>)'
    match = re.search(html_pattern, raw_code, re.IGNORECASE)
    if match:
        return match.group(1)
    
    return raw_code

def ensure_complete_html(html_code):
    """确保返回完整的HTML文档"""
    html_code = html_code.strip()
    
    # 如果已经是完整HTML，直接返回
    if html_code.startswith('<!DOCTYPE') or html_code.startswith('<html'):
        return html_code
    
    # 包装成完整HTML
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
            font-family: 'Inter', system-ui, -apple-system, sans-serif;
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
        "model": "glm-4-plus",  # 使用更强模型，设计效果更好
        "messages": [
            {"role": "system", "content": f"""你是顶级前端开发专家。严格按照以下原则生成代码：

{SKILL_CONTENT}

【强制规则 - 必须100%遵守】
1. 配色：使用现代深色主题（#0f172a 背景，#3b82f6 强调色），禁止紫色渐变
2. 图标：全部使用 Font Awesome 6，已在 head 中添加 CDN，用 <i class="fas fa-xxx"></i>
3. 图片：禁止使用 via.placeholder.com、picsum.photos 等任何外部图片URL，全部用图标或CSS代替
4. 字体：'Inter', system-ui, -apple-system
5. 圆角：卡片 1rem，按钮 0.5rem
6. 动画：卡片 hover 时上浮 + 阴影过渡
7. 响应式：移动端（max-width: 768px）卡片堆叠显示
8. 只输出完整的 HTML 代码，从 <!DOCTYPE html> 开始，不要任何解释文字

【参考样式】
- 导航栏：毛玻璃效果 backdrop-blur
- 卡片：背景 #1e293b，圆角，hover 上浮
- 按钮：渐变背景或纯色，圆润设计
- 整体布局：max-width 1200px 居中，padding 2rem 左右"""},
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
            print(f"✅ API返回成功，原始内容长度: {len(generated_code)} 字符")
            
            clean_code = clean_html_code(generated_code)
            print(f"✅ 清理后代码长度: {len(clean_code)} 字符")
            
            final_code = ensure_complete_html(clean_code)
            print(f"✅ 最终代码长度: {len(final_code)} 字符")
            
            return jsonify({'htmlCode': final_code})
        else:
            error_msg = result.get("error", {}).get("message", "未知错误")
            print(f"❌ API返回格式错误: {result}")
            return jsonify({'error': f'API错误: {error_msg}'}), 500
            
    except Exception as e:
        print(f"❌ 服务器异常: {str(e)}")
        return jsonify({'error': f'服务器错误: {str(e)}'}), 500

if __name__ == '__main__':
    print("🚀 启动后端服务...")
    print("🤖 使用模型: glm-4-plus")
    print("⏰ 超时时间: 120 秒，自动重试 3 次")
    app.run(debug=True, port=5000)