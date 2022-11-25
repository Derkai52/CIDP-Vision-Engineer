import logging
from utils import json_keys as jk
from utils.util_file import read_json_file, write_json_file


setting_file_path = "../config.json"


class ImageConfig():
    """
    doc: 图像配置类
    """
    def __init__(self, js):
        self.from_json(js)

    def from_json(self, js):
        self.image_orgin = js.get(jk.image_orgin, 0)
        self.create_template_mode = js.get(jk.create_template_mode, False)
        self.minH = js.get(jk.minH, 0)
        self.maxH = js.get(jk.maxH, 255)
        self.minS = js.get(jk.minS, 0)
        self.maxS = js.get(jk.maxS, 255)
        self.minV = js.get(jk.minV, 0)
        self.maxV = js.get(jk.maxV, 255)

    def to_json(self):
        return {jk.image_orgin: self.image_orgin,
                jk.create_template_mode: self.create_template_mode,
                jk.minH: self.minH,
                jk.maxH: self.maxH,
                jk.minS: self.minS,
                jk.maxS: self.maxS,
                jk.minV: self.minV,
                jk.maxV: self.maxV}


class DetectionConfig():
    """
    doc: 识别参数配置类
    """
    def __init__(self, js):
        self.from_json(js)

    def from_json(self, js):
        self.min_angle = js.get(jk.min_angle, 20)
        self.max_angle = js.get(jk.max_angle, 70)
        self.min_aspect_ratio = js.get(jk.min_aspect_ratio, 0.6)
        self.max_aspect_ratio = js.get(jk.max_aspect_ratio, 1.6)
        self.min_area = js.get(jk.min_area, 1000)
        self.max_area = js.get(jk.max_area, 7000)
        self.tmpWidth = js.get(jk.tmpWidth, 100)
        self.tmpHeight = js.get(jk.tmpHeight, 100)
        self.tmpThreshold = js.get(jk.tmpThreshold, 0.5)

    def to_json(self):
        return {jk.min_angle: self.min_angle,
                jk.max_angle: self.max_angle,
                jk.min_aspect_ratio: self.min_aspect_ratio,
                jk.max_aspect_ratio: self.max_aspect_ratio,
                jk.min_area: self.min_area,
                jk.max_area: self.max_area,
                jk.tmpWidth: self.tmpWidth,
                jk.tmpHeight: self.tmpHeight,
                jk.tmpThreshold: self.tmpThreshold}


class CommunicationConfig():
    """
    doc: Mech通讯配置类
    """
    def __init__(self, js):
        self.from_json(js)

    def from_json(self, js):
        self.bps = js.get(jk.bps, 115200)
        self.debug_data_flag = js.get(jk.debug_data_flag, False)
        self.debug_vofa_flag = js.get(jk.debug_vofa_flag, False)

    def to_json(self):
        return {jk.bps: self.bps,
                jk.debug_data_flag: self.debug_data_flag,
                jk.debug_vofa_flag: self.debug_vofa_flag}



class LogConfig():
    """
    doc: 日志配置类
    """
    def __init__(self, js):
        self.from_json(js)

    def from_json(self, js):
        self.log_save_path = js.get(jk.log_save_path, "")
        self.log_save_level = js.get(jk.log_save_level, "warning")
        self.log_back_count = js.get(jk.log_back_count, 30)
        self.log_format = js.get(jk.log_format, "'%(asctime)s - %(levelname)s: %(message)s'") # bug

    def to_json(self):
        return {jk.log_save_path: self.log_save_path,
                jk.log_save_level: self.log_save_level,
                jk.log_back_count: self.log_back_count,
                jk.log_format: self.log_format}

class DisplayConfig():
    """
    doc: 展示配置页设置类
    """
    def __init__(self, js):
        self.from_json(js)

    def from_json(self, js):
        pass

    def to_json(self):
        pass

class OtherConfig():
    """
    doc: 其他配置页设置类
    """
    def __init__(self, js):
        self.from_json(js)

    def from_json(self, js):
        self.update_doc_name = js.get(jk.update_doc_name, "update_log.html")

    def to_json(self):
        return {jk.update_doc_name: self.update_doc_name}


# 单例模式装饰器
def singleton(cls, *args, **kwargs):
    instances = {}
    def _singleton():
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return _singleton

@singleton
class Generator(object):
    def __init__(self):
        self.deserialize_config()  # 当转化器初始化时，进行反序列化操作(解包json配置文件)

    # 反序列化操作(解包json配置文件设置并将其读取)
    def deserialize_config(self):
        configs = read_json_file(setting_file_path)
        self.image_config = ImageConfig(configs.get(jk.image, {}))
        self.detection_config = DetectionConfig(configs.get(jk.detection, {}))
        self.communication_config = CommunicationConfig(configs.get(jk.communication, {}))
        self.log_config = LogConfig(configs.get(jk.log, {}))
        self.display_config = DisplayConfig(configs.get(jk.display, {}))
        self.other_config = OtherConfig(configs.get(jk.other, {}))


    # 序列化操作：将各部分(图像配置、通讯、日志、可视化等)配置文件写入为json形式并保存到指定路径
    def serialize_config(self):
        configs = {}
        configs[jk.image] = self.image_config.to_json()
        configs[jk.detection] = self.detection_config.to_json()
        configs[jk.communication] = self.communication_config.to_json()
        configs[jk.log] = self.log_config.to_json()
        configs[jk.display] = self.display_config.to_json()
        configs[jk.other] = self.other_config.to_json()
        logging.info("保存配置信息:{}".format(configs))
        write_json_file(setting_file_path, configs)


# 使用单例模式实例化配置生成器
configObject = Generator()


# 配置文件读取测试
if __name__ == "__main__":
    print("当前使用的图像源:", configObject.image_config.image_orgin)
    print("当前串口通讯的波特率:", configObject.communication_config.bps)
