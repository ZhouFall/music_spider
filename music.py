from loguru import logger
import codecs
import requests,json
import math
import random
import base64
from Crypto.Cipher import AES
from datetime import datetime
#词云图相关
import matplotlib.pyplot as plt
import jieba
from imageio import imread
from wordcloud import WordCloud, STOPWORDS,ImageColorGenerator
#多线程
from multiprocessing import Pool,cpu_count
import sys
import hashlib

# 生成16个随机字符
def generate_random_strs(length):
    string = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    # 控制次数参数i
    i = 0
    # 初始化随机字符串
    random_strs  = ""
    while i < length:
        e = random.random() * len(string)
        # 向下取整
        e = math.floor(e)
        random_strs = random_strs + list(string)[e]
        i = i + 1
    return random_strs

# AES加密
def AESencrypt(msg, key):
    # 如果不是16的倍数则进行填充(paddiing)
    padding = 16 - len(msg) % 16
    # 这里使用padding对应的单字符进行填充
    msg = msg + padding * chr(padding)
    # 用来加密或者解密的初始向量(必须是16位)
    iv = '0102030405060708'

    cipher = AES.new(bytearray(key,'utf-8'),AES.MODE_CBC, bytearray(iv,'utf-8'))
    # 加密后得到的是bytes类型的数据
    encryptedbytes = cipher.encrypt(bytearray(msg,'utf-8'))
    # 使用Base64进行编码,返回byte字符串
    encodestrs = base64.b64encode(encryptedbytes)
    # 对byte字符串按utf-8进行解码
    enctext = encodestrs.decode('utf-8')

    return enctext

# RSA加密
def RSAencrypt(randomstrs, key, f):
    # 随机字符串逆序排列
    string = randomstrs[::-1]
    # 将随机字符串转换成byte类型数据
    text = bytes(string, 'utf-8')
    seckey = int(codecs.encode(text, encoding='hex'), 16)**int(key, 16) % int(f, 16)
    return format(seckey, 'x').zfill(256)

# 获取参数
def get_params(text):
    # msg = '{"rid":"R_SO_4_1302938992","offset":"0","total":"True","limit":"100","csrf_token":""}'
    # 偏移量
    # offset和limit是必选参数,其他参数是可选的,其他参数不影响data数据的生成
    msg = text
    key = '0CoJUm6Qyw8W8jud'
    f = '00e0b509f6259df8642dbc35662901477df22677ec152b5ff68ace615bb7b725152b3ab17a876aea8a5aa76d2e417629ec4ee341f56135fccf695280104e0312ecbda92557c93870114af6c9d05c4f7f0c3685b7a46bee255932575cce10b424d813cfe4875d3e82047b97ddef52741d546b8e289dc6935b3ece0462db0a22b8e7'
    e = '010001'
    enctext = AESencrypt(msg, key)
    # 生成长度为16的随机字符串
    i = generate_random_strs(16)
    # 两次AES加密之后得到params的值
    encText = AESencrypt(enctext, i)
    # RSA加密之后得到encSecKey的值
    encSecKey = RSAencrypt(i, e, f)
    return encText, encSecKey

class NetEase():
    def __init__(self,link,text,headers):
        self.link = link
        self.text = text
        self.header = headers

    def create_form_data(self):
        text = json.dumps(self.text)
        params, encSecKey = get_params(text)
        form_data = {'params': params, 'encSecKey': encSecKey}
        return form_data

    def get_song_list(self):
        data = self.create_form_data()
        res = requests.post(self.link, headers= self.header, data=data)
        with open(r'data/wyy.json', 'wb') as f:
            f.write(res.content)
        if(res.status_code == 200):
            print('歌曲列表网页下载成功')
        else:
            print('歌曲列表网页下载失败，响应码为{}'.format(res.status_code))

    def analysis_song_list(self):
        filename = r'data/wyy.json'
        with open(filename,'rb') as f:
            content = json.load(f)
        tracks = content['playlist']['tracks']
        with open(r'data/song.txt', 'wb') as f:
            for k in tracks:
                song = k['name']
                f.write((song + '\n').encode('utf-8'))
        print('歌曲列表解析成功')

        with open(r'data/players.txt','wb') as f:
            for k in tracks:
                player = k['ar'][0]['name']
                f.write((player + '\n').encode('utf-8'))
        print('歌手解析成功')

        with open(r'data/pic_link.txt','wb') as f:
            for k in tracks:
                pic_url = k['al']['picUrl']
                # print(pic_url)
                #添加空格作为分界符,方便后续分解
                f.write((pic_url+' ').encode('utf-8'))
        print('歌曲图片链接解析成功')

    def muti_process(self):
        # urls = urls[0:21]    #拿前20个做实验
        pool = Pool(cpu_count())
        with open(r'data/pic_link.txt', 'rb') as f:
            urls = f.read()
        urls = urls.decode('utf-8').split()
        print('多线程启动')
        pool.map(self.downlaod_album, urls)
        pool.close()
        pool.join()

    def downlaod_album(self,url):
        try:
            with open(r'output/album/{}.png'.format(url[-15:-4]), 'wb') as f:
                f.write(requests.get(url).content)
                print('图片下载成功')
            # print(url[-10:-4])
        except ConnectionError:
            print('Error Occured ', url)
        finally:
            print('下载任务执行完毕')


class wordcloud():
    def __init__(self):
        self.file = ''
        self.pic = ''

    def cut_word(self,file):
        self.file = file
        with open(self.file,'rb') as f:
            text = f.read()
        cut_text = jieba.cut(text)
        result = " ".join(cut_text)
        return result

    def draw_wordcloud(self,file,pic,outfile):
        self.pic = pic
        mytext = self.cut_word(file)
        mask = imread(self.pic, pilmode="RGB")
        wc = WordCloud(
            # 设置字体，不指定就会出现乱码
            font_path=r"C:\Windows\Fonts\simhei.ttf",
            #避免词的重复
            collocations = False,
            # 设置背景色
            background_color='white',
            # 设置背景宽
            width=500,
            # 设置背景高
            height=350,
            max_words=1000,
            # 最大字体
            max_font_size=50,
            # 最小字体
            min_font_size=5,
            font_step=4,
            mode='RGBA',
            # colormap='pink'
            mask=mask
        )
        # 产生词云
        wc.generate(mytext)
        # 从背景图建立颜色方案
        # image_colors = ImageColorGenerator(mask)
        # 将词云颜色设置为背景图方案
        # wc.recolor(color_func=image_colors)
        # 保存图片
        wc.to_file(r"output/"+outfile)  # 按照设置的像素宽高度保存绘制好的词云图，比下面程序显示更清晰
        print('词云图片保存成功')
        # 4.显示图片
        # 指定所绘图名称
        plt.figure("Netease")
        # 以图片的形式显示词云
        plt.imshow(wc)
        # 关闭图像坐标系
        plt.axis("off")
        # plt.show()
        #显示5s后消失
        plt.ion()
        plt.pause(5)
        plt.close()



if __name__ == '__main__':
    # song_list = 'https://music.163.com/weapi/v6/playlist/detail?csrf_token=0251ce2d0e4fad451746504430572ee3'
    # text = {
    #     'id': "",
    #     'offset': "0",
    #     'total': "true",
    #     'limit': "1000",
    #     'n': "1000",
    #     'csrf_token': "0251ce2d0e4fad451746504430572ee3"
    # }
    # ?csrf_token=0251ce2d0e4fad451746504430572ee3,可不加
    #爬取登录页面时，密码可以用以下hash方式加密，然后输入
    # content = ""
    # md5hash = hashlib.md5(content.encode('utf-8'))
    # md5 = md5hash.hexdigest()
    # print(md5)
    link = 'https://music.163.com/weapi/v6/playlist/detail'
    song = {
        'id': "",    #此处添加你的id，数据提交格式按照说明自己查看一下
        'offset': "0",
        'total': "true",
        'limit': "1000",
        'n': "1000",
        'csrf_token': ""
    }
    headers1 = {
        "Accept": "*/*",
        "Accept-Encoding": "gzip,deflate,br",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Connection": "keep-alive",
        "Content-Type": "application/x-www-form-urlencoded",
        "Host": "music.163.com",
        "Referer": "https://music.163.com/my/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.66 Safari/537.36",
        'Cookie' : 'NMTID=00OtwnUrt3vyloXqU3CrJQUz0o-yFUAAAF2LNqIrA; JSESSIONID-WYYY=AXdnG8nFpoY6PNi3XDdHgu99GoiK59brvkdEsAWd9Dk4u1089gqezazwWxWhCNNZ9wU7CoCFKXJhAboxaOMPRaVS2kmxgYb03I8th7aD72uXAHpQI6CUZRO6IldW%2FRgqPz1EAj2ozCzEeT957j826t78SS%2FOsKrilkCIue0PlHdK0t%2F%2B%3A1607082653296; _iuqxldmzr_=32; _ntes_nnid=9b95e833cabaf03992755f38d129f286,1607070412949; _ntes_nuid=9b95e833cabaf03992755f38d129f286; WM_NI=awDKKogly2FEWYgqHXRmTkHJIAqvPztlqKzum6mrAwE4kFsMecGBGSLRKKcT4nr5dA3tA6aOcqLjivp4L%2F65CRg1H4ijf6oJ7a67Bw43FuWIGjyz3qzGENdashEyPenNN2o%3D; WM_NIKE=9ca17ae2e6ffcda170e2e6eea8c445edb388d1b770a68e8eb3c54f838f8eabaa6f96a6a5daf85fb391bd92c52af0fea7c3b92aa3a98cacca65a5b4b7d3c54f9587a992cb5492b39c8ccb428b9fbf97d372b8b4bfacf97fafeaa393c47d87eca5a7f247a7bd89a3c659908e85ace260f8b2bed6e74bf1ac8fd7e445a1af848bec7eb4ec84d0b53f818ea9d2cb40abb6aad7ee42f5bffad8c17df8ed8a96d64385b6b79bb27bba998bafe76bb1b88b9ad36fae9282d3ee37e2a3; WM_TID=YeT5mqogqlRAVABRAUdueB3h9rV%2BO86Q; ntes_kaola_ad=1; WEVNSM=1.0.0; WNMCID=xqvafx.1607073379709.01.0; __remember_me=true; MUSIC_U=56131b60258d038b13494f63fb6163f1bf9b6ae5b82252dab58e6be3caa4bce20931c3a9fbfe3df2; __csrf=0251ce2d0e4fad451746504430572ee3'
    }
    wyy = NetEase(link,song,headers1)
    starttime = datetime.now()
    print('开始时间为{}'.format(starttime))
    wyy.get_song_list()
    wyy.analysis_song_list()
    wyy.muti_process()
    #参数可以在实例化的时候传入,也可以每次画图的时候传入
    wcloud = wordcloud()
    wcloud.draw_wordcloud(r'data/song.txt',r'data/alice.jpg','alice.png')
    wcloud.draw_wordcloud(r'data/players.txt',r'data/alice.jpg','alice1.png')
    endtime = datetime.now()
    print('结束时间为{}'.format(endtime))
    print('运行时间为{}'.format(endtime - starttime))

