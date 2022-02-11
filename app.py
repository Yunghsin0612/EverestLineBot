# -*- coding: utf-8 -*-
from flask import Flask, request, abort

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import *
import re,json
import stability, usable_card,forecast, battery_abnormal

app = Flask(__name__)
data, yes_ratio, all_ratio = usable_card.battery_info()
stable = stability.stable()
link = forecast.gantt()
consumption = battery_abnormal.power()
cliff = battery_abnormal.cliff()
quake = battery_abnormal.qq()

# 必須放上自己的Channel Access Token
#line_bot_api = LineBotApi('QK9zAE3YahykRi73w72OZ9BF2pCqleOJx1ND5bQ0NIXjItgG3GDXgHjJ5MBiTvOc8OCmteXzVHWUZbZObF3DLUhoK5kor44Ryh4ikVGGlQs0js2ExJ8ZEFGFDjiJfSi2F0kA/Y5/TIqoM4/Kr3aZ7gdB04t89/1O/w1cDnyilFU=')
# 必須放上自己的Channel Secret
#handler = WebhookHandler('47662360ce3f0ab86cc6f0d78056cb14')
# 影片上說要放user id(和自己對話的user)
#line_bot_api.push_message('Uf4583cb14cc686b51574caaf81a79bf1', TextSendMessage(text='請開始你的表演'))  # 我的userid
# 必須放上自己的Channel Access Token
line_bot_api = LineBotApi('j/eSAbajgqwV9IdUCdP+g2TOSOPuAvel5KcR24Omp3wCDyZw5Y3J/cGUlf//6J5PVc+j3zoKBFCwVoQLAyOz6P79F9axxhmIQ1ThFMkks7oQfRZ8BaYyW6fZanwih/YkFaTjU4Dk04UlfcyqZ4mMrgdB04t89/1O/w1cDnyilFU=')
# 必須放上自己的Channel Secret
handler = WebhookHandler('22b075fa01cf948e69d1b9fb11d1395f')

# 監聽所有來自 /callback 的 Post Request
@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'


# 訊息傳遞區塊
##### 基本上程式編輯都在這個function #####
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    print(event)
    message = text = event.message.text
    if re.match('卡號.*', message):
        img_link = usable_card.find_card(re.split('卡號', message)[1])
        line_bot_api.reply_message(event.reply_token, ImageSendMessage(
            original_content_url=img_link, preview_image_url=img_link))
    elif re.match('低電量資訊', message):
        line_bot_api.reply_message(event.reply_token, TextSendMessage(data))
    elif re.match('穩定度', message):
        line_bot_api.reply_message(event.reply_token, TextSendMessage(stable))
    elif re.match('高耗電', message):
        line_bot_api.reply_message(event.reply_token, TextSendMessage(consumption))
    elif re.match('震盪', message):
        line_bot_api.reply_message(event.reply_token, TextSendMessage(quake))
    elif re.match('掉電', message):
        line_bot_api.reply_message(event.reply_token, TextSendMessage(cliff))
    elif re.match('昨日比例', message):
        line_bot_api.reply_message(event.reply_token, TextSendMessage(yes_ratio))
    elif re.match('整體比例', message):
        line_bot_api.reply_message(event.reply_token, TextSendMessage(all_ratio))
    elif re.match('預測', message):
        line_bot_api.reply_message(event.reply_token, ImageSendMessage(
            original_content_url=link, preview_image_url=link))
    elif message == '低電量':
        FlexMessage = json.load(open('low_battery.json', 'r', encoding='utf-8'))
        line_bot_api.reply_message(event.reply_token, FlexSendMessage('LowBattery', FlexMessage))
    elif message == '異常':
        FlexMessage = json.load(open('irregular.json', 'r', encoding='utf-8'))
        line_bot_api.reply_message(event.reply_token, FlexSendMessage('Stability', FlexMessage))
    elif message =='檢修計畫':
        FlexMessage = json.load(open('maintainance.json', 'r', encoding='utf-8'))
        line_bot_api.reply_message(event.reply_token, FlexSendMessage('Stability', FlexMessage))
    else:
        line_bot_api.reply_message(event.reply_token, TextSendMessage('請重新輸入'))

import os

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
