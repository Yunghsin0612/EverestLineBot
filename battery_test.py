import pyodbc

pyodbc.drivers()
conx = pyodbc.connect('DRIVER={SQL Server}; SERVER=172.19.3.224; Database=everest_tracking; UID=user1; PWD=Aa22817999@')
cursor = conx.cursor()


def query(left):
    select = 'SELECT [CardID],Battery FROM [everest_tracking].[dbo].[pathtable'
    where = '] WHERE [Battery]<='
    seq = []
    for i in list(range(1, 32)):
        if i < 10:
            line = select + '0' + str(i) + where + f" {left} "
            seq.append(line)
        else:
            line = select + str(i) + where + f" {left} "
            seq.append(line)
    query = ' UNION '.join(seq)
    return query


def finding(num):
    # 抓資料
    cursor.execute(query(num))
    new_data, card = [], []
    for i in cursor.fetchall():
        if i[0] not in new_data:
            card.append(i[0])
            new_data.append(i[0]+' : ' + i[1])
    return new_data
