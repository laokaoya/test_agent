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

# 数据文件路径
CSV_FILE = os.path.join("data", "test_results.csv")
JSON_FILE = os.path.join("data", "test_results.json")
file_lock = threading.Lock()

def save_to_json(test_data):
    """保存测试结果到JSON文件（完整数据）"""
    try:
        with file_lock:
            # 读取现有JSON数据
            if os.path.isfile(JSON_FILE):
                with open(JSON_FILE, 'r', encoding='utf-8') as f:
                    try:
                        all_data = json.load(f)
                    except json.JSONDecodeError:
                        all_data = []
            else:
                all_data = []
            
            # 生成唯一测试ID
            timestamp_str = test_data.get('timestamp', datetime.now().strftime('%Y%m%d%H%M%S'))
            test_id = f"{timestamp_str.replace('-', '').replace(':', '').replace(' ', '_')}_{test_data.get('child_name', 'unknown')}"
            
            # 解析日期
            try:
                test_datetime = datetime.strptime(test_data.get('timestamp', ''), '%Y-%m-%d %H:%M:%S')
                test_date = test_datetime.strftime('%Y-%m-%d')
            except:
                test_date = datetime.now().strftime('%Y-%m-%d')
            
            # 提取角色类型
            child_type = ''
            traits = test_data.get('child_traits', '')
            if '害羞' in traits:
                child_type = '害羞型'
            elif '话多' in traits:
                child_type = '话多型'
            elif '好奇' in traits:
                child_type = '好奇型'
            elif '自信' in traits:
                child_type = '自信型'
            elif '抗拒' in traits:
                child_type = '抗拒型'
            
            # 计算统计数据
            conversations = test_data.get('conversations', [])
            actual_rounds = len(conversations)
            total_child_chars = sum(len(conv.get('user_message', '')) for conv in conversations)
            total_ai_chars = sum(len(conv.get('ai_response', '')) for conv in conversations)
            
            scores = test_data.get('scores', {})
            if scores:
                score_values = list(scores.values())
                avg_score = sum(score_values) / len(score_values)
                max_score = max(score_values)
                min_score = min(score_values)
                variance = sum((x - avg_score) ** 2 for x in score_values) / len(score_values)
                std_dev = variance ** 0.5
            else:
                avg_score = max_score = min_score = std_dev = 0
            
            # 构建完整记录
            record = {
                'test_id': test_id,
                'timestamp': test_data.get('timestamp', ''),
                'test_date': test_date,
                'child': {
                    'name': test_data.get('child_name', ''),
                    'age': test_data.get('child_age', ''),
                    'type': child_type,
                    'traits': test_data.get('child_traits', ''),
                    'opening': test_data.get('opening', '')
                },
                'conversations': conversations,
                'rounds': actual_rounds,
                'scores': {
                    'individual': scores,
                    'average': round(avg_score, 2),
                    'max': max_score,
                    'min': min_score,
                    'std_dev': round(std_dev, 2),
                    'criteria_used': list(scores.keys())
                },
                'evaluation': {
                    'reason': test_data.get('reason', ''),
                    'lessons': test_data.get('lessons', ''),
                    'character_review': test_data.get('character_review', ''),
                    'experience_score': test_data.get('experience_score', 50)
                },
                'statistics': {
                    'total_chars_child': total_child_chars,
                    'total_chars_ai': total_ai_chars,
                    'avg_chars_child': round(total_child_chars / actual_rounds, 1) if actual_rounds > 0 else 0,
                    'avg_chars_ai': round(total_ai_chars / actual_rounds, 1) if actual_rounds > 0 else 0
                }
            }
            
            # 添加到列表
            all_data.append(record)
            
            # 保存JSON文件
            with open(JSON_FILE, 'w', encoding='utf-8') as f:
                json.dump(all_data, f, ensure_ascii=False, indent=2)
            
        return True
    except Exception as e:
        print(f"保存JSON失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def save_to_csv(test_data):
    """保存测试结果到CSV文件（简化版，评分用JSON）"""
    try:
        with file_lock:
            file_exists = os.path.isfile(CSV_FILE)
            
            # 固定最多支持10轮对话的CSV结构
            MAX_CSV_ROUNDS = 10
            
            with open(CSV_FILE, 'a', newline='', encoding='utf-8-sig') as f:
                # ========== 简化的列名设计（固定列）==========
                # 1. 基础信息
                fieldnames = [
                    '测试ID',           # 唯一标识符
                    '测试时间',         # 时间戳
                    '测试日期',         # 日期
                    '角色名称',         # 角色名
                    '角色类型',         # 害羞型/话多型等
                    '角色年龄',         # 年龄
                    '对话轮数',         # 实际轮数
                ]
                
                # 2. 对话内容（使用JSON字符串存储）
                fieldnames.append('对话记录_JSON')
                
                # 3. 评分数据（使用JSON字符串，避免动态列）
                fieldnames.extend([
                    '评分详情_JSON',      # 各项评分（JSON格式）
                    '评分_平均分',        # 平均分
                    '评分_最高分',        # 最高分
                    '评分_最低分',        # 最低分
                    '评分_标准差',        # 标准差
                    '使用的评分标准',     # 标准列表
                    '角色体验评分',       # 角色给出的0-100分体验评分
                ])
                
                # 4. 对话统计
                fieldnames.extend([
                    '总字数_孩子',
                    '总字数_AI',
                    '平均字数_孩子',
                    '平均字数_AI',
                ])
                
                # 5. 评价内容
                fieldnames.extend([
                    '评分理由_总体',
                    '经验教训',
                    '角色自述',
                ])
                
                # 6. 元数据
                fieldnames.extend([
                    '角色完整设定',
                    '开场白',
                ])
                
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                
                if not file_exists:
                    writer.writeheader()
                
                conversations = test_data.get('conversations', [])
                actual_rounds = len(conversations)
                
                # 生成唯一测试ID（时间戳+角色名）
                timestamp_str = test_data.get('timestamp', datetime.now().strftime('%Y%m%d%H%M%S'))
                test_id = f"{timestamp_str.replace('-', '').replace(':', '').replace(' ', '_')}_{test_data.get('child_name', 'unknown')}"
                
                # 解析日期
                try:
                    test_datetime = datetime.strptime(test_data.get('timestamp', ''), '%Y-%m-%d %H:%M:%S')
                    test_date = test_datetime.strftime('%Y-%m-%d')
                except:
                    test_date = datetime.now().strftime('%Y-%m-%d')
                
                # 提取角色类型（从性格特点中尝试提取）
                child_type = ''
                traits = test_data.get('child_traits', '')
                # 尝试从Markdown格式中提取类型
                if '害羞' in traits:
                    child_type = '害羞型'
                elif '话多' in traits:
                    child_type = '话多型'
                elif '好奇' in traits:
                    child_type = '好奇型'
                elif '自信' in traits:
                    child_type = '自信型'
                elif '抗拒' in traits:
                    child_type = '抗拒型'
                
                # 基础信息
                row = {
                    '测试ID': test_id,
                    '测试时间': test_data.get('timestamp', ''),
                    '测试日期': test_date,
                    '角色名称': test_data.get('child_name', ''),
                    '角色类型': child_type,
                    '角色年龄': test_data.get('child_age', ''),
                    '对话轮数': actual_rounds,
                }
                
                # 对话内容和字数统计（存储为JSON）
                total_child_chars = 0
                total_ai_chars = 0
                
                conversation_data = []
                for i, conv in enumerate(conversations, 1):
                    child_msg = conv.get('user_message', '')
                    ai_msg = conv.get('ai_response', '')
                    
                    child_chars = len(child_msg)
                    ai_chars = len(ai_msg)
                    
                    total_child_chars += child_chars
                    total_ai_chars += ai_chars
                    
                    conversation_data.append({
                        'round': i,
                        'child_message': child_msg,
                        'ai_response': ai_msg,
                        'child_chars': child_chars,
                        'ai_chars': ai_chars
                    })
                
                row['对话记录_JSON'] = json.dumps(conversation_data, ensure_ascii=False)
                
                # 评分数据（使用JSON字符串）
                scores = test_data.get('scores', {})
                criteria_names = list(scores.keys())
                row['评分详情_JSON'] = json.dumps(scores, ensure_ascii=False)
                
                # 统计指标
                if scores:
                    score_values = list(scores.values())
                    avg_score = sum(score_values) / len(score_values)
                    max_score = max(score_values)
                    min_score = min(score_values)
                    
                    # 计算标准差
                    variance = sum((x - avg_score) ** 2 for x in score_values) / len(score_values)
                    std_dev = variance ** 0.5
                    
                    row['评分_平均分'] = f"{avg_score:.2f}"
                    row['评分_最高分'] = max_score
                    row['评分_最低分'] = min_score
                    row['评分_标准差'] = f"{std_dev:.2f}"
                else:
                    row['评分_平均分'] = ''
                    row['评分_最高分'] = ''
                    row['评分_最低分'] = ''
                    row['评分_标准差'] = ''
                
                row['使用的评分标准'] = ', '.join(criteria_names)
                row['角色体验评分'] = test_data.get('experience_score', '')
                
                # 对话统计
                row['总字数_孩子'] = total_child_chars
                row['总字数_AI'] = total_ai_chars
                row['平均字数_孩子'] = f"{total_child_chars / actual_rounds:.1f}" if actual_rounds > 0 else '0'
                row['平均字数_AI'] = f"{total_ai_chars / actual_rounds:.1f}" if actual_rounds > 0 else '0'
                
                # 评价内容
                row['评分理由_总体'] = test_data.get('reason', '')
                row['经验教训'] = test_data.get('lessons', '')
                row['角色自述'] = test_data.get('character_review', '')
                
                # 元数据
                row['角色完整设定'] = test_data.get('child_traits', '')
                row['开场白'] = test_data.get('opening', '')
                
                writer.writerow(row)
                
        return True
    except Exception as e:
        print(f"保存CSV失败: {e}")
        import traceback
        traceback.print_exc()
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
        # 构建新的三级指标评分标准文本
        criteria_text = ""
        all_criteria_keys = []
        
        for main_key, main_criteria in criteria.items():
            if isinstance(main_criteria, dict) and 'sub_criteria' in main_criteria:
                # 新的一级指标结构
                criteria_text += f"【{main_criteria.get('name', main_key)}】\n{main_criteria.get('description', '')}\n\n"
                
                for sub_key, sub_criteria in main_criteria.get('sub_criteria', {}).items():
                    criteria_text += f"  - {sub_criteria.get('name', sub_key)}：{sub_criteria.get('prompt', '')}\n\n"
                    all_criteria_keys.append(f"{main_key}.{sub_key}")
            else:
                # 兼容旧的平级结构
                criteria_text += f"【{main_key}】\n{main_criteria}\n\n"
                all_criteria_keys.append(main_key)
        
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
    {', '.join([f'"{key}": 5' for key in all_criteria_keys])}
  }},
  "score_details": {{
    {', '.join([f'"{key}": "【严格评分】从孩子视角看，AI在这方面的问题是...（必须引用具体对话，如\\"第X轮AI说...这让孩子可能感到...\\")（挑刺心态，找问题）"' for key in all_criteria_keys])}
  }},
  "reason": "【严苛总评】从孩子的角度看，AI的主要问题是...（必须具体，引用对话，不留情面地指出不足）",
  "lessons": "【改进建议】分条列出：\\n1. ❌ 主要问题：（最严重的问题是什么，引用对话）\\n2. ⚠️ 次要问题：（还有哪些问题，具体说明）\\n3. 💡 改进方向：（如果重做，应该如何改进，给出3-5条具体建议）",
  "character_review": "【角色自述】用孩子的第一人称口吻，让孩子自己说说这次对话的感受（必须完全符合角色性格、年龄、说话方式）",
  "experience_score": 介于1-100的一个数字
}}

【最终提醒】
1. 你的评分必须让人觉得"这个评价者很严格"
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
7. experience_score（体验评分）：0-100分，站在孩子的角度评价这次对话的整体体验，1分1档，不要只给几个固定的分数
   - 90-100分：超级开心，非常想继续聊
   - 70-89分：挺好的，愿意继续聊
   - 50-69分：还行吧，有点意思但不太激动
   - 30-49分：有点无聊，不太想继续
   - 0-29分：很不喜欢，不想再聊了
   - 要基于孩子的真实感受打分，不要因为AI"做了什么"就给高分
8. 只输出JSON，不要```json```包裹"""

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
            default_scores = {key: 5 for key in all_criteria_keys}
            default_details = {key: "评分解析失败，无法提供详细理由" for key in all_criteria_keys}
            return {
                "scores": default_scores,
                "score_details": default_details,
                "reason": "Gemini返回格式无法解析，使用默认评分5分",
                "lessons": "无法生成经验教训",
                "character_review": "（角色自述生成失败）",
                "experience_score": 50
            }
    except Exception as e:
        print(f"❌ Gemini评分异常: {e}")
        default_scores = {key: 5 for key in all_criteria_keys}
        default_details = {key: "评分异常，无法提供详细理由" for key in all_criteria_keys}
        return {
            "scores": default_scores,
            "score_details": default_details,
            "reason": f"评分失败: {str(e)}",
            "lessons": "评分异常，无法生成经验教训",
            "character_review": "（角色自述生成失败）",
            "experience_score": 50
        }


@app.route('/')
def index():
    return render_template('index.html', max_rounds=MAX_ROUNDS)

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/preset-children', methods=['GET'])
def get_preset_children():
    """返回内置角色配置"""
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(base_dir, 'config', 'preset_children.json')
        
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
        json_path = os.path.join(base_dir, 'config', 'preset_criteria.json')
        
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
        "experience_score": eval_result.get("experience_score", 50),
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })

@app.route('/api/save-result', methods=['POST'])
def save_result():
    """保存测试结果到JSON和CSV"""
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
        'character_review': data.get('character_review', ''),
        'experience_score': data.get('experience_score', 50)
    }
    
    # 同时保存到JSON和CSV
    json_success = save_to_json(test_data)
    csv_success = save_to_csv(test_data)
    
    if json_success and csv_success:
                return jsonify({
            "success": True,
            "message": "测试结果已保存到JSON和CSV"
        })
    elif json_success:
            return jsonify({
            "success": True,
            "message": "测试结果已保存到JSON（CSV保存失败）"
        })
    elif csv_success:
            return jsonify({
            "success": True,
            "message": "测试结果已保存到CSV（JSON保存失败）"
        })
    else:
            return jsonify({
                "success": False,
            "message": "保存失败"
        }), 500

# ========== 数据可视化仪表盘 API ==========

@app.route('/api/dashboard/summary', methods=['GET'])
def get_dashboard_summary():
    """获取仪表盘概览数据"""
    try:
        # 读取JSON数据
        if not os.path.isfile(JSON_FILE):
            return jsonify({
                "success": True,
                "data": {
                    "total_tests": 0,
                    "today_tests": 0,
                    "total_pass_rate": 0,
                    "avg_score": 0,
                    "avg_experience_score": 0
                }
            })
        
        with open(JSON_FILE, 'r', encoding='utf-8') as f:
            all_data = json.load(f)
        
        if not all_data:
            return jsonify({
                "success": True,
                "data": {
                    "total_tests": 0,
                    "today_tests": 0,
                    "total_pass_rate": 0,
                    "avg_score": 0,
                    "avg_experience_score": 0
                }
            })
        
        # 统计数据
        total_tests = len(all_data)
        
        # 今日测试数
        today = datetime.now().strftime('%Y-%m-%d')
        today_tests = sum(1 for test in all_data if test.get('test_date', '') == today)
        
        # 平均分和通过率
        avg_scores = [test.get('scores', {}).get('average', 0) for test in all_data]
        avg_score = sum(avg_scores) / len(avg_scores) if avg_scores else 0
        
        # 通过率（≥7.0算通过）
        pass_count = sum(1 for score in avg_scores if score >= 7.0)
        total_pass_rate = (pass_count / len(avg_scores) * 100) if avg_scores else 0
        
        # 平均体验评分
        exp_scores = [test.get('evaluation', {}).get('experience_score', 0) for test in all_data]
        avg_experience_score = sum(exp_scores) / len(exp_scores) if exp_scores else 0
        
        return jsonify({
            "success": True,
            "data": {
                "total_tests": total_tests,
                "today_tests": today_tests,
                "total_pass_rate": round(total_pass_rate, 1),
                "avg_score": round(avg_score, 2),
                "avg_experience_score": round(avg_experience_score, 1)
            }
        })
    except Exception as e:
        print(f"获取概览数据失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/dashboard/role-stats', methods=['GET'])
def get_role_stats():
    """获取各角色统计数据"""
    try:
        if not os.path.isfile(JSON_FILE):
            return jsonify({"success": True, "data": []})
        
        with open(JSON_FILE, 'r', encoding='utf-8') as f:
            all_data = json.load(f)
        
        if not all_data:
            return jsonify({"success": True, "data": []})
        
        # 按角色类型统计
        role_stats = {}
        for test in all_data:
            role_type = test.get('child', {}).get('type', '未知')
            if role_type not in role_stats:
                role_stats[role_type] = {
                    'count': 0,
                    'scores': [],
                    'experience_scores': []
                }
            
            role_stats[role_type]['count'] += 1
            avg_score = test.get('scores', {}).get('average', 0)
            role_stats[role_type]['scores'].append(avg_score)
            
            exp_score = test.get('evaluation', {}).get('experience_score', 0)
            role_stats[role_type]['experience_scores'].append(exp_score)
        
        # 计算平均值
        result = []
        for role_type, stats in role_stats.items():
            avg_score = sum(stats['scores']) / len(stats['scores']) if stats['scores'] else 0
            avg_exp = sum(stats['experience_scores']) / len(stats['experience_scores']) if stats['experience_scores'] else 0
            pass_rate = sum(1 for s in stats['scores'] if s >= 7.0) / len(stats['scores']) * 100 if stats['scores'] else 0
            
            result.append({
                'role_type': role_type,
                'count': stats['count'],
                'avg_score': round(avg_score, 2),
                'avg_experience': round(avg_exp, 1),
                'pass_rate': round(pass_rate, 1)
            })
        
        return jsonify({"success": True, "data": result})
    except Exception as e:
        print(f"获取角色统计失败: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/dashboard/criteria-stats', methods=['GET'])
def get_criteria_stats():
    """获取各指标统计数据"""
    try:
        if not os.path.isfile(JSON_FILE):
            return jsonify({"success": True, "data": []})
        
        with open(JSON_FILE, 'r', encoding='utf-8') as f:
            all_data = json.load(f)
        
        if not all_data:
            return jsonify({"success": True, "data": []})
        
        # 统计各指标
        criteria_stats = {}
        for test in all_data:
            individual_scores = test.get('scores', {}).get('individual', {})
            for criteria, score in individual_scores.items():
                if criteria not in criteria_stats:
                    criteria_stats[criteria] = []
                criteria_stats[criteria].append(score)
        
        # 计算平均值
        result = []
        for criteria, scores in criteria_stats.items():
            avg_score = sum(scores) / len(scores) if scores else 0
            result.append({
                'criteria': criteria,
                'avg_score': round(avg_score, 2),
                'count': len(scores)
            })
        
        # 按平均分排序
        result.sort(key=lambda x: x['avg_score'], reverse=True)
        
        return jsonify({"success": True, "data": result})
    except Exception as e:
        print(f"获取指标统计失败: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/dashboard/trend', methods=['GET'])
def get_trend_data():
    """获取趋势数据"""
    try:
        if not os.path.isfile(JSON_FILE):
            return jsonify({"success": True, "data": []})
        
        with open(JSON_FILE, 'r', encoding='utf-8') as f:
            all_data = json.load(f)
        
        if not all_data:
            return jsonify({"success": True, "data": []})
        
        # 按日期统计
        daily_stats = {}
        for test in all_data:
            test_date = test.get('test_date', '')
            if not test_date:
                continue
            
            if test_date not in daily_stats:
                daily_stats[test_date] = {
                    'count': 0,
                    'scores': [],
                    'experience_scores': []
                }
            
            daily_stats[test_date]['count'] += 1
            avg_score = test.get('scores', {}).get('average', 0)
            daily_stats[test_date]['scores'].append(avg_score)
            
            exp_score = test.get('evaluation', {}).get('experience_score', 0)
            daily_stats[test_date]['experience_scores'].append(exp_score)
        
        # 计算每日平均值
        result = []
        for date, stats in sorted(daily_stats.items()):
            avg_score = sum(stats['scores']) / len(stats['scores']) if stats['scores'] else 0
            avg_exp = sum(stats['experience_scores']) / len(stats['experience_scores']) if stats['experience_scores'] else 0
            
            result.append({
                'date': date,
                'count': stats['count'],
                'avg_score': round(avg_score, 2),
                'avg_experience': round(avg_exp, 1)
            })
        
        return jsonify({"success": True, "data": result})
    except Exception as e:
        print(f"获取趋势数据失败: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/dashboard/recent-tests', methods=['GET'])
def get_recent_tests():
    """获取最近的测试记录"""
    try:
        limit = int(request.args.get('limit', 10))
        
        if not os.path.isfile(JSON_FILE):
            return jsonify({"success": True, "data": []})
        
        with open(JSON_FILE, 'r', encoding='utf-8') as f:
            all_data = json.load(f)
        
        if not all_data:
            return jsonify({"success": True, "data": []})
        
        # 按时间戳排序，取最近的
        sorted_data = sorted(all_data, key=lambda x: x.get('timestamp', ''), reverse=True)
        recent_tests = sorted_data[:limit]
        
        # 提取关键信息
        result = []
        for test in recent_tests:
            result.append({
                'test_id': test.get('test_id', ''),
                'timestamp': test.get('timestamp', ''),
                'child_name': test.get('child', {}).get('name', ''),
                'child_type': test.get('child', {}).get('type', ''),
                'avg_score': test.get('scores', {}).get('average', 0),
                'experience_score': test.get('evaluation', {}).get('experience_score', 0),
                'rounds': test.get('rounds', 0),
                'passed': test.get('scores', {}).get('average', 0) >= 7.0
            })
        
        return jsonify({"success": True, "data": result})
    except Exception as e:
        print(f"获取最近测试失败: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
