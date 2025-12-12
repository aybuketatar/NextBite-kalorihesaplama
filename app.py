from flask import Flask, render_template, request, session, redirect, url_for, jsonify
import google.generativeai as genai
import json
import os

app = Flask(__name__)

app.secret_key = 'cok_gizli_anahtar_nextbite'
my_key = os.environ.get("GOOGLE_API_KEY")
genai.configure(api_key=my_key)

active_model_name = 'gemini-1.5-flash'
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            active_model_name = m.name
            break
except:
    pass
model = genai.GenerativeModel(active_model_name)

def calculate_daily_needs(data):
    try:
        weight = float(data['weight'])
        height = float(data['height'])
        age = int(data['age'])
        gender = data['gender']
        activity = float(data['activity'])
        goal = data['goal']
    except:
        return 2000

    if gender == 'male':
        bmr = (10 * weight) + (6.25 * height) - (5 * age) + 5
    else:
        bmr = (10 * weight) + (6.25 * height) - (5 * age) - 161

    tdee = bmr * activity

    if goal == 'lose': return round(tdee - 500)
    elif goal == 'gain': return round(tdee + 500)
    else: return round(tdee)

@app.route('/', methods=['GET', 'POST'])
def index():
    if 'user_data' not in session:
        return render_template('index.html', show_login=True)

    user = session['user_data']
    total_calories = 0
    food_items = []
    error_message = None
    ai_advice = None

    if request.method == 'POST':
        user_inputs = request.form.getlist('food_input')
        full_list = [x for x in user_inputs if x.strip()]

        if full_list:
            food_text = ", ".join(full_list)
            prompt = f"""
            Sen uzman bir diyetisyensin. Hedef: {user['target_calories']} kcal.
            Amaç: {user['goal_tr']}. Yenenler: {food_text}.
            1. Kalorileri hesapla.
            2. Duruma göre KISA bir tavsiye ver.
            Cevap formatı (JSON):
            {{
                "foods": [{{"name": "...", "calories": 0, "protein": 0, "carbs": 0, "fat": 0}}],
                "advice": "Tavsiye metni"
            }}
            """
            try:
                response = model.generate_content(prompt)
                cleaned = response.text.replace('```json', '').replace('```', '').strip()
                data = json.loads(cleaned)
                food_items = data.get('foods', [])
                ai_advice = data.get('advice', "Afiyet olsun!")
                for food in food_items: total_calories += food['calories']
            except Exception as e:
                error_message = f"Hata: {e}"

    return render_template('index.html', show_login=False, user=user, items=food_items, total=round(total_calories), error=error_message, advice=ai_advice)

@app.route('/suggest_meal', methods=['POST'])
def suggest_meal():
    data = request.get_json()
    ingredients = data.get('ingredients')
    calories = data.get('calories')
    
    prompt = f"""
    Sen yaratıcı bir şefsin. Kullanıcının elindeki malzemeler: {ingredients}.
    Bu öğün için istediği kalori: {calories} kcal.
    
    Bu malzemeleri (veya evde bulunabilecek çok temel şeyleri) kullanarak YAPILABİLECEK EN MANTIKLI TEK BİR TARİF ver.
    Tarif kısa ve net olsun.
    
    Cevabı SADECE şu formatta ver (Başka bir şey yazma):
    **Tarif Adı:** [Buraya Adı]
    **Kalori:** [Tahmini Kalori]
    **Hazırlanışı:** [Kısa tarif]
    """
    
    try:
        response = model.generate_content(prompt)
        return jsonify({'result': response.text})
    except Exception as e:
        return jsonify({'result': "Üzgünüm, şu an bir tarif oluşturamadım."})

@app.route('/setup', methods=['POST'])
def setup():
    user_data = {
        'name': request.form.get('name'),
        'age': request.form.get('age'),
        'height': request.form.get('height'),
        'weight': request.form.get('weight'),
        'gender': request.form.get('gender'),
        'activity': request.form.get('activity'),
        'goal': request.form.get('goal')
    }
    daily_cal = calculate_daily_needs(user_data)
    user_data['target_calories'] = daily_cal
    goals_tr = {'lose': 'Kilo Vermek', 'maintain': 'Formu Korumak', 'gain': 'Kilo Almak'}
    user_data['goal_tr'] = goals_tr.get(user_data['goal'], 'Dengeli Beslenmek')
    session['user_data'] = user_data
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.pop('user_data', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
