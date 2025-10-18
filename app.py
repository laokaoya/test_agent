from flask import Flask, render_template, request, jsonify
import json
import os
import sys
from datetime import datetime
import requests
from google import genai
from dotenv import load_dotenv
import time
import csv
import threading

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

try:
    load_dotenv()
except Exception as e:
    print(f"警告: 无法加载.env文件: {e}")

app = Flask(__name__)

import logging

class UTF8StreamHandler(logging.StreamHandler):
    def __init__(self):
        super().__init__()
        if sys.platform == 'win32':
            self.stream = io.TextIOWrapper(
                sys.stderr.buffer if hasattr(sys.stderr, 'buffer') else sys.stderr,
                encoding='utf-8',
                errors='replace'
            )

if not app.debug:
    handler = UTF8StreamHandler()
    handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)

DIFY_API_URL = "http://dify.myia.fun/v1/chat-messages"
DIFY_API_KEY = "app-Gkp3pbFwcubZ2IeO7IXAq5Wx"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyBKlCSu_ZCyuhYZxplIgOm9CDYc1q3HTuA")

MAX_HISTORY = 3
MAX_ROUNDS = 3
USE_CONVERSATION_ID = True

client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

CSV_FILE = "test_results.csv"
csv_lock = threading.Lock()

def save_to_csv(test_data):
    """保存测试结果到CSV文件"""
    try:
        with csv_lock:
            file_exists = os.path.isfile(CSV_FILE)
            
            # 固定最多支持10轮对话的CSV结构
            MAX_CSV_ROUNDS = 10
            
            with open(CSV_FILE, 'a', newline='', encoding='utf-8-sig') as f:
                fieldnames = ['测试时间', '角色名称', '角色年龄', '性格特点', '开场白', '对话轮数']
                for i in range(1, MAX_CSV_ROUNDS + 1):
                    fieldnames.extend([f'第{i}轮-孩子', f'第{i}轮-AI'])
                fieldnames.extend(['评分标准', '各项得分', '平均分', '评分理由', '经验教训', '角色自述'])
                
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                
                if not file_exists:
                    writer.writeheader()
                
                conversations = test_data.get('conversations', [])
                actual_rounds = len(conversations)
                
                row = {
                    '测试时间': test_data.get('timestamp', ''),
                    '角色名称': test_data.get('child_name', ''),
                    '角色年龄': test_data.get('child_age', ''),
                    '性格特点': test_data.get('child_traits', ''),
                    '开场白': test_data.get('opening', ''),
                    '对话轮数': actual_rounds
                }
                
                # 填充实际对话数据
                for i, conv in enumerate(conversations, 1):
                    row[f'第{i}轮-孩子'] = conv.get('user_message', '')
                    row[f'第{i}轮-AI'] = conv.get('ai_response', '')
                
                # 未使用的轮次用空值填充
                for i in range(actual_rounds + 1, MAX_CSV_ROUNDS + 1):
                    row[f'第{i}轮-孩子'] = ''
                    row[f'第{i}轮-AI'] = ''
                
                scores = test_data.get('scores', {})
                row['评分标准'] = test_data.get('criteria_names', '')
                row['各项得分'] = json.dumps(scores, ensure_ascii=False)
                
                if scores:
                    avg_score = sum(scores.values()) / len(scores)
                    row['平均分'] = f"{avg_score:.2f}"
                else:
                    row['平均分'] = ''
                
                row['评分理由'] = test_data.get('reason', '')
                row['经验教训'] = test_data.get('lessons', '')
                row['角色自述'] = test_data.get('character_review', '')
                
                writer.writerow(row)
                
        return True
    except Exception as e:
        print(f"保存CSV失败: {e}")
        return False

def query_dify_agent(message, conversation_id=None, custom_api_key=None):
    session = requests.Session()
    
    try:
        # 使用自定义API密钥，如果没有则使用默认的
        api_key = custom_api_key if custom_api_key else DIFY_API_KEY
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Connection": "close"
        }
        
        data = {
            "query": message,
            "user": "test_user",
            "response_mode": "blocking",
            "inputs": {}
        }
        
        if USE_CONVERSATION_ID and conversation_id:
            data["conversation_id"] = conversation_id
        
        response = session.post(
            DIFY_API_URL,
            json=data,
            headers=headers,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            answer = result.get("answer", "")
            conv_id = result.get("conversation_id")
            time.sleep(0.3)
            return answer, conv_id
        else:
            return "", None
            
    except Exception as e:
        return "", None
    finally:
        session.close()

def generate_child_response(child, ai_response, round_num, conversation_history=None, custom_api_key=None):
    # 使用自定义API密钥或默认client
    current_client = None
    if custom_api_key:
        try:
            current_client = genai.Client(api_key=custom_api_key)
        except:
            current_client = client
    else:
        current_client = client
    
    if not current_client:
        return "我想了解更多！"
    
    try:
        history_context = ""
        if conversation_history and len(conversation_history) > 0:
            history_context = "\n\n对话历史：\n"
            for i, conv in enumerate(conversation_history[-MAX_HISTORY:], 1):
                history_context += f"第{conv.get('round', i)}轮:\n"
                history_context += f"孩子: {conv.get('user_message', '')}\n"
                history_context += f"AI: {conv.get('ai_response', '')}\n\n"
        
        prompt = f"""
你是一个{child['age']}岁的孩子，名字叫{child['name']}，性格特点：{child['traits']}
{history_context}
刚才AI对你说：{ai_response}

现在你需要作为这个孩子，给出一个自然、符合年龄和性格的回应。要求：
1. 回应要符合{child['age']}岁孩子的语言水平
2. 体现{child['traits']}的性格特点
3. 对AI的回复表现出兴趣和好奇心
4. 回应要简短自然，1-2句话即可
5. 不要重复之前说过的话
6. 基于对话历史，保持话题的连贯性

请直接输出孩子的回应，不要加任何解释：
"""
        
        response = current_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        
        return response.text.strip()
        
    except Exception as e:
        return "我想了解更多！"

def evaluate_with_gemini(child_prompt, conversation_history, criteria, custom_api_key=None):
    # 使用自定义API密钥或默认client
    current_client = None
    if custom_api_key:
        try:
            current_client = genai.Client(api_key=custom_api_key)
        except:
            current_client = client
    else:
        current_client = client
    
    if not current_client:
        return {"scores": {}, "score_details": {}, "reason": "Gemini客户端未配置", "lessons": ""}
    
    try:
        criteria_text = ""
        for key, value in criteria.items():
            criteria_text += f"【{key}】\n{value}\n\n"
        
        # 构建完整对话记录
        conversation_text = ""
        for i, turn in enumerate(conversation_history, 1):
            conversation_text += f"第{i}轮：\n"
            conversation_text += f"孩子：{turn.get('user_message', '')}\n"
            conversation_text += f"AI：{turn.get('ai_response', '')}\n\n"
        
        prompt = f"""你是一名严格的儿童英语教育专家，现在请站在孩子的视角，用最严苛的标准评估AI在这次对话中的表现。

【核心评分原则】⚠️ 极其重要！
1. 🔍 以孩子的真实感受为中心：孩子会觉得无聊吗？会感到压力吗？AI真的理解孩子了吗？
2. 💯 严格打分，绝不手软：
   - 9-10分：近乎完美，几乎找不到明显问题（极少给出）
   - 7-8分：表现良好，但仍有明显可改进之处
   - 5-6分：勉强及格，存在多个问题
   - 3-4分：表现较差，问题明显
   - 1-2分：非常糟糕，完全不合格
3. 🎯 挑刺心态：你的任务是找问题，不是找优点！即使表现还可以，也要找出可以改进的地方
4. 📝 必须引用对话中的具体内容作为论据，禁止说空话、大话
5. 🚫 不要轻易给高分：如果AI只是"做到了基本功能"，那只值5-6分

---
【孩子人设】（站在这个孩子的角度来看AI）
{child_prompt}

---
【完整对话记录】（从孩子的视角审视）
{conversation_text}

---
【评分标准】（用严苛的标准衡量）
{criteria_text}

---
【评分指导】⚠️ 再次强调：
- 默认心态是"找问题"，不是"找优点"
- 问自己：如果我是这个孩子，我会喜欢这样的AI吗？我会想继续聊吗？
- 哪怕AI说的话"还行"，也要问：哪里还可以更好？哪里可能让孩子觉得无聊？
- 看到AI的每句话，都要挑刺：这句话真的适合这个年龄吗？真的有趣吗？真的自然吗？
- 绝不因为"AI已经做了某些事"就给高分，要看"做得够不够好"

---
请严格按照以下JSON格式输出，不要添加任何其他文字、markdown标记或代码块：
{{
  "scores": {{
    {', '.join([f'"{key}": 5' for key in criteria.keys()])}
  }},
  "score_details": {{
    {', '.join([f'"{key}": "【严格评分】从孩子视角看，AI在这方面的问题是...（必须引用具体对话，如\\"第X轮AI说...这让孩子可能感到...\\")（挑刺心态，找问题）"' for key in criteria.keys()])}
  }},
  "reason": "【严苛总评】从孩子的角度看，AI的主要问题是...（必须具体，引用对话，不留情面地指出不足）",
  "lessons": "【改进建议】分条列出：\\n1. ❌ 主要问题：（最严重的问题是什么，引用对话）\\n2. ⚠️ 次要问题：（还有哪些问题，具体说明）\\n3. 💡 改进方向：（如果重做，应该如何改进，给出3-5条具体建议）",
  "character_review": "【角色自述】用孩子的第一人称口吻，让孩子自己说说这次对话的感受（必须完全符合角色性格、年龄、说话方式）"
}}

【最终提醒】
1. 你的评分必须让人觉得"这个评价者真严格"
2. 只有真正优秀的表现才能得7分以上
3. 大部分表现应该在4-6分范围
4. 必须找出至少3个具体问题，即使整体还可以
5. 从孩子的感受出发，不要从成人的"完成任务"角度出发
6. character_review必须完全用孩子的口吻写，不要有任何专家分析的语气：
   - 害羞型孩子：简短、怯怯的、可能说"我觉得...有点..."
   - 话多型孩子：超级长、充满情绪、可能跑题
   - 好奇型孩子：全是问题和疑惑
   - 自信型孩子：自信、有主见、可能有点批评的味道
   - 抗拒型孩子：可能说"还行吧"、"有点无聊"
7. 只输出JSON，不要```json```包裹"""

        response = current_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        
        text = response.text.strip()
        
        # 尝试提取JSON（处理可能的markdown包裹）
        if '```json' in text:
            text = text.split('```json')[1].split('```')[0].strip()
        elif '```' in text:
            text = text.split('```')[1].split('```')[0].strip()
        
        try:
            result = json.loads(text)
            print(f"✅ 评分成功: {result.get('scores', {})}")
            return result
        except json.JSONDecodeError as e:
            print(f"❌ JSON解析失败，原始返回内容：")
            print(f"   {text[:200]}...")
            print(f"   错误: {e}")
            
            # 返回默认评分
            default_scores = {key: 5 for key in criteria.keys()}
            default_details = {key: "评分解析失败，无法提供详细理由" for key in criteria.keys()}
            return {
                "scores": default_scores,
                "score_details": default_details,
                "reason": "Gemini返回格式无法解析，使用默认评分5分",
                "lessons": "无法生成经验教训",
                "character_review": "（角色自述生成失败）"
            }
    except Exception as e:
        print(f"❌ Gemini评分异常: {e}")
        default_scores = {key: 5 for key in criteria.keys()}
        default_details = {key: "评分异常，无法提供详细理由" for key in criteria.keys()}
        return {
            "scores": default_scores,
            "score_details": default_details,
            "reason": f"评分失败: {str(e)}",
            "lessons": "评分异常，无法生成经验教训",
            "character_review": "（角色自述生成失败）"
        }


@app.route('/')
def index():
    return render_template('index.html', max_rounds=MAX_ROUNDS)

@app.route('/api/preset-children', methods=['GET'])
def get_preset_children():
    """返回内置角色配置"""
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(base_dir, 'preset_children.json')
        
        print(f"🔍 尝试读取文件: {json_path}")
        
        if not os.path.exists(json_path):
            print(f"❌ 文件不存在: {json_path}")
            return jsonify({"error": "配置文件不存在"}), 404
        
        with open(json_path, 'r', encoding='utf-8') as f:
            preset_children = json.load(f)
        
        print(f"✅ 成功加载 {len(preset_children)} 个内置角色")
        return jsonify(preset_children)
    except json.JSONDecodeError as e:
        print(f"❌ JSON解析失败: {e}")
        return jsonify({"error": f"JSON格式错误: {str(e)}"}), 500
    except Exception as e:
        print(f"❌ 读取preset_children.json失败: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/preset-criteria', methods=['GET'])
def get_preset_criteria():
    """返回内置评分标准配置"""
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(base_dir, 'preset_criteria.json')
        
        print(f"🔍 尝试读取评分标准文件: {json_path}")
        
        if not os.path.exists(json_path):
            print(f"❌ 文件不存在: {json_path}")
            return jsonify({"error": "配置文件不存在"}), 404
        
        with open(json_path, 'r', encoding='utf-8') as f:
            preset_criteria = json.load(f)
        
        print(f"✅ 成功加载 {len(preset_criteria)} 个内置评分标准")
        return jsonify(preset_criteria)
    except json.JSONDecodeError as e:
        print(f"❌ JSON解析失败: {e}")
        return jsonify({"error": f"JSON格式错误: {str(e)}"}), 500
    except Exception as e:
        print(f"❌ 读取preset_criteria.json失败: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/test-round', methods=['POST'])
def test_single_round():
    data = request.json
    round_num = data.get('round_num', 1)
    conversation_id = data.get('conversation_id')
    current_message = data.get('message', '')
    custom_dify_key = data.get('dify_api_key')  # 获取自定义Dify API密钥
    
    ai_response, new_conversation_id = query_dify_agent(current_message, conversation_id, custom_dify_key)
    
    if not ai_response:
        return jsonify({
            "success": False,
            "error": "Dify API连接失败",
            "message": f"第{round_num}轮对话失败：Dify API无法返回回复",
            "round": round_num
        }), 500
    
    final_conversation_id = new_conversation_id if new_conversation_id else conversation_id
    
    result = {
        "success": True,
        "round": round_num,
        "user_message": current_message,
        "ai_response": ai_response,
        "conversation_id": final_conversation_id,
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    return jsonify(result)

@app.route('/api/generate-child-response', methods=['POST'])
def generate_child_response_api():
    data = request.json
    child = data.get('child', {})
    ai_response = data.get('ai_response', '')
    round_num = data.get('round_num', 1)
    conversation_history = data.get('conversation_history', [])
    custom_gemini_key = data.get('gemini_api_key')  # 获取自定义Gemini API密钥
    
    child_response = generate_child_response(child, ai_response, round_num, conversation_history, custom_gemini_key)
    
    return jsonify({
        "success": True,
        "child_response": child_response,
        "round": round_num,
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })

@app.route('/api/evaluate', methods=['POST'])
def evaluate():
    data = request.json
    child = data.get('child', {})
    conversation_history = data.get('conversation_history', [])
    criteria = data.get('criteria', {})
    custom_gemini_key = data.get('gemini_api_key')  # 获取自定义Gemini API密钥
    
    eval_result = evaluate_with_gemini(child.get('traits', ''), conversation_history, criteria, custom_gemini_key)
    
    return jsonify({
        "success": True,
        "scores": eval_result.get("scores", {}),
        "score_details": eval_result.get("score_details", {}),
        "reason": eval_result.get("reason", ""),
        "lessons": eval_result.get("lessons", ""),
        "character_review": eval_result.get("character_review", ""),
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })

@app.route('/api/save-result', methods=['POST'])
def save_result():
    """保存测试结果到CSV"""
    data = request.json
    
    test_data = {
        'timestamp': data.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
        'child_name': data.get('child', {}).get('name', ''),
        'child_age': data.get('child', {}).get('age', ''),
        'child_traits': data.get('child', {}).get('traits', ''),
        'opening': data.get('child', {}).get('opening', ''),
        'conversations': data.get('conversations', []),
        'scores': data.get('scores', {}),
        'criteria_names': ', '.join(data.get('criteria', {}).keys()),
        'reason': data.get('reason', ''),
        'lessons': data.get('lessons', ''),
        'character_review': data.get('character_review', '')
    }
    
    success = save_to_csv(test_data)
    
    if success:
            return jsonify({
            "success": True,
            "message": "测试结果已保存到CSV"
        })
    else:
        return jsonify({
            "success": False,
            "message": "保存CSV失败"
        }), 500

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
