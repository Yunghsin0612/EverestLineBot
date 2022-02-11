# # [1] import data (約9分鐘)
import pyodbc
from datetime import datetime
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

pyodbc.drivers()
conx = pyodbc.connect('DRIVER={SQL Server}; SERVER=172.19.3.224; Database=everest_tracking; UID=user1; PWD=Aa22817999@')
cursor = conx.cursor()

# 取全定位卡資料，生成SQL指令
seq = []
for i in list(range(1, 32)):
    seq.append('SELECT [CardID],[Battery],[UDateTime] FROM [everest_tracking].[dbo].[pathtable' + '%02d' % i + ']')
query = ' UNION '.join(seq)

# 抓資料
cursor.execute(query)
data = sorted(list(map(lambda x: list(x), cursor.fetchall())),
              key=lambda x: datetime.strptime(x[2], "%Y/%m/%d %H:%M:%S"), reverse=True)
# 所有卡號列表
id_list = []
# 卡號最新資訊
all_info = []
# 選出最新的資料
for i in data:
    if i[0] not in id_list:
        id_list.append(i[0])
        all_info.append(i)


# # [2] 分類中高低穩定度資料 (約23分鐘)
# 計算震盪次數
def unsteady(num):
    drop = 0
    up = 0
    result = sorted(list(map(lambda x: list(x), list(filter(lambda i: i[0] == num, data)))),
                    key=lambda d: datetime.strptime(d[2], "%Y/%m/%d %H:%M:%S"), reverse=False)
    mm = [int(i[1]) for i in result]
    for i in range(len(mm) - 1):
        if mm[i + 1] - mm[i] < 0:
            drop += 1
        if mm[i + 1] - mm[i] > 0:
            up += 1
    return [num, drop, up]


steady = list(map(lambda i: unsteady(i), id_list))
# 各卡號震盪情形表格
col = ['CardID', 'drop', 'up']
ddd = pd.DataFrame(steady, columns=col)
ddd['total'] = ddd['drop'] + ddd['up']
# 計算總體震盪平均與標準差
drop_mean = ddd['drop'].mean()
drop_s = ddd['drop'].std()
up_mean = ddd['up'].mean()
up_s = ddd['up'].std()
# 設定兩倍標準差邊界
drop_std = drop_s * 2
up_std = up_s * 2
# 限制式
block1 = (ddd['up'] < up_mean + up_std)
block2 = (ddd['drop'] < drop_mean) & (ddd['up'] > up_mean + up_std)
block3 = (ddd['drop'] > drop_mean) & (ddd['up'] > up_mean + up_std)
# 震盪中高穩定資料，排除單次下降
ok = ddd[block1 | block2]
ok = ok.drop(ok[ok['drop'] < 2].index)
# 震盪低穩定的異常資料
no = ddd[block3]

# # [3] 線性回歸中高穩定資料 (約37分鐘QQ)

import time
from sklearn import linear_model
from sklearn.model_selection import train_test_split


def linear_all(datas):
    id_coef_accuracy = []
    can_not_cal = []

    def search(num):
        result = sorted(list(map(lambda x: list(x), list(filter(lambda i: i[0] == num, data)))),
                        key=lambda d: datetime.strptime(d[2], "%Y/%m/%d %H:%M:%S"), reverse=False)
        for i in result:
            i[2] = int(time.mktime(time.strptime(i[2], "%Y/%m/%d %H:%M:%S")))
        return result

    for i in datas:
        record = search(i)
        # 建立dataframe
        col = ['CardID', 'Battery', 'UDateTime']
        df = pd.DataFrame(record, columns=col)
        df.set_index('UDateTime', inplace=True)
        # 線性回歸
        X = df.index.values.reshape(-1, 1)
        y = df['Battery']
        try:
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=0)
            regr = linear_model.LinearRegression()
            regr.fit(X_train, y_train)
            ##計算回歸準確度
            score = float(regr.score(X_test, y_test)) * 100
            ## 計算出截距值與係數值
            w_0 = float(regr.intercept_)
            w_1 = float(regr.coef_)
            id_coef_accuracy.append([i, w_1, score])
        except ValueError:
            can_not_cal.append(i)

    return id_coef_accuracy, can_not_cal


# 中高穩定資料下降幅度
final, error = linear_all(ok['CardID'])
col = ['CardID', '單月估算下降電量', 'accuracy']
df1 = pd.DataFrame(final, columns=col)
df1['單月估算下降電量'] = df1['單月估算下降電量'] * -2592000


# # [4] box-plot outlier detection (約2分鐘)
# 計算box-plot邊界
def cal_bound(arr):
    q1 = np.quantile(arr, 0.25)
    q3 = np.quantile(arr, 0.75)
    iqr = q3 - q1
    upper_bound = q3 + (1.5 * iqr)
    return upper_bound


# 中高穩定高耗電資料
arr1 = df1['單月估算下降電量'].to_numpy()
upper_bound = cal_bound(arr1)
serious_drop = df1[df1['單月估算下降電量'] >= upper_bound]
# 只有單次下降的資料
only_one_drop = ddd[(ddd['drop'] == 1) & (ddd['up'] == 0)]
# 計算單次下降數值
drop_b = []
for num in only_one_drop['CardID']:
    result = list(map(lambda x: int(x[1]), list(filter(lambda i: i[0] == num, data))))
    m = max(result) - min(result)
    drop_b.append(m)
only_one_drop['drop_b'] = drop_b
# 輸出單次下降大於臨界值
cliff = only_one_drop[only_one_drop['drop_b'] >= upper_bound]

# # [5 輸出前置作業]找定位卡最新位置 (約2分半鐘)
# 擷取異常定位卡最新電量時間資訊
search_id = list(no['CardID']) + list(cliff['CardID']) + list(serious_drop['CardID'])
search_info = list(filter(lambda x: x[0] in search_id, all_info))


# 生成SQL指令，抓異常卡號位置資料
def query_pos(info):
    result = 'OR '.join(map(lambda i: '[CardID] = ' + f" '{i[0]}' " + 'AND [Battery] = ' + f" '{i[1]}' " + 'AND [UDateTime] = ' + f" '{i[2]}' ",info))
    seq = []
    for i in list(range(1, 32)):
        seq.append('SELECT [CardID],[AreaID] FROM dbo.pathtable' + '%02d' % i + ' WHERE ' + result)
    query = ' UNION '.join(seq)
    return query

cursor.execute(query_pos(search_info))
pos_data = list(map(lambda x: list(x), cursor.fetchall()))

# search_info加入位置資料
def find_pos(num, pos_data):
    result = []
    for i in pos_data:
        if i[0] == num:
            result.append(i[1])
    return result

for i in search_info:
    a = find_pos(i[0], pos_data)
    i.append(a)
# 分群
search_info_no = []
search_info_cliff = []
search_info_serious_drop = []
for i in search_info:
    if i[0] in list(no['CardID']):
        search_info_no.append(i)
    if i[0] in list(cliff['CardID']):
        search_info_cliff.append(i)
    if i[0] in list(serious_drop['CardID']):
        search_info_serious_drop.append(i)

# # [輸出結果] 高耗電卡號

# 建立dataframe
serious_drop_final = serious_drop.copy()
serious_drop_final.set_index('CardID', inplace=True)
serious_drop_final['預測準確度 %'] = np.round(serious_drop_final['accuracy'], 2)
serious_drop_final['單月估算下降電量'] = np.round(serious_drop_final['單月估算下降電量'], 2)
serious_drop_final['最新資料'] = list(map(lambda x: str('電量剩餘 ' + x[1] + '  紀錄於 ' + x[2]), search_info_serious_drop))
serious_drop_final['最新位置'] = list(map(lambda x: x[3], search_info_serious_drop))
serious_drop_final = serious_drop_final.drop(columns=['accuracy']).sort_values(by=['單月估算下降電量'], ascending=False)

def power():
    d = serious_drop_final.copy()
    d.drop(columns=['預測準確度 %', '最新資料', '最新位置'], inplace=True)
    d = d.reset_index()
    d.loc[d['單月估算下降電量'] > 100, '單月估算下降電量'] = 100
    o = '當前高耗電定位卡張數 : ' + str(len(list(d['CardID'])))
    o += '\n**************************'
    o += '\n卡號      單月估算下降電量\n'
    for i in range(len(list(d['CardID']))):
        o += '\n' + list(d['CardID'])[i] + '  ----------->   ' + str(list(d['單月估算下降電量'])[i])

    return o

# # [輸出結果] 單次掉電過大卡號
# 建立dataframe
cliff_final = cliff.copy()
cliff_final.set_index('CardID', inplace=True)
cliff_final = cliff_final.drop(columns=['drop', 'up', 'total']).rename(columns={"drop_b": "單次下降電量"}).sort_values(
    by=["單次下降電量"], ascending=False)
cliff_final['最新資料'] = list(map(lambda x: str('電量剩餘 ' + x[1] + '  紀錄於 ' + x[2]), search_info_cliff))
cliff_final['最新位置'] = list(map(lambda x: x[3], search_info_cliff))

#掉電
def cliff():
    d = cliff_final.copy()
    d.drop(columns=['最新資料', '最新位置'], inplace=True)
    d = d.reset_index()
    d.loc[d['單次下降電量'] > 100, '單次下降電量'] = 100
    o = '當前掉電過大定位卡張數 : ' + str(len(list(d['CardID'])))
    o += '\n******************************'
    o += '\n卡號          單次下降電量\n'
    for i in range(len(list(d['CardID']))):
        o += '\n' + list(d['CardID'])[i] + '  ------------>   ' + str(list(d['單次下降電量'])[i])

    return o

# # [輸出結果] 電量震盪過大卡號
no_final = no.copy()
no_final.set_index('CardID', inplace=True)
no_final = no_final.drop(columns=['drop', 'up']).rename(columns={"total": "總震盪次數"}).sort_values(by=['總震盪次數'],ascending=False)
no_final['最新資料'] = list(map(lambda x: str('電量剩餘 ' + x[1] + '  紀錄於 ' + x[2]), search_info_no))
no_final['最新位置'] = list(map(lambda x: x[3], search_info_no))

#震盪
def qq():
    d = no_final.copy()
    d.drop(columns=['最新資料', '最新位置'], inplace=True)
    d = d.reset_index()
    o = '當前電量震盪過大定位卡張數 : ' + str(len(list(d['CardID'])))
    o += '\n*******************************'
    o += '\n卡號                總震盪次數\n'
    for i in range(len(list(d['CardID']))):
        o += '\n' + list(d['CardID'])[i] + '  --------------->   ' + str(list(d["總震盪次數"])[i])

    return o

