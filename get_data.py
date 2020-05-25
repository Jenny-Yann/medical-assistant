from selenium import webdriver
from pyquery import PyQuery as pq
import requests
import pymongo
from bson.objectid import ObjectId

# log：医院、医生列表未解决翻页问题
#      数据存放在 helper2 helper3 数据相同

home_url = 'https://yyk.familydoctor.com.cn/area_305_0_0_0_1.html'

def get_html2(url):           #获取当前页面html  by selenium
    browser = webdriver.Chrome()
    browser.get(url)
    html = browser.page_source  
    browser.close()
    return html

def get_html(url):            #获取当前页面 by requests
    headers = {
        'user-agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36'
    }
    r = requests.get(url,headers = headers)
    return r.text

def get_area_list(url):       #建立区的二级list
    html = get_html(url)
    doc = pq(html)
    areas = doc('.selection .filter .clearfix a').items()
    areas_list = []
    for area in areas:
        tmp = []
        tmp.append(area.text())
        tmp.append(area.attr('href'))  #为每一个区建立一个list，list[0]=区名 list[1]=页面url
        areas_list.append(tmp)
    areas_list.pop(0)     #删去无关第一项
    return areas_list     #返回所有区list

def get_hosp_list(url):  #获取当前区的所有医院及页面url二级list       未解决翻页问题!
    html = get_html(url)
    doc = pq(html)
    hosps = doc('.listItem .summary a').items()
    hosp_list = []
    for hosp in hosps:
        tmp = []
        tmp.append(hosp.text())
        tmp.append(hosp.attr('href'))
        hosp_list.append(tmp)
    return hosp_list

def get_hosp_inf(url):             #返回该医院各项信息的元组
    detail_url = url + 'detail/'   #构造医院的介绍页面，医师页面，地址页面
    sche_url = url + 'schedule/'
    map_url = url + 'map/'
    #科室信息

    details = get_details(detail_url)      #获取医院介绍一级列表(包含3个字符串)
    departs = get_departs(url)
    schedules = get_schedules(sche_url)    #获取医生列表二级（一医生一列表）
    maps = get_maps(map_url)               #获取地址信息一级列表

    return details,departs,schedules,maps          #自动封装成元组 直接用多个变量接收

def get_details(detail_url):   #获取医院介绍信息
    html = get_html(detail_url)
    doc = pq(html)
    title = doc('.mBasicInfo .titleBar h3').text()  #获取标题
    basics = doc('.mBasicInfo .moduleContent dl').items() #获取基本信息生成器
    details = doc('.mIntroduction .moduleContent p').items() #获取详情信息生成器
    
    result = []  #结果列表：标题，基本信息，详情  

    result.append(title)  #写入标题 (字符串1)

    for basic in basics:    #写入基本信息 (字符串2)
        key = basic('dt').text()
        value = basic('dd').text()
        result.append(key+value)

    detail_tmp = ''     #写入详情(长字符串3)
    for detail in details:
        detail_tmp += (detail('p').text())
    result.append('医院详情:' + detail_tmp)

    return result    #返回包含三个字符串元素的列表

def get_departs(url):
    html = get_html(url)
    doc = pq(html)
    departs = doc('.mCategory .mc .itemTitle a').items()
    result = []
    for depart in departs:
        result.append(depart.text())
    return result
    
def get_schedules(sche_url):    #获取该医院的医生及其擅长疾病的2级list  未实现翻页
    html = get_html(sche_url)
    doc = pq(html)
    docts = doc('.wrap .mSchedule .tabContent tr:has(td)').items()
    result = []
    for doct in docts:
        name = doct('span[itemprop]')
        duty = doct('.doctorInfo p:eq(1)')
        info = doct('td:eq(1)')
        doctor = []
        if duty and name and info:
            doctor.append(name.text())
            doctor.append(duty.text())
            doctor.append(info.text())
            result.append(doctor)
    return result     

def get_maps(map_url): #获取得分以及各项信息的一级列表
    html = get_html(map_url)
    doc = pq(html)
    result = []
    score = '综合得分：'+doc('.subLogo .score em').text() + ' / 10分'  
    try:
        result.append(int(doc('.subLogo .score em').text())) #首项为整数型得分，用于排序
    except ValueError :
        return None
    
    result.append(score)
    infos = doc('.mYydz .moduleContent dl').items()
    for info in infos:
        result.append(info('dt').text() + info('dd').text())
    
    return result

    
if __name__ == "__main__":
    client = pymongo.MongoClient(host='localhost',port=27017)
    db = client.helper3
    areas = get_area_list(home_url)
    collections = []
    for area in areas:
        collection = db[area[0]] #为每一个区建一个表（集合）
        collections.append(collection)  

    #方式一：手动改变索引进行爬取
           
    # index = 12
    # hosps = get_hosp_list(areas[index][1])  # 收集该区医院信息 手动指定areas
    # for hosp in hosps:
    # tmp = {}
    # tmp['name'] = hosp[0]
    # details,departs,schedules,maps = get_hosp_inf(hosp[1])
    # if details:
    #     tmp['detail'] = details
    # if departs:
    #     tmp['depart'] = departs
    # if schedules:
    #     tmp['doctor'] = schedules
    # if maps:
    #     tmp['score'] = maps[0]
    #     maps.pop(0)
    #     tmp['address'] = maps
    # if tmp:
    #     result = collections[index].insert_one(tmp)   #手动指定集合 collections
    #     print(areas[index][0],hosp[0]+'加载完成',result)
    


    #方式二：自动循环索引（有可能会报停）

        hosps = get_hosp_list(area[1])  # 收集该区医院信息 手动指定areas
        for hosp in hosps:
            tmp = {}
            tmp['name'] = hosp[0]
            details,departs,schedules,maps = get_hosp_inf(hosp[1])
            if details:
                tmp['detail'] = details
            if departs:
                tmp['depart'] = departs
            if schedules:
                tmp['doctor'] = schedules
            if maps:
                tmp['score'] = maps[0]
                maps.pop(0)
                tmp['address'] = maps 
            if tmp:
                result = collection.insert_one(tmp)   #手动指定集合 collections
                print(area[0],hosp[0]+'加载完成',result)
        

    


