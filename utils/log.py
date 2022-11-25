import logging
from logging.handlers import TimedRotatingFileHandler
import os
import time
import colorlog

from utils.config_generator import configObject

# 默认日志存储位置
default_log_dir = os.path.join(os.path.dirname(__file__), "..", "logs")

# 颜色用于区分日志等级
# 1、HTML文件显示
HTML_COLORS = {
    'DEBUG': '0000aa',
    'INFO': '0000ff',
    'WARNING':  'aaaa00',
    'ERROR':    'aa0000',
    'CRITICAL': 'aa00aa'
}

# 2、终端显示
TEMINAL_COLOR = {
    'DEBUG': 'white',
    'INFO': 'green',
    'WARNING': 'yellow',
    'ERROR': 'red',
    'CRITICAL': 'bold_red',
}



class ColorFormatter(logging.Formatter):
    """
    日志格式生成(可带颜色)
    颜色详情参阅COLORS字典
    """
    def __init__(self, msg, use_color=True):
        logging.Formatter.__init__(self, fmt=msg, datefmt='%H:%M:%S')
        self.use_color = use_color

    def format(self, record):
        levelname = record.levelname
        if self.use_color and levelname in HTML_COLORS:
            record.levelname = '['+ levelname[0] + ']'
            record.color = HTML_COLORS[levelname] + ';">'
        return logging.Formatter.format(self, record)



def create_file_logger(log_dir=default_log_dir, log_level = logging.DEBUG, file_name_prefix="longer_", name=None):
    if not os.path.exists(log_dir):
        os.mkdir(log_dir)
    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    # 建立一个filehandler来把日志记录在HTML文件里，级别为debug以上
    filename = os.path.join(log_dir, file_name_prefix) + time.strftime("%Y-%m-%d") + ".html" # 以日期为单位分隔日志
    file_handler = TimedRotatingFileHandler(filename, when='D', interval=1,
                                   encoding="utf-8", backupCount=7)
    file_handler.file_name_prefix = file_name_prefix
    color_format = '<p style="margin-top:0px; margin-bottom:0px;font-family:serif;font-weight:bold;">' \
                   ' %(asctime)s.%(msecs)03d <span style=" color:#%(color)s%(levelname)s %(threadName)s %(filename)s' \
                   ' %(lineno)d: %(message)s</span></p>'
    color_formatter = ColorFormatter(color_format)
    file_handler.setFormatter(color_formatter)

    # 建立一个teminal_heandler来把日志显示在终端，级别为debug以上
    teminal_heandler = logging.StreamHandler()
    fmt_string = '%(log_color)s%(levelname)s%(message)s'
    fmt = colorlog.ColoredFormatter(fmt_string, log_colors=TEMINAL_COLOR)
    teminal_heandler.setFormatter(fmt)


    # 添加日志handler到logger
    logger.addHandler(file_handler)
    logger.addHandler(teminal_heandler)
    return logger



logs = create_file_logger(log_level=logging.DEBUG) # 用于写入文本



# 日志测试
if __name__ == "__main__":
    logs.info("下面为一组日志测试")
    logs.info("这是一个Info日志")
    logs.debug("这是一个Debug日志")
    logs.warning("这是一个Warning日志")
    logs.error("这是一个Error日志")
    logs.info("日志测试结束")
