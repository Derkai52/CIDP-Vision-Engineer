# -*- coding: utf-8 -*-
'''
    可视化颜色阈值调参工具
'''
import sys

import cv2
import numpy as np
from matplotlib import pyplot as plt
from utils.config_generator import configObject
import utils.json_keys as jk


class Tools():
    def __init__(self):
        self.lowerb = 0  # 最小值
        self.upperb = 255  # 最大值
        self.img = None  # RGB源图
        self.mask = None  # 二值化图
        self.img_hsv = None  # HSV图

    def updateMask(self):
        """ 更新MASK图像，并且刷新窗体 """
        # 计算MASK
        self.mask = cv2.inRange(self.img_hsv, np.int32(self.lowerb), np.int32(self.upperb))
        cv2.imshow('mask', self.mask)

    def updateThreshold(self, x):
        """ 更新阈值 """

        minH = cv2.getTrackbarPos('minH', 'image')
        maxH = cv2.getTrackbarPos('maxH', 'image')
        minS = cv2.getTrackbarPos('minS', 'image')
        maxS = cv2.getTrackbarPos('maxS', 'image')
        minV = cv2.getTrackbarPos('minV', 'image')
        maxV = cv2.getTrackbarPos('maxV', 'image')

        self.lowerb = [minH, minS, minV]
        self.upperb = [maxH, maxS, maxV]

        # print('当前阈值范围:\n最小值{}\n最小值{}:'.format(self.lowerb, self.upperb))
        self.updateMask()

    def debugHsv(self, img):
        self.img = img  # 获取图像 # TODO:这破坏了代码的优雅
        # 将图片转换为HSV格式
        self.img_hsv = cv2.cvtColor(self.img, cv2.COLOR_BGR2HSV)
        self.colorSpaceHist()  # 可视化目标区域HSV直方图

        cv2.namedWindow('image', flags=cv2.WINDOW_NORMAL | cv2.WINDOW_FREERATIO)
        cv2.imshow('image', self.img)

        cv2.namedWindow('mask', flags=cv2.WINDOW_NORMAL | cv2.WINDOW_FREERATIO)

        # 红色阈值 Bar
        cv2.createTrackbar('minH', 'image', 0, 255, self.updateThreshold)
        cv2.createTrackbar('maxH', 'image', 0, 255, self.updateThreshold)
        cv2.setTrackbarPos('maxH', 'image', configObject.image_config.maxH)
        cv2.setTrackbarPos('minH', 'image', configObject.image_config.minH)
        # 绿色阈值 Bar
        cv2.createTrackbar('minS', 'image', 0, 255, self.updateThreshold)
        cv2.createTrackbar('maxS', 'image', 0, 255, self.updateThreshold)
        cv2.setTrackbarPos('maxS', 'image', configObject.image_config.maxS)
        cv2.setTrackbarPos('minS', 'image', configObject.image_config.minS)
        # 蓝色阈值 Bar
        cv2.createTrackbar('minV', 'image', 0, 255, self.updateThreshold)
        cv2.createTrackbar('maxV', 'image', 0, 255, self.updateThreshold)
        cv2.setTrackbarPos('maxV', 'image', configObject.image_config.maxV)
        cv2.setTrackbarPos('minV', 'image', configObject.image_config.minV)

        # 首次初始化窗口的色块
        # 后面的更新 都是由getTrackbarPos产生变化而触发
        self.updateThreshold(None)
        # TODO: 将调试结果保存到配置文件，用于主程序读取
        print("调试目标物体的颜色阈值, 键入 e 退出Debug模式, 键入 s 保存当前配置")
        while True:
            keyBoard = cv2.waitKey(0)
            if keyBoard == (ord('s') or ord('S')):
                software_config = {}
                software_config[jk.image_orgin] = configObject.image_config.image_orgin  # 此处仅作为填充数据用，避免空值初始化
                software_config[jk.create_template_mode] = configObject.image_config.create_template_mode # 此处仅作为填充数据用，避免空值初始化
                software_config[jk.minH] = self.lowerb[0]
                software_config[jk.maxH] = self.upperb[0]
                software_config[jk.minS] = self.lowerb[1]
                software_config[jk.maxS] = self.upperb[1]
                software_config[jk.minV] = self.lowerb[2]
                software_config[jk.maxV] = self.upperb[2]
                configObject.image_config.from_json(software_config)  # 修改配置项
                configObject.serialize_config()  # 更新配置表
                print("HVS阈值范围已经保存！Min:", self.lowerb, "Max:", self.upperb)
                cv2.destroyAllWindows()
                return
            elif keyBoard == (ord('e') or ord('E')):
                print("退出调试模式")
                # cv2.imwrite('tmp_bin.png', self.mask)
                cv2.destroyAllWindows()
                return
            else:
                continue

    def colorSpaceHist(self):
        '''
        绘制彩图在HSV颜色空间下的统计直方图
        '''
        if self.img is None:
            print("图片读入失败, 请检查图片路径及文件名")
            exit()

        # 划分ROI范围
        bbox = cv2.selectROI(self.img, False)
        x1 = bbox[0]  # 左边界
        x2 = bbox[0] + bbox[2]  # 右边界
        y1 = bbox[1]  # 上边界
        y2 = bbox[1] + bbox[3]  # 下边界
        print("ROI范围为: \nX范围{}\nY范围{}".format((x1, x2), (y1, y2)))

        self.img = self.img[y1:y2, x1:x2]
        cv2.imshow("ROI", self.img)
        cv2.waitKey(1)

        # 将图片转换为HSV格式
        self.img = cv2.cvtColor(self.img, cv2.COLOR_BGR2HSV)
        # 创建画布
        fig, ax = plt.subplots()
        # Matplotlib预设的颜色字符
        hsvColor = ('y', 'g', 'k')
        # 统计窗口间隔 , 设置小了锯齿状较为明显 最小为1 最好可以被256整除
        bin_win = 3
        # 设定统计窗口bins的总数
        bin_num = int(256 / bin_win)
        # 控制画布的窗口x坐标的稀疏程度. 最密集就设定xticks_win=1
        xticks_win = 2
        # 设置标题
        ax.set_title('HSV Color Space')
        lines = []
        for cidx, color in enumerate(hsvColor):
            # cidx channel 序号
            # color r / g / b
            cHist = cv2.calcHist([self.img], [cidx], None, [bin_num], [0, 256])
            # 绘制折线图
            line, = ax.plot(cHist, color=color, linewidth=8)
            lines.append(line)

        # 标签
        labels = [cname + ' Channel' for cname in 'HSV']
        # 添加channel
        plt.legend(lines, labels, loc='upper right')
        # 设定画布的范围
        ax.set_xlim([0, bin_num])
        # 设定x轴方向标注的位置
        ax.set_xticks(np.arange(0, bin_num, xticks_win))
        # 设定x轴方向标注的内容
        ax.set_xticklabels(list(range(0, 256, bin_win * xticks_win)), rotation=45)

        # 显示画面
        plt.show()


def get_mask(img_bgr):
    """ 二值化矿石图 """
    img_hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    # 加载HSV阈值
    lowerb = [configObject.image_config.minH,
              configObject.image_config.minS,
              configObject.image_config.minV]

    upperb = [configObject.image_config.maxH,
              configObject.image_config.maxS,
              configObject.image_config.maxV]

    mask = cv2.inRange(img_hsv, np.int32(lowerb), np.int32(upperb))
    return mask


# 测试用例
if __name__ == "__main__":
    # 样例图片 (从命令行中填入)
    # image_path = sys.argv[1]

    # 样例图片 (在代码中填入)
    # image_path = "../test/rotate_test1.png" # 填入测试图像路径
    # img = cv2.imread(image_path)d
    # if img is None:
    #     print("Error: 文件路径错误，没有此图片 {}".format(image_path))
    #     exit(1)

    cap = cv2.VideoCapture(0)
    test_tools = Tools()

    while cap.isOpened():
        ret, image = cap.read()
        if cv2.waitKey(20) == (ord('d') or ord('D')):  # 对图像按下d键即可进入debug图像模式
            test_tools.debugHsv(image)
        image = get_mask(image)

        cv2.imshow("test", image)
