import cv2 as cv
import numpy as np
import time

from block_correction.pose import solve_pnp, four_point_transform, _order_points
from utils.auto_debug import Tools, get_mask
from utils.config_generator import configObject
from block_correction.classify import classic
from communite import MessageProcesser


class FeatureLabel():  # TODO: 等待迁移，用特征类代替
    def __init__(self, cla, h, w, box, particle, cnt_area, rect_area):
        self.classification = cla  # 特征类别
        self.height = h  # 最小外接矩形高
        self.width = w  # 最小外接矩形宽
        self.box = box  # 最小外接矩形的角点坐标 [[x1,y1],[x2,y2]...[x4,y4]]
        # self.point = []
        self.particle = particle  # 质点坐标 [x,y]
        self.cnt_area = cnt_area  # 特征轮廓面积
        self.rect_area = rect_area  # 最小外接矩形面积


class Cube():
    def __init__(self):
        self.height = None  # 特征标识最大矩形轮廓的高 float
        self.width = None  # 特征标识最大矩形轮廓的宽 float
        self.binary = None  # 二值化图
        self.box = None  # 存储特征标识的四点坐标信息 [[x1,y1],[x2,y2]...[x4,y4]]
        self.angle = None
        self.points = []  # 特征标识的质点坐标 [x,y]
        self.contour = None  # 轮廓坐标列表
        self.cnt_area = None  # 特征轮廓面积
        self.rect_area = None  # 特征外接矩形面积
        self.show_img = None  # 用于显示

        self.display_origin = True  # 展示源图像
        self.display_pretreatment = True  # 展示预处理结果图
        self.display_contours = True  # 展示特征轮廓
        self.is_centroid = True  # 展示特征轮廓质心

        self.load_det_params()  # 加载检测参数

    def load_det_params(self):
        """ 加载检测参数 """
        try:
            self.min_area = configObject.detection_config.min_area
            self.max_area = configObject.detection_config.max_area
            self.min_ration = configObject.detection_config.min_aspect_ratio
            self.max_ration = configObject.detection_config.max_aspect_ratio
            self.min_angle = configObject.detection_config.min_angle
            self.max_angle = configObject.detection_config.max_angle
            self.is_TemplateCreate = configObject.image_config.create_template_mode  # 模板采集模式
        except Exception as e:
            raise (e, "配置文件读取失败")

    def pretreatment(self, ori_image):
        """ 图像预处理 """
        if self.display_origin:
            cv.imshow("Origin", ori_image)
        mask_image = get_mask(ori_image)
        """ 若不使用HSV阈值二值化可用灰度图二值化
        st = cv.GaussianBlur(ori_image, (7, 7), 0) # 主要使得【条形码形成一个整体】和【R标尖角】”远离“ 右下角特征标签
        gray = cv.cvtColor(dst, cv.COLOR_BGR2GRAY)
        ret, binary = cv.threshold(gray, 0, 255, cv.THRESH_BINARY | cv.THRESH_OTSU)
        """
        kernel = cv.getStructuringElement(cv.MORPH_RECT, (3, 3))
        binary = cv.morphologyEx(mask_image, cv.MORPH_CLOSE, kernel)
        binary = cv.morphologyEx(binary, cv.MORPH_OPEN, kernel)
        if self.display_pretreatment:
            cv.imshow("Pretreatment", binary)
        return binary

    def min_contour_fitting(self):
        """ 最小矩形拟合 """
        rect = cv.minAreaRect(self.contour)
        self.angle = rect[-1]
        self.box = np.int0(cv.boxPoints(rect))  # 获得矩形角点
        self.rect_area = cv.contourArea(self.box)
        self.width = rect[1][0]
        self.height = rect[1][1]

    def check_area(self):
        """ 面积筛选 """
        self.cnt_area = cv.contourArea(self.contour)
        if self.min_area <= self.cnt_area <= self.max_area:  # 300 ~ 2000(跑仿真视频)
            self.min_contour_fitting()  # 首先通过面积筛选出可能的轮廓，再进行轮廓拟合
            return True
        else:
            return False

    def check_proportion(self):
        """ 长宽比筛选 """
        if self.min_ration <= (self.height/self.width) <= self.max_ration:
            return True
        else:
            return False

    def check_Inclination(self):
        """ 倾斜度筛选 """
        if (0 <= abs(self.angle) <= self.min_angle) or \
                (self.max_angle <= abs(self.angle) <= 90):
            return True
        else:
            return False

    def _reinitialize(self):
        """ 重置实例属性 """
        self.cnt_area = None
        self.rect_area = None
        self.box = None
        self.angle = None
        self.width = None
        self.height = None

    def contour_filter(self):
        """ 特征轮廓筛选 """
        if (self.check_area() and
                self.check_proportion() and
                self.check_Inclination()):
            return True
        else:
            self._reinitialize()  # 如果没有通过筛选，则重置已被赋值的实例属性，防止造成变量污染
            return False

    def display_featureLabel(self):
        """ 可视化展示特征标签 """
        cv.polylines(self.show_img, [self.box], True, (0, 255, 0), 3)
        text1 = 'W: ' + str(int(self.width)) + ' H: ' + str(int(self.height))
        text2 = 'Area: ' + str(int(self.cnt_area))
        # 为了显示直观，这里绘制文字选用的起始点是特征外轮廓左上角点；
        cv.putText(self.show_img, text1, (self.box[1][0] - 7, self.box[1][1] - 13), cv.FONT_HERSHEY_SIMPLEX, 0.5,
                   (200, 0, 0), 1,
                   cv.LINE_AA, 0)
        cv.putText(self.show_img, text2, (self.box[1][0] - 7, self.box[1][1] - 26), cv.FONT_HERSHEY_SIMPLEX, 0.5,
                   (200, 0, 0), 1,
                   cv.LINE_AA, 0)
        cv.putText(self.show_img, "1", (self.box[0][0], self.box[0][1]), cv.FONT_HERSHEY_SIMPLEX, 0.5, (200, 0, 0), 1,
                   cv.LINE_AA,
                   0)
        cv.putText(self.show_img, "2", (self.box[1][0], self.box[1][1]), cv.FONT_HERSHEY_SIMPLEX, 0.5, (200, 0, 0), 1,
                   cv.LINE_AA,
                   0)
        cv.putText(self.show_img, "3", (self.box[2][0], self.box[2][1]), cv.FONT_HERSHEY_SIMPLEX, 0.5, (200, 0, 0), 1,
                   cv.LINE_AA,
                   0)
        cv.putText(self.show_img, "4", (self.box[3][0], self.box[3][1]), cv.FONT_HERSHEY_SIMPLEX, 0.5, (200, 0, 0), 1,
                   cv.LINE_AA,
                   0)

        cv.imshow("featureLabel", self.show_img)

    def centroid_coordinate(self):
        """ 求轮廓质心坐标 """
        mu = cv.moments(self.contour, False)
        if mu['m00'] == 0.0:  # TODO: 一个不太优美的地方，可能会引发逻辑漏洞
            return
        mc = [mu['m10'] / mu['m00'], mu['m01'] / mu['m00']]
        if self.is_centroid:
            cv.circle(self.show_img, (int(mc[0]), int(mc[1])), 4, (255, 0, 0), 5)
        self.points.append([mc[0], mc[1]])

    def find_featureLabel_cnt(self, binary):
        """ 查找特征标签轮廓 """
        a, contours, hierarchy = cv.findContours(binary, cv.RETR_TREE, cv.CHAIN_APPROX_SIMPLE)
        if self.display_contours:
            cv.drawContours(self.show_img, contours, -1, (0, 0, 255), 2)
            cv.imshow("contours", self.show_img)
        return contours

    def _line_intersection(self, line1, line2):  # 传入元组
        """ 求两直线交点的算法 """
        xdiff = (line1[0][0] - line1[1][0], line2[0][0] - line2[1][0])
        ydiff = (line1[0][1] - line1[1][1], line2[0][1] - line2[1][1])

        def det(a, b):
            return a[0] * b[1] - a[1] * b[0]

        div = det(xdiff, ydiff)
        if div == 0:
            raise Exception('lines do not intersect')

        d = (det(*line1), det(*line2))
        x = det(d, xdiff) / div
        y = det(d, ydiff) / div
        return x, y

    def _iou_classify(self):
        """ 通过矩形轮廓与最大外轮廓IOU之比筛选出方型特征标签 """
        if self.rect_area / self.cnt_area < 1.5:  # 通常方形的比率控制在0.9~1.1, 直角边的比率控制在1.6~1.9， 所以使用1.5作为分界值
            return 1
        else:
            return 2

    def feature_classify(self):  # TODO: 质点坐标和轮廓中心坐标可能存在不对齐的情况
        """ 分类方形特征和直角特征，并获得直角特征的朝向 """
        # 区分方形特征和直角特征
        feature_class = self._iou_classify()
        if feature_class == 1:  # 方形特征
            direction = "rect"
            return direction
        elif feature_class == 2:  # 直角特征
            A = self.box[0]
            B = self.box[2]
            C = self.box[1]
            D = self.box[3]
            # 获取特征图案中心坐标
            center_x, center_y = self._line_intersection((A, B), (C, D))
            cv.circle(self.show_img, (int(center_x), int(center_y)), 4, (255, 0, 0), 5)

            # 获取特征图案质点坐标
            moment_x = self.points[-1][0]
            moment_y = self.points[-1][1]
            cv.circle(self.show_img, (int(moment_x), int(moment_y)), 4, (0, 255, 0), 5)

            # 区分直角特征图案方向
            if center_x > moment_x and center_y > moment_y:  # 左上角图案
                direction = "left_top"

            elif center_x > moment_x and center_y < moment_y:  # 左下角图案
                direction = "left_bottom"

            elif center_x < moment_x and center_y > moment_y:  # 右上角图案
                direction = "right_top"

            elif center_x < moment_x and center_y < moment_y:  # 右下角图案
                direction = "right_bottom"

            cv.putText(self.show_img, direction, (int(moment_x), int(moment_y) - 10), cv.FONT_HERSHEY_PLAIN,
                       1.0, (255, 0, 0), thickness=1)
            return direction


    def get_four_point(self, feature_list):  # TODO: 筛选出最合适的四点进行配对
        """ 筛选出最佳四点组合用于透视变换 """
        point_list = []
        for feature in feature_list:
            pass

    def main(self, ori_img):
        self.show_img = ori_img.copy()
        timer = cv.getTickCount()
        feature_list = []  # 存储特征实例
        # 1、图像预处理
        binary = self.pretreatment(ori_img)

        # 2、查找四角标签，轮廓筛选与处理
        contours = self.find_featureLabel_cnt(binary)
        for self.contour in contours:
            if not self.contour_filter():  # 轮廓条件筛选
                continue
            self.centroid_coordinate()  # 求轮廓质心坐标
            classify = self.feature_classify()  # 特征标签分类
            self.display_featureLabel()  # 可视化展示四角标签轮廓

        # 3、透视变换
        self.get_four_point(feature_list)  # 筛选合适四点
        if len(self.points) == 4:
            self.points = _order_points(np.array(self.points)).tolist()  # 获得四点排序后的点列表
            # 四点透视变换形成校正图像
            warped = four_point_transform(self.points,
                                          configObject.detection_config.tmpWidth,
                                          configObject.detection_config.tmpHeight,
                                          ori_img)

            if self.is_TemplateCreate:
                cv.imshow("templateCreate", warped)
                if cv.waitKey(1) & 0xFF in [ord('c'), ord('C')]:  # 按下 c 键创建模板图像
                    template_id = int(input("请输入录入模板类型:\n 0、R正立\n 1、R左躺\n 2、R右躺\n 3、R倒立\n 4、顶部\n 5、二维码面\n"))
                    tmpNames = ["label_R_top.jpg", "label_R_left.jpg", "label_R_right.jpg",
                                "label_R_bottom.jpg", "label_top.jpg", "label_barCode.jpg"]
                    cv.imwrite(tmpNames[template_id], warped)

            # 6、特征分类
            class_id = classic(warped)
            if class_id:
                # 7、姿态估计
                coordinate, pose = solve_pnp(self.points)
                coor_x = pose[0]
                coor_y = pose[1]
                coor_z = pose[2]

                # 8、上下位机通讯
                send_msg = messageProcesser.get_send_msg(function_word=2, class_id=class_id, x=coor_x, y=coor_y, z=coor_z)
                messageProcesser.USB0.write(send_msg)  # 这里面不断地进行发送任务
                # time.sleep(0.005)

        self.points = []  # 清空变量

        cv.imshow("Origin", ori_img)
        cv.waitKey(1)
        fps = cv.getTickFrequency() / (cv.getTickCount() - timer)
        print("FPS：", fps)


def on_EVENT_LBUTTONDOWN(event, x, y, flags, param):
    if event == cv.EVENT_LBUTTONDOWN:
        global label_box_list
        label_box_list.append([x, y])
        xy = "%d,%d" % (x, y)
        # print(xy)
        cv.circle(image, (x, y), 1, (255, 0, 0), thickness=-1)
        cv.putText(image, xy, (x, y), cv.FONT_HERSHEY_PLAIN,
                   1.0, (0, 0, 0), thickness=1)
        cv.imshow("image", image)


# cv.setMouseCallback("image", on_EVENT_LBUTTONDOWN)

if __name__ == "__main__":
    # cap = cv.VideoCapture("../test/hik_test.avi")
    cap = cv.VideoCapture(0)
    cube = Cube()
    test_tools = Tools()
    messageProcesser = MessageProcesser(is_vofa=True)
    while cap.isOpened():
        ret, image = cap.read()
        if not ret:
            break
        if cv.waitKey(1) == (ord('d') or ord('D')):  # 对图像按下d键即可进入debug图像模式
            test_tools.debugHsv(image)
        # image = cv.resize(image, (640, 480))
        cube.main(image)  # 程序主入口
