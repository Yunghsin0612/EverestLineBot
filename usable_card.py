import pymssql, os, shutil, pyimgur
import datetime
import pandas as pd
import matplotlib.pyplot as plt
plt.switch_backend('agg')

conn = pymssql.connect(server='172.19.3.224', user='user1', password='Aa22817999@', database='everest_tracking')
cursor = conn.cursor()
seq = []

# 找出所有定位卡
for i in list(range(1, 32)):
    seq.append('SELECT CardID,Battery FROM dbo.pathtable' + '%02d' % i)

query = ' UNION '.join(seq)
cursor.execute(query)
data = cursor.fetchall()
all_cardID, total_card = [], []

for i in data:
    if i[0] not in all_cardID:
        all_cardID.append(i[0])
        total_card.append([i[0], int(i[1])])

all_card = pd.DataFrame(total_card, columns=['CardID', 'Battery'])

date = datetime.date.today() + datetime.timedelta(-1)
cursor.execute('SELECT CardID,Battery,UDateTime FROM dbo.pathtable' + '%02d' % date.day)
yesterday_cardID, yesterday_total = [], []
data = cursor.fetchall()

# 找出前一天低電量情況
for i in data:
    if i[0] not in yesterday_cardID:
        yesterday_cardID.append(i[0])
        yesterday_total.append([i[0], int(i[1]),i[2]])

yesterday_card = pd.DataFrame(yesterday_total, columns=['CardID', 'Battery', 'Date'])
unusable_card = yesterday_card[yesterday_card['Battery'] < 30]
unusableID = list(unusable_card['CardID'])
result='OR '.join(map(lambda i: 'CardID = '+f" '{i}' ", unusableID))
seq=[]
for i in list(range(1,32)):
    seq.append('SELECT CardID,Battery,UDateTime FROM dbo.pathtable'+ '%02d' %i + ' WHERE ' +result )
    query=' UNION '.join(seq)
cursor.execute(query)
record = cursor.fetchall()

from datetime import datetime


def find_card(cardID):
    num = cardID
    path = os.getcwd()
    if not os.path.exists(path + '/everestPic'):
        os.makedirs(path + '/everestPic')
    else:
        shutil.rmtree(path + '/everestPic')
        os.makedirs(path + '/everestPic')

    result = sorted(list(map(lambda x: list(x), list(filter(lambda i: i[0] == num, record)))),
                    key=lambda d: datetime.strptime(d[2], "%Y/%m/%d %H:%M:%S"), reverse=False)
    x = [datetime.strptime(i[2], "%Y/%m/%d %H:%M:%S") for i in result]
    y = [int(i[1]) for i in result]
    name = num + '.png'
    # 繪圖
    plt.plot_date(x, y, linestyle='solid')
    plt.gcf().set_size_inches(15, 6)
    plt.title('Battery Data of ' + num, fontsize=20)  # 設定圖形標題
    plt.xlabel('Date', fontsize=20)  # 設定X軸標籤
    plt.ylabel('Battery', fontsize=20)
    plt.savefig('everestPic/' + name)
    plt.close()

    client_id = '4b685f760b2d4d5'
    PATH = 'everestPic/' + name  # A Filepath to an image on your computer"
    title = "Uploaded with PyImgur"

    im = pyimgur.Imgur(client_id)
    uploaded_image = im.upload_image(PATH, title=title)

    return uploaded_image.link

# 印出電量資訊(若要dataframe原資料即是)
def battery_info():

    lowbat_info = '昨日低於電量30定位卡數量 : '+ str(len(unusable_card))
    lowbat_info += '\n******************************'
    lowbat_info += '\n低電量卡號            剩餘電量\n'
    yes_ratio = '%.2f' % ((len(yesterday_cardID) - len(unusable_card)) / len(yesterday_cardID) * 100) + '%'
    yes_ratio+='\n(昨日記錄定位卡數量) : '+str(len(yesterday_cardID))
    all_ratio = '%.2f' % ((len(all_cardID) - len(unusable_card)) / len(all_cardID) * 100) + '%'
    all_ratio += '\n(31天內可用定位卡數量) : '+str(len(all_cardID))
    for i in range(0, len(unusable_card)):
        lowbat_info += str(unusable_card.iat[i, 0]) + '   ------------>     ' + str(unusable_card.iat[i, 1]) + '\n'
    lowbat_info += '\n******************************'
    lowbat_info += '\n在對話框中輸入 : 卡號' + unusable_card.iat[0, 0] + '\n可查看詳細情形'
    return lowbat_info, yes_ratio, all_ratio
