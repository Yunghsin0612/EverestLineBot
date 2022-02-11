import pyodbc
from datetime import datetime
import time, os, pyimgur, shutil
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn import linear_model
from sklearn.model_selection import train_test_split

pyodbc.drivers()
conx = pyodbc.connect('DRIVER={SQL Server}; SERVER=172.19.3.224; Database=everest_tracking; UID=user1; PWD=Aa22817999@')
cursor = conx.cursor()

seq = []
for i in list(range(1, 32)):
    seq.append('SELECT CardID FROM dbo.pathtable' + '%02d' % i + ' WHERE Battery <= 20')

query = ' UNION '.join(seq)
cursor.execute(query)
# Import dataset
raw_data = cursor.fetchall()
low_ID = []

for i in raw_data:
    if i[0] not in low_ID:
        low_ID.append(i[0])

result = 'OR '.join(map(lambda i: 'CardID = ' + f" '{i}' ", low_ID))
seq = []
for i in list(range(1, 32)):
    seq.append('SELECT CardID,Battery,UDateTime FROM dbo.pathtable' + '%02d' % i + ' WHERE ' + result)

query = ' UNION '.join(seq)
cursor.execute(query)
raw_data = cursor.fetchall()
raw_low_b_data = sorted(raw_data, key=lambda x: datetime.strptime(x[2], "%Y/%m/%d %H:%M:%S"), reverse=True)

raw_id, raw_info = [], []
for i in raw_low_b_data:
    if i[0] not in raw_id:
        raw_id.append(i[0])
        raw_info.append(i)

low_b_data = list(map(lambda x: list(x), list(filter(lambda x: int(x[1]) <= 20, raw_info))))
raw_id = [i[0] for i in low_b_data]


# 查詢卡號
def search(num):
    result = sorted(map(lambda x: list(x), filter(lambda i: i[0] == num, raw_low_b_data)),
                    key=lambda d: datetime.strptime(d[2], "%Y/%m/%d %H:%M:%S"), reverse=False)
    for i in result:
        i[2] = int(time.mktime(time.strptime(i[2], "%Y/%m/%d %H:%M:%S")))
    return result


def linear(data):
    id_left_accuracy = []

    for i in data:
        record = search(i)
        # 建立dataframe
        col = ['CardID', 'Battery', 'UDateTime']
        df = pd.DataFrame(record, columns=col)
        df.set_index('UDateTime', inplace=True)
        # 線性回歸
        X = df.index.values.reshape(-1, 1)
        y = df['Battery']
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=0)
        regr = linear_model.LinearRegression()
        regr.fit(X_train, y_train)
        ##計算回歸準確度
        score = float(regr.score(X_test, y_test)) * 100
        ## 計算出截距值與係數值
        w_0 = float(regr.intercept_)
        w_1 = float(regr.coef_)
        ## 拿訓練好的迴歸模型預測測試集資料的目標值(依變數)
        try:
            time_stamp = (0 - w_0) / w_1  # 設定timeStamp
            struct_time = time.localtime(time_stamp)  # 轉成時間元組
            left_time = time.strftime("%Y-%m-%d %H:%M:%S", struct_time)  # 轉成字串
        except ZeroDivisionError:
            left_time = 'error '
            score = 0
        # 儲存資料
        id_left_accuracy.append([i, left_time, score])

    return id_left_accuracy


final = linear(raw_id)

# 建立dataframe
col = ['CardID', '預測沒電日期', '預測準確度 %']
final_df = pd.DataFrame(final, columns=col)
final_df.set_index('CardID', inplace=True)
final_df['最後一筆電量資訊'] = list(map(lambda x: str(x[1]), low_b_data))
final_df['最後一筆日期資訊'] = list(map(lambda x: str(x[2]), low_b_data))
final_df['預測準確度 %'] = np.round(final_df['預測準確度 %'], 2)
error, before, after = 0, 0, 0
status = []
for i in final:
    if i[1] < str(datetime.today()):
        before += 1
        status.append('before')
    elif i[1] == 'error ':
        error += 1
        status.append('error')
    else:
        after += 1
        status.append('after')
final_df['Status'] = status
final_df = final_df.sort_values(by=['預測沒電日期'])

import plotly.express as px
import plotly.io as pio
pio.renderers.default='svg'

def gantt():

    d = final_df.copy()
    error_index = d[d['預測沒電日期'] == 'error '].index
    dd = d.drop(error_index)
    dd.drop(columns=['預測準確度 %', '最後一筆電量資訊'], inplace=True)
    dd = dd.reset_index()
    dd.columns = ['Task', 'Finish', 'Start', 'Status']
    dd['Finish'] = [datetime.strptime(i, "%Y-%m-%d %H:%M:%S").strftime('%Y-%m-%d') for i in dd['Finish']]
    dd['Start'] = [datetime.strptime(i, "%Y/%m/%d %H:%M:%S").strftime('%Y-%m-%d') for i in dd['Start']]
    fig = px.timeline(dd, x_start="Start", x_end="Finish", y="Task", color='Status', title='Forecast')
    fig.update_yaxes(autorange="reversed")

    path = os.getcwd()
    if not os.path.exists(path + '/forecast'):
        os.makedirs(path + '/forecast')

    fig.write_image('forecast/forecast.png')
    client_id = '338e9d3319c68de'
    PATH = 'forecast/forecast.png'
    title = "Uploaded with PyImgur"
    im = pyimgur.Imgur(client_id)
    uploaded_image = im.upload_image(PATH, title=title)

    return uploaded_image.link


# 畫有顏色的表格
def color_table():
    error_index = final_df[final_df['預測沒電日期'] == 'error '].index
    dd = final_df.drop(error_index)
    plt.rcParams['font.sans-serif'] = ['SimSun']
    fig, ax = plt.subplots(dpi=500)
    fig.patch.set_visible(False)
    ax.axis('tight')
    ax.axis('off')
    color = [['crimson'] * 4 for i in range(before)]
    color.extend([['coral'] * 4 for i in range(after)])
    # color.extend([['darksalmon'] * 4 for i in range(error)])
    ax.table(cellText=dd.values,
             colLabels=dd.columns,
             rowLabels=dd.index,
             cellColours=color,
             loc="center")

    path = os.getcwd()
    if not os.path.exists(path + '/forecast'):
        os.makedirs(path + '/forecast')

    plt.savefig('forecast/table.png')
    plt.close()

    client_id = '338e9d3319c68de'
    PATH = 'forecast/table.png'
    title = "Uploaded with PyImgur"
    im = pyimgur.Imgur(client_id)
    uploaded_image = im.upload_image(PATH, title=title)

    return uploaded_image.link
