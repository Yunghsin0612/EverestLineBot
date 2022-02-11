import pandas as pd
import numpy as np
import datetime
import pymssql

conn = pymssql.connect(server='172.19.3.224', user='user1', password='Aa22817999@', database='everest_tracking',
                       as_dict=True)
cursor = conn.cursor()

date = datetime.date.today() + datetime.timedelta(-1)
cursor.execute('SELECT * FROM dbo.pathtable' + '%02d' % date.day + ' WHERE Battery >= %s', '50')
data = pd.DataFrame(cursor.fetchall())
groups = data.groupby(data.CardID)

def stable():
    dataframe = pd.DataFrame(columns=['Date', 'CardID', 'unSteadyness', 'Battery'])
    a = 0
    card = '不穩定定位卡號: '
    for CardID in groups:
        # find longest
        df = groups.get_group(CardID[0]).groupby(groups.get_group(CardID[0]).AreaID).size().reset_index(name="len")
        area = df[df["len"] == max(df["len"])].AreaID
        area = area.to_string()
        data_day = groups.get_group(CardID[0]).groupby(groups.get_group(CardID[0]).AreaID).get_group(area[-5:])

        # calculate mean and std
        mean = []
        sd = []
        num = []
        for i in range(0, len(data_day)):
            if (i == 0):
                num.append(float(data_day.iat[i, 4]))
                if (len(data_day) == 1):
                    mean.append(np.mean(num))
                    sd.append(np.std(num))
                continue
            if (data_day.iat[i, 6] < data_day.iat[i - 1, 6] or data_day.iat[i, 6] == data_day.iat[i - 1, 6]):
                if (int(data_day.iat[i, 6]) < 65534):
                    mean.append(np.mean(num))
                    sd.append(np.std(num))
                    num = []
            num.append(float(data_day.iat[i, 4]))
            if (i == len(data_day) - 1 and len(num) != 0):
                mean.append(np.mean(num))
                sd.append(np.std(num))

        # calculate coefficient of variation
        sdy = []
        for i in range(0, len(mean)):
            if (mean[i] == 0):
                mean[i] = 1
            steady = sd[i] / mean[i]
            sdy.append(steady)
        sdy = round(np.mean(sdy) * 100, 2)

        # print
        if (sdy > 15):
            card += CardID[0]+' '
            p = groups.get_group(CardID[0])
            a = 1
        bat = data_day.iat[-1, 5]

        dataframe = dataframe.append({'Date': date, 'CardID': CardID[0], 'unSteadyness': sdy, 'Battery': bat},
                                     ignore_index=True)

    if (a == 0):
        return 'Every card is stable'
    else:
        return card
